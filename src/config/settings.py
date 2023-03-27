import os

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

PYTHON_PATH = os.environ['PYTHONPATH']
TOKEN_FILE_PATH = f'{PYTHON_PATH}/config/token.json'
CREDENTIALS_FILE_PATH = f'{PYTHON_PATH}/config/credentials.json'
MAX_EMAIL_LIMIT = 1000
MYSQL_DB_CREDENTIALS = dict(user='appuser', password='$ecr3tpas5w0rD', host='127.0.0.1', database='google_mail')
QUERYABLE_HEADERS = ('From', 'Cc', 'Bcc', 'Subject', 'To')
DEFAULT_HEADER_DICT = dict(cc=None, bcc=None)
MESSAGE_FORMAT_FULL = 'full'  # Returns the full content of an email
MESSAGE_FORMAT_MINIMAL = 'minimal'  # To fetch only label ids of a previously fetched email
BATCH_FETCH_EMAIL_SIZE = 1000  # Google mail's batch processing limit
BULK_UPDATE_BATCH_SIZE = 1000
