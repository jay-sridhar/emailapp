from lib.logger_utils import get_logger
from lib.db_utils import DBUtils
from models.email import EmailDAO
from lib.google_api import GoogleAPIHelper
from datetime import datetime
from dateutil.relativedelta import relativedelta
from config.settings import BULK_UPDATE_BATCH_SIZE

LOGGER = get_logger(__name__)

DATE_OPERATOR_MAPPING = {'less than': '>', 'more than': '<'}
SENT_MESSAGES_FILTER = "json_search(`labels`, 'one', 'SENT')"
TEXT_PREDICATE_TO_SQL_CONDITION_MAPPING = {'contains': lambda field, value: f'`{field}` like "%{value}%"',
                                           'equals': lambda field, value: f'`{field}` = "{value}"',
                                           'not equals': lambda field, value: f'`{field}` != "{value}"'
                                           }
TEXT_FIELDS = ('subject', 'from', 'to', 'cc', 'bcc')
DATE_FIELDS = ('date_received', 'date_sent')
FIELDS = TEXT_FIELDS + DATE_FIELDS
JOIN_STRING = {'any': ' or ',
               'all': ' and '
               }


def get_filter_for_date_field(field, operator, value):
    """
    :brief: This method returns the required filter conditions to apply the passed date field based rule
    :param field: a date field (date_sent / date_received)
    :param operator: less than / greater than
    :param value: a string that captures duration in days or months or years Eg. 1 day, 2 days, 2 months, etc,.
    :return:  a query filter condition that needs to be applied in the database to process the rule
    """
    values = value.split(' ')
    unit_value = int(values[0])
    time_unit = values[1].rstrip('s') + 's'
    date_time = datetime.now() - relativedelta(**{time_unit: unit_value})
    query_string = f'`internal_timestamp` {DATE_OPERATOR_MAPPING[operator]} "{date_time}"'
    query_string += f' and {SENT_MESSAGES_FILTER} '
    if field == 'date_received':
        query_string += 'is null'
    return query_string


class RulesProcessor(object):
    def __init__(self):
        self.__connection = None
        self.service = GoogleAPIHelper().get_service_instance()

    def _get_connection(self):
        self.__connection = DBUtils.renew_or_get_new_connection(self.__connection)

    def _close_connection(self):
        connection_id = self.__connection.connection_id
        try:
            self.__connection.close()
        finally:
            LOGGER.debug(f"Closed connection: {connection_id}")

    def _validate_rules(self, rules):
        """
        This method validates the structure of the rules to eliminate bad fields, predicates, values and actions
        :param rules: a dictionary containing the input rules to be applied
        :return: void
        :raises: ValueError if the input rules dictionary is invalid. See the exception message for more information.
        """
        if 'predicate' not in rules or rules['predicate'] not in ('any', 'all'):
            raise ValueError("Group predicate is invalid or missing. Should be one of 'any', 'all'.")
        for rule in rules.get('rules'):
            if 'field' not in rule or rule['field'] not in FIELDS:
                raise ValueError(f"Invalid or missing field in rule {rule}")
            if 'predicate' not in rule:
                raise ValueError(f"Missing predicate in rule {rule}")
            else:
                if rule['field'] in TEXT_FIELDS and rule['predicate'] not in TEXT_PREDICATE_TO_SQL_CONDITION_MAPPING:
                    raise ValueError(f"Unsupported predicate found in rule {rule}")
                if rule['field'] in DATE_FIELDS and rule['predicate'] not in DATE_OPERATOR_MAPPING:
                    raise ValueError(f"Unsupported predicate found in rule {rule}")
            if 'value' not in rule or not isinstance(rule['value'], str):
                raise ValueError(f"Invalid or missing value in rule {rule}")
        if not rules.get('rules'):
            raise ValueError("At least one rule condition is required")
        if 'action' not in rules or not isinstance(rules['action'], dict):
            raise ValueError("Action block is missing or invalid")
        action = rules['action']
        if not set(action.keys()).intersection(['addLabelIds', 'removeLabelIds']):
            raise ValueError("Action block should have at least one of 'set_labels' or 'unset_labels' array")

    def _get_query_condition_for_rules(self, rules):
        conditions_list = []
        for rule in rules.get('rules'):
            field, predicate, value = rule['field'], rule['predicate'], rule['value']
            # Get the field property which contains predicate mapper.
            # Predicate mapper maps to the function that should be applied for a given predicate
            # Fields are classified based the data type stored in the database
            if field in TEXT_FIELDS:
                conditions_list.append(TEXT_PREDICATE_TO_SQL_CONDITION_MAPPING[predicate](field, value))
            elif field in DATE_FIELDS:
                conditions_list.append(get_filter_for_date_field(field, predicate, value))
        group_predicate = rules['predicate']  # Finally apply the overall predicate - any or all
        query_condition = JOIN_STRING[group_predicate].join(conditions_list)
        return query_condition

    def _process_rule_actions(self, rules):
        self.service.users().messages().batchModify(userId='me')

    def process_rules(self, rules):
        try:
            self._validate_rules(rules)
        except ValueError as ex:
            LOGGER.error(f"Validation failed. Details: {ex}")
            raise
        query_condition = self._get_query_condition_for_rules(rules)
        LOGGER.debug(f"final query condition is {query_condition}")
        self._get_connection()
        message_ids_list = EmailDAO(self.__connection).fetch_message_ids(query_condition)
        self._close_connection()
        while True:
            # Process bulk update in batches (max batch size of Google's bulk update is 1000)
            request_body = {'ids': message_ids_list[:BULK_UPDATE_BATCH_SIZE-1],
                            'addLabelIds': rules['action'].get('addLabelIds') or [],
                            'removeLabelIds': rules['action'].get('removeLabelIds') or []
                            }
            LOGGER.debug(request_body)
            # Call Gmail's batch modify API
            response_body = self.service.users().messages().batchModify(userId='me',
                                                                        body=request_body).execute()
            if response_body:
                LOGGER.error(f"Error in processing rules. Details: {response_body}")
            else:
                LOGGER.info(f"Bulk modify succeeded!")
            message_ids_list = message_ids_list[BULK_UPDATE_BATCH_SIZE-1:]
            if not message_ids_list:
                break
