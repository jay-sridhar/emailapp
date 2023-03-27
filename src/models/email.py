from config.settings import DEFAULT_HEADER_DICT, QUERYABLE_HEADERS, MESSAGE_FORMAT_MINIMAL
import json
from datetime import datetime
from lib.logger_utils import get_logger
from lib.db_utils import DBUtils
import mysql.connector

LOGGER = get_logger(__name__)


class EmailDAO(object):
    def __init__(self, connection):
        self.connection = connection

    def remove_all_labels(self):
        cursor = self.connection.cursor()
        cursor.execute(f"delete from label")

    def insert_label(self, label):
        cursor = self.connection.cursor()
        cursor.execute(f"insert into label(`id`, `name`, `type`, `refreshed_on`) values ('{label['id']}',"
                       f"'{label['name']}', '{label['type']}', now())")

    def bulk_insert_message_ids(self, messages):
        cursor = self.connection.cursor()
        values_clause = ""
        for message in messages:
            values_clause += f"({int(message['id'], 16)}, {int(message['threadId'], 16)}, now()),"
        values_clause = values_clause.rstrip(',')
        query = f"insert into email (`id`, `thread_id`, `refreshed_on`) " \
                f"values {values_clause} on duplicate key update refreshed_on=now()"
        cursor.execute(query)
        self.connection.commit()
        LOGGER.info("Saved message ids")

    def upsert_labels(self, messages):
        cursor = self.connection.cursor()
        values_clause = ""
        unlabeled_messages = []
        for body in messages:
            # Need to remove existing labels in the database to sync with the server
            if 'labelIds' not in body:
                unlabeled_messages.append(int(body['id'], 16))
                continue
            labels_json = json.dumps(body['labelIds'])
            labels_query = f"insert into message_label(`message_id`, `labels`, `refreshed_on`) " \
                           f"values ({int(body['id'], 16)}, '{labels_json}', now()) " \
                           f"on duplicate key update `labels`='{labels_json}', refreshed_on=now()"
            cursor.execute(labels_query)

        try:
            if unlabeled_messages:
                DBUtils.process_statement(cursor, "delete from message_label where `message_id` in (%s)",
                                          (unlabeled_messages,))
        except mysql.connector.errors.Error as ex:
            LOGGER.exception(f"Exception while syncing labels. Details: {ex}", exc_info=True)
        self.connection.commit()
        LOGGER.info("Synchronized message labels")

    def upsert_attributes_and_labels(self, messages):
        self.upsert_labels(messages)
        cursor = self.connection.cursor()
        for body in messages:
            attributes = dict(DEFAULT_HEADER_DICT)
            for header in body['payload']['headers']:
                if header['name'] in QUERYABLE_HEADERS:
                    attributes[header['name'].lower()] = header['value']
            attributes.update({'size_estimate': body['sizeEstimate'], 'history_id': body['historyId'],
                               'internal_date': datetime.fromtimestamp(int(body['internalDate']) // 1000),
                               'payload_headers': json.dumps(body['payload']['headers'])})
            arguments = (int(body['id'], 16), attributes['history_id'], attributes['internal_date'],
                         attributes['from'], attributes['to'], attributes['subject'],
                         attributes['cc'], attributes['bcc'], attributes['size_estimate'],
                         attributes['payload_headers'], attributes['history_id'])
            query = f"insert into email_attributes(`message_id`, `history_id`, `internal_timestamp`, `from`, `to`, " \
                    f"`subject`, `cc`, `bcc`, `size_estimate`, `payload_headers`, `refreshed_on`) values " \
                    f"(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) " \
                    f"on duplicate key update history_id = %s, refreshed_on=now()"
            cursor.execute(query, arguments)

        self.connection.commit()
        LOGGER.info("Saved message data")

    def fetch_message_ids(self, query_condition):
        """
        TODO: Google's batch modify API's limit is only 1000 message ids. Need to paginate with page_size = 1000.
        :param query_condition:
        :return:
        """
        cursor = self.connection.cursor()
        query = f"select message_id from email_attributes left join message_label using(message_id) " \
                f"where {query_condition}"
        cursor.execute(query)
        results = cursor.fetchall()
        results = [hex(value[0]).strip('0x') for value in results]
        return results

    def update_labels(self, add_label_ids, remove_label_ids, message_ids):
        """
        Add / remove message labels to the message_ids where applicable.
        That is, add label only when it doesn't exist and remove only when it does.
        """
        cursor = self.connection.cursor()
        message_ids = [int(item, 16) for item in message_ids]
        for label in remove_label_ids:
            query = f'''update message_label join email on message_label.message_id=email.id 
            set labels = json_remove(labels, json_unquote(json_search(labels, 'one', '{label}'))) 
            where email.id in (%s) and json_contains(labels, '"{label}"')'''
            DBUtils.process_statement(cursor, query, (message_ids,))
        for label in add_label_ids:
            query = f'''update message_label join email on message_label.message_id=email.id 
            set labels=json_array_append(labels, '$', '{label}') 
            where email.id in (%s) and not json_contains(labels, '"{label}"')'''
            DBUtils.process_statement(cursor, query, (message_ids,))
