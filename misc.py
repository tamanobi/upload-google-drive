from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import json

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class AppDrive:
    app_name = None
    app_root_id = None
    service = None
    slack = None


    def __init__(self, name, client_secrets_raw, slack=None):
        self.app_name = name
        self.service = self.get_service(client_secrets_raw)
        self.root_id = self.get_root_id()
        self.slack = slack
        if self.root_id is None:
            self.root_id = self.mkdir(self.app_name)

    def get_service(self, client_secrets_raw):
        """Shows basic usage of the Drive v3 API.
        Pirints the names and ids of the first 10 files the user has access to.
        """
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        creds = None
        if os.path.exists('token/token.pickle'):
            with open('token/token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                       json.loads(client_secrets_raw), SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token/token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def mkdir(self, name):
        folder_metadata = {
            'name' : name,
            # The mimetype defines this new file as a folder, so don't change this.
            'mimeType' : 'application/vnd.google-apps.folder'
        }
        a = self.service.files().create(body=folder_metadata).execute()
        return a.get('id')

    def get_root_id(self):
        result = self.service.files().list(
                pageSize=1,
                q=f"'root' in parents and trashed=false and name = '{self.app_name}'",
                fields="files(id, name)"
        ).execute()
        files = result.get('files')
        if len(files) == 0:
            return None
        return files[0].get('id')

    def media(self, media_path, name=None, description="", parent_id=None):
        if parent_id is None:
            parent_id = self.root_id
        if name is None:
            name = Path(media_path).name

        metadata = {
            'name' : name,
            "parents": [parent_id],
            "description": description,
        }
        return self.service.files().create(body=metadata, media_body=media_path)

    def upload_media(self, media_path, name=None, description="", parent_id=None):
        uploader = self.media(media_path, name=None, description="", parent_id=None)
        r = uploader.execute()
        return r.get('id')

    def callback(request_id, response, exception):
        if exception:
            # Handle error
            print(exception)
        else:
            print(f"Permission Id: {response.get('id')}")

    def upload_medium_from_directory(self, dir_path):
        png = [str(p) for p in Path(dir_path).glob('*.png')]
        jpg = [str(p) for p in Path(dir_path).glob('*.jpg')]
        total = len(png) + len(jpg)
        for i, file_path in enumerate(png + jpg):
            txt = f"{i}/{total}: uploading: {file_path}"
            print(txt)
            if self.slack is not None:
                try:
                    self.slack.notify(text=txt)
                except:
                    pass

            self.upload_media(media_path=file_path)

            txt = f"{i}/{total}: done: {file_path}"
            print(txt)
            if self.slack is not None:
                try:
                    self.slack.notify(text=txt)
                except:
                    pass

    def upload_media_many(self, medium):
        batch = self.service.new_batch_http_request(callback=self.callback)

        for media in medium:
            path = media.get('path')
            name = media.get('name', None)
            description = media.get('description', None)
            parent_id = media.get('parent_id', None)
            uploader = self.media(path, name=None, description="", parent_id=None)
            batch.add(uploader)

        batch.execute()
