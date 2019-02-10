from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from misc import AppDrive
import os
import slackweb

def main():
    client_secrets_raw = os.getenv('GOOGLE_CLIENT_SECRETS', '')
    if os.getenv('SLACK'):
        slack = slackweb.Slack(url=os.getenv('SLACK'))

    drive = AppDrive("gazo-collection", client_secrets_raw, slack)

    path = os.getenv('UPLOAD_DIR')
    if path is not None:
        drive.upload_medium_from_directory(path)

if __name__ == '__main__':
    main()
