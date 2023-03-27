import argparse
from config.settings import MAX_EMAIL_LIMIT
from businesslogic.email_processor import EmailProcessor


class Downloader(object):
    def __init__(self, arguments):
        self.max_fetch_limit = arguments.m[0] if arguments.m else MAX_EMAIL_LIMIT
        self.fetch_mode = arguments.f[0] if arguments.f else 'full'
        self.parameter_dict = dict()
        if arguments.l:
            self.parameter_dict['labelIds'] = arguments.l
        if arguments.q:
            self.parameter_dict['q'] = arguments.q[0]
        if arguments.s:
            self.parameter_dict['maxResults'] = arguments.s[0]

    def download(self):
        EmailProcessor().download_emails_to_db(self.max_fetch_limit, self.fetch_mode, **self.parameter_dict)
        print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='This script downloads given emails from your Gmail account. '
                    'Running this script without arguments would fetch all the emails '
                    'and save it to the MySQL database.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', nargs=1, metavar='fetch_mode', choices=['full', 'minimal'],
                        help='Specify the fetch mode. '
                             '"full" is meant to be used for the first time synchronization or when '
                             'fetching newer emails;\nTo update / refresh already stored emails, use "minimal"')
    parser.add_argument('-m', nargs=1, type=int, metavar='max_limit',
                        help='Specify a maximum limit for the number of emails that should be fetched & saved.',
                        default=None)
    parser.add_argument('-s', nargs=1, type=int, metavar='page_size',
                        help='Specify the page size (when paging over a large result)', default=None)
    parser.add_argument('-q', nargs=1, metavar='querystring',
                        help='Google email search query filter to be applied while fetching emails.\n '
                             'Refer https://support.google.com/mail/answer/7190?hl=en.')
    parser.add_argument('-l', nargs='+', metavar='labels',
                        help='Specify one (or more) labels that should be filtered')

    args = parser.parse_args()
    Downloader(args).download()
