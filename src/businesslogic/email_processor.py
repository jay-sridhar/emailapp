from lib.google_api import GoogleAPIHelper
from lib.db_utils import DBUtils
from lib.logger_utils import get_logger
from config.settings import MESSAGE_FORMAT_MINIMAL, BATCH_FETCH_EMAIL_SIZE
from models.email import EmailDAO

LOGGER = get_logger(__name__)


class EmailProcessor(object):
    def __init__(self):
        self.service = GoogleAPIHelper().get_service_instance()
        self.__connection = None
        self.__max_fetch_limit = None
        self.fetch_mode = None

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

    def _batch_get_email_details(self, messages):
        """
        Bulk fetches email contents in multiples of BATCH_FETCH_EMAIL_SIZE
        """

        def sync_emails(request_id, response, exception):
            """
            :brief: Callback method that syncs the GET message response to the database
            :param request_id: request id, if set in add() method can be accessed here.
            :param response: Response body containing the message information
            :param exception: When the GET call fails due to an exception, the same is available in this param
            """
            LOGGER.debug(f"Request_id {request_id}")
            if exception is None:
                self._get_connection()
                if self.fetch_mode == MESSAGE_FORMAT_MINIMAL:
                    EmailDAO(self.__connection).upsert_labels(response)
                else:
                    EmailDAO(self.__connection).upsert_attributes_and_label(response)
            else:
                LOGGER.error(f"Exception while getting message. Details: {exception}")

        count = 0
        message_len = len(messages)
        batch = self.service.new_batch_http_request(callback=sync_emails)
        # Outer for loop determines the number of batches needed
        for batch_id in range(0, ((message_len - 1) // BATCH_FETCH_EMAIL_SIZE) + 1):
            batch_count = 0
            # The while loop queues up the GET requests till either the batch size is reached or
            # all the message ids are processed
            while True:
                batch.add(self.service.users().messages().get(userId='me', id=messages[count]['id'], format='full'))
                batch_count += 1
                count += 1
                if batch_count == BATCH_FETCH_EMAIL_SIZE or count == message_len:
                    batch.execute()
                    break
            LOGGER.info(f"Processed batch # {batch_id}. Batch size: {BATCH_FETCH_EMAIL_SIZE}")

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
