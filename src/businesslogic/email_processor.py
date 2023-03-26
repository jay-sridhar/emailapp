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

    def fetch_user_messages_meta(self, user_id='me', page_token=None, query_string=None, include_spam=False,
                                 max_results=10):
        return self.service.users().messages().list(userId=user_id, maxResults=max_results, q=query_string,
                                                    includeSpamTrash=include_spam, pageToken=page_token).execute()

    def _download_and_save_labels(self):
        labels = self.service.users().labels().list(userId='me').execute()
        # insert labels into the database
        self._get_connection()
        cursor = self.__connection.cursor()
        cursor.execute("delete from label")
        for label in labels.get('labels'):
            cursor.execute(f"insert into label(`id`, `name`, `type`, `refreshed_on`) values ('{label['id']}', "
                           f"'{label['name']}', '{label['type']}', now())")
        cursor.close()
        self.__connection.commit()

    def __sync_emails(self, emails):
        """
        :param emails:
        :return:
        """
        self._get_connection()
        if self.fetch_mode == MESSAGE_FORMAT_MINIMAL:
            EmailDAO(self.__connection).bulk_sync_labels(emails)
        else:
            EmailDAO(self.__connection).bulk_insert_attributes_and_labels(emails)

    def __process_batch_request(self, emails, batch_header, data):
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

    def _download_and_save_message_ids(self, fetch_mode, **kwargs):
        defaults = {'userId': 'me'}
        self.fetch_mode = fetch_mode

        if kwargs:
            kwargs.update(defaults)
        else:
            kwargs = defaults
        while True:
            result = self.service.users().messages().list(**kwargs).execute()
            self._get_connection()
            EmailDAO(self.__connection).bulk_insert_message_ids(result['messages'])
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
        self._download_and_save_message_ids(fetch_mode, **kwargs)
