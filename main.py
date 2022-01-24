"""
How to deploy:
    - Create an IFTTT worflow
        - if this = webhook with a json payload
            - name the event 'random_exercise'
        - then that = notification
            - choose the rich one
            - the title and message are irrelavant as they will overwrriten
        - add a filter code step in between the two:
            let payload = JSON.parse(MakerWebhooks.jsonEvent.JsonPayload)
            IfNotifications.sendRichNotification.setTitle(payload.message_title)
            IfNotifications.sendRichNotification.setMessage(payload.message)
            IfNotifications.sendRichNotification.setImageUrl(payload.image_url)
        - locate the api key for IFTTT under your account
            - go to My services
            - then choose Webhooks and go to settings
    - Create a Google Cloud Project that can do billing
    - Enable the following APIs in the project
        - Google Sheets
        - Google Drive
        - Secrets Manager
        - Cloud Functions
    - Add the following secrets in the secrets manager
        - 'ifttt_api_key' as a string
        - url for image to be used in notification
            - call it 'workout_image_url'
        - default app engine service account json key as a file
            - call it 'service_account_json'
            - this can be downloaded from IAM
            - other service account can be created an used
            - if so make sure to grant this account permission to the funcion
    - In the IAM console add a new role to give the service account access to secret manager secret accessor
    - Create a google sheet with one column titled "exercises"
        - name the sheet 'random exercises'
        - share this sheet with the service account you are using
        - use their service account email address
        - add in row by row the names of the exercises of interest
    - Enable the Cloud Scheduler in GCP
    - Add a new job with a frequency like: 45 8,11,13,16,19,21 * * *
    - Make sure to set the right timezone
    - for the execution use the URL from the cloud function

Use the following command to deploy:
* change the project_id accordingly
"""
# gcloud functions deploy exercise --set-env-vars project_id=home-automation-272816 --runtime python39 --trigger-http --allow-unauthenticated
from requests import get, post
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import secretmanager
import json
import os
from random import choice

# the project id is set using an env variable when deploying
# it is needed for acessing secrets
PROJECT_ID = os.environ["project_id"]

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
