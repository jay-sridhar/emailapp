from lib.google_api import GoogleAPIHelper
from lib.db_utils import DBUtils
from lib.logger_utils import get_logger
from config.settings import END_OF_REQUEST_DELIMITER, MESSAGE_FORMAT_MINIMAL, BATCH_FETCH_EMAIL_SIZE
from models.email import EmailDAO
import json

import requests

LOGGER = get_logger(__name__)


class EmailProcessor(object):
    def __init__(self):
        self.service = GoogleAPIHelper().get_service_instance()
        self.__connection = None
        self.__max_fetch_limit = None
        self.fetch_mode = None
        self.__token = GoogleAPIHelper.get_api_token()

    def _get_connection(self):
        self.__connection = DBUtils.renew_or_get_new_connection(self.__connection)
        return self.__connection

    def _download_and_save_labels(self):
        EmailDAO(self._get_connection()).remove_all_labels()
        labels = self.service.users().labels().list(userId='me').execute()
        # insert labels into the database
        for label in labels.get('labels'):
            EmailDAO(self._get_connection()).insert_label(label)
        self.__connection.commit()

    def __sync_emails(self, emails):
        """
        Saves / syncs the email contents to the database.
        :param emails: List of message content fetched from batch API
        """
        self._get_connection()
        if self.fetch_mode == MESSAGE_FORMAT_MINIMAL:
            EmailDAO(self.__connection).upsert_labels(emails)
        else:
            EmailDAO(self.__connection).upsert_attributes_and_labels(emails)

    def __process_batch_request(self, emails, batch_header, data):
        """
        Call the Google's batch GET email API
        """
        data += f'--{END_OF_REQUEST_DELIMITER}--'
        r = requests.post(f"https://www.googleapis.com/batch/gmail/v1",
                          headers=batch_header, data=data)
        bodies = r.content.decode().split('\r\n')
        for body in bodies:
            # Other responses that don't begin with { are either empty or batch or http status messages
            if body.startswith('{'):
                parsed_body = json.loads(body)
                emails.append(parsed_body)
        self.__sync_emails(emails)
        LOGGER.info(f"Processed {len(emails)} emails")

    def _batch_get_email_details(self, messages):
        """
        Bulk fetches email contents in multiples of BATCH_FETCH_EMAIL_SIZE
        """
        emails = []
        batch_header = {'Authorization': f'Bearer {self.__token}',
                        'Content-Type': f'multipart/mixed; boundary="{END_OF_REQUEST_DELIMITER}"'}
        data = ''
        count = 0
        batch_size = BATCH_FETCH_EMAIL_SIZE
        processed_mails = 0

        for message in messages:
            data += f'--{END_OF_REQUEST_DELIMITER}\nContent-Type: application/http\n\nGET /gmail/v1/users/me/messages/{message["id"]}?format={self.fetch_mode}\n'
            if count == batch_size - 1:
                print(f"calling batch {count} {batch_size}")
                self.__process_batch_request(emails, batch_header, data)
                processed_mails += len(emails)
                if processed_mails >= self.__max_fetch_limit:
                    LOGGER.error(f"Halting the process as the max_fetch_limit ({self.__max_fetch_limit}) is reached")
                    exit(-1)
                emails = []
                data = ''
                count = 0
                continue
            count += 1
        if data:
            data += f'--{END_OF_REQUEST_DELIMITER}--'
            self.__process_batch_request(emails, batch_header, data)

    def _download_and_save_emails(self, fetch_mode, **kwargs):
        """
        :brief: This method does the following operations with pagination till all the pages are processed.
                1. Gets the message ids for all the messages (or for the given filter when supplied)
                2. Upserts the message ids into the database
                3. Bulk reads the email contents corresponding to the message ids and stores / syncs the same
        :param fetch_mode:  One of full or minimal (Supported by Gmail messages.get API).
                            Only labels and history id are fetched with minimal mode
        :param kwargs:  arguments supported by users.messages.list API.
                        Refer: https://developers.google.com/gmail/api/reference/rest/v1/users.messages/list#query-parameters
        """
        defaults = {'userId': 'me'}
        self.fetch_mode = fetch_mode
        if kwargs:
            kwargs.update(defaults)
        else:
            kwargs = defaults
        while True:
            result = self.service.users().messages().list(**kwargs).execute()
            if not result.get('messages'):
                print("No emails found with the matching filters")
                break
            EmailDAO(self._get_connection()).bulk_insert_message_ids(result['messages'])
            self._batch_get_email_details(result['messages'])
            next_page_token = result.get('nextPageToken')
            LOGGER.info(f"Next page token is {next_page_token}")
            if next_page_token:
                kwargs['pageToken'] = next_page_token
            else:
                break

    def download_emails_to_db(self, max_fetch_limit, fetch_mode, **kwargs):
        self.__max_fetch_limit = max_fetch_limit
        self._download_and_save_labels()
        self._download_and_save_emails(fetch_mode, **kwargs)
