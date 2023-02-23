from requests import get, post
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import secretmanager
import json
import os
from random import choice

# the project id is set using an env variable when deploying
# it is needed for acessing secrets
PROJECT_ID = os.getenv("MY_PROJECT_ID")

# name of Google Sheet that has the exercises
SHEET_NAME = "random exercises"

# name of the ifttt event that will handle the web request
IFTTT_EVENT = "random_exercise"


# this function gets a secret from the GCP secret manager
def get_secret(secret_name: str):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(name=name)
    secret = response.payload.data.decode("UTF-8")
    # if the secret is a file we need to convert to a dict
    # otherwise keep as is
    try:
        secret = json.loads(secret)
    except:
        pass
    return secret  # returns a json or a string depending on the secret type


# the request parameter is not used but GCP requires it
def exercise(request):
    ifttt_key = get_secret("ifttt_api_key")
    service_account_json = get_secret("service_account_json")
    image_url = get_secret("workout_image_url")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_json, scope
    )

    # connect to the Google Sheet
    client = gspread.authorize(creds)
    data = client.open(SHEET_NAME).sheet1.get_all_records()

    # put into a list all the exercises
    # there must be a column with the name 'exercises'
    exercises = [x["exercises"] for x in data if "exercises" in x]

    # ifttt will be expecting this
    data = {
        "message_title": "Exercise Time!",
        "message": choice(exercises),  # choose a random exercise
        "image_url": image_url,
    }

    # exercise is pushed to IFTTT notification on phone
    post(
        f"https://maker.ifttt.com/trigger/{IFTTT_EVENT}/json/with/key/{ifttt_key}",
        data=data,
    )
    return "Yay Exercise!"
