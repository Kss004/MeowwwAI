import json
import certifi
import pymongo
import plivo

with open("config.json", "r") as f:
    config = json.load(f)

mongo_client = pymongo.MongoClient(config["mongodb"]["url"], tlsCAFile=certifi.where())
db_name = mongo_client[config["mongodb"]["dbName"]]
screenings = db_name['screenings']
jobs = db_name['jobs']
jobquestions = db_name['jobquestions']
companies = db_name['companies']

NUMBER = config['PLIVO_NUMBER']
DEEPGRAM_API_KEY = config['DEEPGRAM_API_KEY']
AUTH_ID = config['PLIVO_AUTH_ID']
AUTH_TOKEN = config['PLIVO_AUTH_TOKEN']

plivo_client = plivo.RestClient(auth_id=AUTH_ID, auth_token=AUTH_TOKEN)