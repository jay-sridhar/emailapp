import re

import mysql.connector

from config.settings import MYSQL_DB_CREDENTIALS
from lib.logger_utils import get_logger

LOGGER = get_logger(__name__)


class DBUtils(object):
    @staticmethod
    def get_new_connection(autocommit=True):
        try:
            connection_params = dict(MYSQL_DB_CREDENTIALS)
            connection_params['autocommit'] = autocommit
            connection = mysql.connector.connect(**connection_params)
            LOGGER.debug(f"Created new connection with id: {connection.connection_id}")
            return connection
        except (mysql.connector.DatabaseError,
                mysql.connector.OperationalError,
                mysql.connector.PoolError) as ex:
            LOGGER.exception("Exception while obtaining connection. Details %s", ex, exc_info=True)

    @staticmethod
    def renew_or_get_new_connection(connection):
        if not connection:
            connection = DBUtils.get_new_connection(autocommit=False)
        if not connection.is_connected():
            connection.ping(reconnect=True)
        return connection

    @staticmethod
    def _formatargs(query, arguments):
        if isinstance(arguments, tuple):
            arguments = list(arguments)
        if isinstance(arguments, list):
            end_idx = 0
            query = re.sub('\([ ]*%[ ]*s[ ]*\)', '(%s)', query)
            for i, value in enumerate(arguments):
                if isinstance(value, tuple) or isinstance(value, list):
                    len_ = len(value)
                    find_idx = query.index('(%s)', end_idx)
                    end_idx = find_idx + len("(%s)")
                    query = list(query)
                    query[find_idx:end_idx] = '(%s' + ', %s' * (len_ - 1) + ')'
                    query = ''.join(query)
                    arguments.remove(value)
                    for ele in value:
                        arguments.insert(i, ele)
                        i += 1
        return query, arguments

    @staticmethod
    def process_statement(cursor, query, arguments):
        query, arguments = DBUtils._formatargs(query, arguments)
        cursor.execute(query, arguments)
