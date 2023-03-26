import logging
import os
from logging.config import dictConfig

LOG_PATH = os.path.dirname(os.path.realpath(__file__)) + '/../../logs/combined_log'

LOG_SETTINGS = {'version': 1,
                'disable_existing_loggers': False,

                'formatters': {
                    'standard': {
                        'format': "%(asctime)s %(levelname)-8s%(module)s:%(lineno)s:%(funcName)s %(message)s",
                    },
                },

                'handlers': {
                    'default': {
                        'level': 'DEBUG',
                        'class': 'logging.FileHandler',
                        'formatter': 'standard',
                        'filename': LOG_PATH

                    }
                },
                'loggers': {

                },
                'root': {
                    'level': 'DEBUG',
                    'handlers': ['default']
                }
                }
dictConfig(LOG_SETTINGS)


def get_logger(logger_val):
    return logging.getLogger(logger_val)
