from conns import plivo_client
import plivo
from datetime import datetime, timedelta, timezone
import bson
from conns import *

async def end_call(call_uuid: str, reason: str = None):
    try:
        if not call_uuid:
            print(f"Attempted to end call with no UUID. Reason: {reason}")
            return {
                "status": "error",
                "message": "No active call UUID provided",
                "reason": reason
            }
        
        try:
            response = plivo_client.calls.delete(call_uuid=call_uuid)
            
            print(f"Call {call_uuid} ended successfully. Reason: {reason}")
            
            return {
                "status": "success",
                "message": "Call ended successfully",
                "reason": reason,
                "plivo_response": response
            }
        
        except plivo.exceptions.PlivoRestError as plivo_err:
            error_msg = f"Plivo error ending call {call_uuid}: {str(plivo_err)}"
            print(error_msg)
            
            return {
                "status": "error",
                "message": error_msg,
                "error_details": str(plivo_err)
            }
        
    except Exception as e:
        error_msg = f"Unexpected error ending call {call_uuid}: {str(e)}"
        print(error_msg)
        
        return {
            "status": "error",
            "message": error_msg,
            "error_details": str(e)
        }

def reschedule_interview(screening_id: str, preferred_date: str, preferred_time: str, reason: str = None):
    try:
        try:
            from dateutil.parser import parse
            from dateutil.relativedelta import relativedelta
            
            parsed_datetime = parse(f"{preferred_date} {preferred_time}")
            
            ist_datetime = parsed_datetime.astimezone(timezone(timedelta(hours=5, minutes=30)))
            
            max_future_date = datetime.now(ist_datetime.tzinfo) + relativedelta(months=3)
            
            if ist_datetime < datetime.now(ist_datetime.tzinfo):
                return {
                    "status": "error",
                    "message": "Interview cannot be scheduled in the past."
                }
            
            if ist_datetime > max_future_date:
                return {
                    "status": "error",
                    "message": "Interview cannot be scheduled more than 3 months in the future."
                }
            
            rescheduled_datetime = ist_datetime.isoformat()
            print(rescheduled_datetime)
            
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Invalid date or time format: {str(e)}. Please use a clear date and time."
            }

        screenings.update_one(
            {"_id": bson.ObjectId(screening_id)},
            {
                "$set": {
                    "rescheduledTo": rescheduled_datetime,
                    "rescheduledReason": reason or "Candidate requested reschedule",
                    "status": "rescheduled",
                    "updatedAt": datetime.utcnow().isoformat()
                }
            }
        )

        print("reschedule completed")
        
        return {'status':"success", "message": "rescheduled call successfully!"}

    except Exception as e:
        error_msg = f"Error rescheduling interview: {str(e)}"
        print(error_msg)
        
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": error_msg,
            "error_details": str(e)
        }