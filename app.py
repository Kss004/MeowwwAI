from quart import Quart, websocket, Response, request
import asyncio
import websockets
import json
import base64
from datetime import datetime
from conns import *
import bson
from quart_cors import cors
from functions import *
from schema import *

with open("prompt.txt", "r") as file:
    prompt = file.read()

app = Quart(__name__)
app = cors(app, allow_origin="*", allow_headers=["*"], allow_methods=["*"])

@app.before_serving
async def setup_cors():
    def _add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Allow-Methods'] = '*'
        return response
    
    app.after_request(_add_cors_headers)

@app.route('/')
async def health_check():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })

    ws_status = "Not tested"
    try:
        async with websockets.connect(
            "wss://agent.deepgram.com/agent",
            extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        ) as ws:
            ws_status = "Connected"
    except Exception as e:
        ws_status = f"Error: {str(e)}"

    active_calls_info = {
        'count': len(active_calls),
        'call_ids': list(active_calls.keys())
    }

    plivo_status = "Not tested"
    try:
        account_details = plivo_client.account.get()
        plivo_status = "Connected"
    except Exception as e:
        plivo_status = f"Error: {str(e)}"

    db_status = "Not tested"
    try:
        db_name.command('ping')
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"

    status_info = {
        'status': 'running',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
        "account_details": account_details,
        'routes': routes,
        'connections': {
            'deepgram_websocket': ws_status,
            'plivo_api': plivo_status,
            'mongodb': db_status
        },
        'active_calls': active_calls_info,
        'version': '1.0.0'
    }

    return status_info

@app.post('/make-a-call')
async def make_outbound_call():
    request_data = await request.get_json()
    req = data(**request_data)

    targetData = targets.find_one({"_id": bson.ObjectId(str(req.target_id))})
    orgData = organizations.find_one({"_id": bson.ObjectId(str(targetData['jobId']))})

    call_session = CallSession(
        target_id = req.target_id,
        target_name = targetData['target_name'],
        target_details = targetData['target_details'],
        target_call_agenda = targetData['target_call_agenda'],
        target_extra_details = targetData["target_extra_details"],
        org_name = orgData['org_name'],
        org_about = orgData['org_about'],
        transcript=[]
    )

    call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{req.target_id}"
    
    call_response = plivo_client.calls.create(
        from_=NUMBER,
        to_="91"+str(targets['target_phone'])[-10:],
        answer_url=f"https://8159-115-245-68-163.ngrok-free.app/webhook/{call_id}",
        answer_method='GET',
    )
    
    call_session.call_uuid = call_response.request_uuid
    active_calls[call_id] = call_session

    return {
        "status": "Call initiated", 
        "call_id": call_id,
        "call_uuid": call_response.request_uuid
    }

@app.route("/webhook/<call_id>", methods=["GET", "POST"])
async def webhook(call_id):
    if call_id not in active_calls:
        return Response("Invalid call ID", status=400)

    print(f"Generating webhook response for call_id: {call_id}")
    print(f"Request host: {request.host}")
    
    xml_data = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Record recordSession="true" redirect="false" maxLength="3600" />
        <Stream streamTimeout="86400" keepCallAlive="true" bidirectional="true" contentType="audio/x-mulaw;rate=8000" audioTrack="inbound">
            wss://{request.host}/media-stream/{call_id}
        </Stream>
    </Response>
    '''
    print(f"Generated XML: {xml_data}")
    return Response(xml_data, mimetype='application/xml')

@app.websocket('/media-stream/<call_id>')
async def handle_message(call_id):
    try:
        print(f"Websocket connection attempt for call_id: {call_id}")
        
        if call_id not in active_calls:
            print(f"Call ID {call_id} not found in active_calls")
            return

        call_session = active_calls[call_id]
        plivo_ws = websocket

        print(f"Active calls: {list(active_calls.keys())}")

        url = "wss://agent.deepgram.com/agent"
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

        try:
            async with websockets.connect(url, extra_headers=headers) as deepgram_ws:
                call_session.websocket_connections = {
                    'plivo': plivo_ws,
                    'deepgram': deepgram_ws
                }

                await send_session_update(call_session)
                receive_task = asyncio.create_task(
                    receive_from_plivo(call_session)
                )

                try:
                    async for message in deepgram_ws:
                        await receive_from_deepgram(message, call_session)
                except Exception as inner_e:
                    print(f"Inner websocket error for call {call_id}: {inner_e}")
                
                await receive_task

        except Exception as e:
            print(f"Error in call {call_id}: {e}")
        finally:
            await save_transcript(call_session)
            if call_id in active_calls:
                del active_calls[call_id]
    except Exception as e:
        print(f"Error in websocket connection: {e}")
        raise

async def receive_from_plivo(call_session: CallSession):
    plivo_ws = call_session.websocket_connections['plivo']
    deepgram_ws = call_session.websocket_connections['deepgram']
    
    BUFFER_SIZE = 20 * 160
    inbuffer = bytearray(b"")

    try:
        while True:
            message = await plivo_ws.receive()
            data = json.loads(message)
            
            if data['event'] == 'media' and deepgram_ws.open:
                chunk = base64.b64decode(data['media']['payload'])
                inbuffer.extend(chunk)
            elif data['event'] == "start":
                call_session.stream_id = data['start']['streamId']
            elif data['event'] == "stop":
                break

            while len(inbuffer) >= BUFFER_SIZE:
                chunk = inbuffer[:BUFFER_SIZE]
                await deepgram_ws.send(chunk)
                inbuffer = inbuffer[BUFFER_SIZE:]

    except Exception as e:
        print(f"Error in Plivo communication: {e}")

def check_end_call_trigger(message: str) -> bool:
    goodbye_phrases = [
        'goodbye',
        'have a great day',
        "We'll see you soon"
    ]
    
    lowercase_message = message.lower()
    return any(phrase in lowercase_message for phrase in goodbye_phrases)

async def receive_from_deepgram(message, call_session: CallSession):
    plivo_ws = call_session.websocket_connections['plivo']
    deepgram_ws = call_session.websocket_connections['deepgram']
    
    try:
        if isinstance(message, str):
            response = json.loads(message)
            print( response)
            
            if response['type'] == 'ConversationText':
                current_message = response.get('content', '').strip()
                
                call_session.transcript.append({
                    'role': response['role'],
                    'message': current_message
                })
                
                if check_end_call_trigger(current_message):
                    result = await end_call(call_session.call_uuid, 'wrong_person')
                    print(f"Auto-ending call due to goodbye phrase: {current_message}")
            
            elif response['type'] == 'FunctionCallRequest':
                if response['function_name'] == 'endCall':
                    reason = response.get('input', {}).get('reason', 'NA')
                    result = await end_call(call_session.call_uuid, reason)
                    print(result)
                    functionCallResponse = {
                        "type": "FunctionCallResponse",
                        "function_call_id": response['function_call_id'],
                        "output": "Call ended successfully. Goodbye!" if result["status"] == "success" else f"Failed to end call: {result['message']}"
                    }

                    print(functionCallResponse)
                    await deepgram_ws.send(json.dumps(functionCallResponse))

                # elif response['function_name'] == 'rescheduleInterview':
                #     params = response.get('input', {})
                #     preferred_date = params.get('preferred_date')
                #     preferred_time = params.get('preferred_time')
                #     reason = params.get('reason', 'Candidate requested reschedule')

                #     if not preferred_date or not preferred_time:
                #         functionCallResponse = {
                #             "type": "FunctionCallResponse",
                #             "function_call_id": response['function_call_id'],
                #             "output": "Missing required parameters for rescheduling. Please provide both date and time."
                #         }
                #     else:
                #         result = reschedule_interview(
                #             call_session.screening_id,
                #             preferred_date,
                #             preferred_time,
                #             reason
                #         )
                #         print(result)
                #         functionCallResponse = {
                #             "type": "FunctionCallResponse",
                #             "function_call_id": response['function_call_id'],
                #             "output": result["status"]
                #         }
                    
                #     print(functionCallResponse)
                #     await deepgram_ws.send(json.dumps(functionCallResponse))
            
            elif response["type"] == 'AgentStartedSpeaking':
                print(f"Agent speaking for call {call_session.target_id}")
                
        else:
            audioDelta = {
                "event": "playAudio",
                "media": {
                    "contentType": 'audio/x-mulaw',
                    "sampleRate": 8000,
                    "payload": base64.b64encode(message).decode("ascii")
                }
            }
            await plivo_ws.send(json.dumps(audioDelta))
    
    except Exception as e:
        print(f"Error in Deepgram communication: {e}")


async def send_session_update(call_session: CallSession):
    deepgram_ws = call_session.websocket_connections['deepgram']
    # current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    session_update = {
            "type": "SettingsConfiguration",
            "audio": {
                "input": {
                    "encoding": "mulaw",
                    "sample_rate": 8000
                },
                "output": {
                    "encoding": "mulaw",
                    "sample_rate": 8000,
                    "container": "none",
                }
            },
            "agent": {
                "listen": {
                    "model": "nova-3"
                },
                "think": {
                    "provider": {
                        "type": "open_ai"
                    },
                    "model": "gpt-4o-mini",
                    "instructions": prompt.format(
                        target_name=call_session.target_name,
                        target_details=call_session.target_details,
                        target_call_agenda=call_session.target_call_agenda,
                        target_extra_details=call_session.target_extra_details,
                        org_name=call_session.org_name,
                        org_about=call_session.org_about
                    ).strip(),
                    "functions": [
                        {
                            "name": "endCall",
                            "description": "End the current phone call. Must be called using proper function calling format. This function will be executed in all scenarios to ensure the call is ended appropriately.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "reason": {
                                        "type": "string",
                                        "enum": ["wrong_person", "user_request", "reschedule", "interview_complete", "declined_interview"],
                                        "description": "The reason for ending the call"
                                    }
                                },
                                "required": ["reason"]
                            }
                        },
                        # {
                        #     "name": "rescheduleInterview",
                        #     "description": f"""Reschedule the interview for a new time slot. Time should be in IST. The date and time right now is: {current_datetime}, use this without asking the user about tomrrow's date if they ask to reschedule the call tomorrow. Also dont ask the time zone, silently take it as IST""",
                        #     "parameters": {
                        #         "type": "object",
                        #         "properties": {
                        #             "preferred_date": {
                        #                 "type": "string",
                        #                 "description": "The preferred date in YYYY-MM-DD format"
                        #             },
                        #             "preferred_time": {
                        #                 "type": "string",
                        #                 "description": "The preferred time in 24-hour HH:mm format (IST)"
                        #             },
                        #             "reason": {
                        #                 "type": "string",
                        #                 "description": "Reason for rescheduling"
                        #             }
                        #         },
                        #         "required": ["preferred_date", "preferred_time", "reason"]
                        #     }
                        # }
                    ]
                },
                "speak": {
                    "model": "aura-hera-en"
                }
            },
            "context": {
                "messages": [
                    {
                        "content": f"Hi, this is Medu from {call_session.org_name}. I have called you for a free consultation for your company. Am I talking with someone from {call_session.target_name}?",
                        "role": "user"
                    }
                ],
                "replay": True
            }
        }
    await deepgram_ws.send(json.dumps(session_update))


if __name__ == "__main__":
    app.run(port=config['server']['port'])
