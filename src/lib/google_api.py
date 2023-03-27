from __future__ import print_function

import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from lib.logger_utils import get_logger
from config.settings import TOKEN_FILE_PATH, CREDENTIALS_FILE_PATH, SCOPES

LOGGER = get_logger(__name__)


class GoogleAPIHelper(object):

    def __init__(self):
        self.credentials = None

    @staticmethod
    def get_api_token():
        with open(TOKEN_FILE_PATH, "r") as file_obj:
            return json.load(file_obj)['token']

    def __setup_token(self):
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(TOKEN_FILE_PATH):
            self.credentials = Credentials.from_authorized_user_file(TOKEN_FILE_PATH, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                LOGGER.info('Creating / refreshing token')
                self.credentials.refresh(Request())
            else:
                LOGGER.debug('Using existing token')
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE_PATH, SCOPES)
                self.credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN_FILE_PATH, 'w') as token:
                token.write(self.credentials.to_json())

    def get_service_instance(self):
        try:
            self.__setup_token()
            # Call the Gmail API
            service = build('gmail', 'v1', credentials=self.credentials)
            return service
        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            LOGGER.exception('An exception while connecting to API. Details %s', error)
