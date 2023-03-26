MAX_EMAIL_LIMIT = 1000
MYSQL_DB_CREDENTIALS = dict(user='appuser', password='$ecr3tpas5w0rD', host='127.0.0.1', database='google_mail')
END_OF_REQUEST_DELIMITER = 'end_of_request'
QUERYABLE_HEADERS = ('From', 'Cc', 'Bcc', 'Subject', 'To')
DEFAULT_HEADER_DICT = dict(cc=None, bcc=None)
MESSAGE_FORMAT_FULL = 'full'  # Returns the full content of an email
MESSAGE_FORMAT_MINIMAL = 'minimal'  # To fetch only label ids of a previously fetched email
BATCH_FETCH_EMAIL_SIZE = 20
BULK_UPDATE_BATCH_SIZE = 5