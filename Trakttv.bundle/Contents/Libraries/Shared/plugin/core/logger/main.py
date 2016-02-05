from plugin.core.constants import PLUGIN_IDENTIFIER
from plugin.core.environment import Environment
from plugin.core.helpers.variable import md5
from plugin.core.logger.filters import FrameworkFilter, AuthorizationFilter, RequestsFilter
from plugin.core.logger.handlers.error_reporter import ERROR_REPORTER_HANDLER, RAVEN

from logging.handlers import RotatingFileHandler
import logging

LOG_FORMAT = '%(asctime)-15s - %(name)-32s (%(thread)x) :  %(levelname)s (%(name)s:%(lineno)d) - %(message)s'
LOG_OPTIONS = {
    'plex':                         'libraries',
    'plex_activity':                'libraries',
    'plex_metadata':                'libraries',
    'raven':                        'libraries',
    'requests':                     'libraries',
    'trakt':                        'libraries',

    'peewee':                       'peewee',
    'peewee_migrate':               'peewee',

    'com.plexapp.plugins.trakttv':  'plugin',
    'plugin':                       'plugin',

    'pyemitter':                    'pyemitter'
}

TRACE = 5

log = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    def __init__(self, handler):
        super(LogHandler, self).__init__()

        self.handler = handler

        # Update formatter for log file
        self.handler.formatter._fmt = LOG_FORMAT

    @property
    def baseFilename(self):
        return self.handler.baseFilename

    def emit(self, record):
        return self.handler.emit(record)


class LoggerManager(object):
    @staticmethod
    def get_handler():
        logger = logging.getLogger(PLUGIN_IDENTIFIER)

        for h in logger.handlers:
            if type(h) is RotatingFileHandler:
                logger.handlers.remove(h)
                return LogHandler(h)

        return None

    @classmethod
    def setup(cls, storage=True):
        cls.setup_logging(storage)
        cls.setup_raven()

        log.debug('Initialized logging (storage: %r)', storage)

    @staticmethod
    def setup_logging(storage=True):
        # Setup root logger
        rootLogger = logging.getLogger()

        # Set filters
        rootLogger.filters = [
            FrameworkFilter()
        ]

        # Set handlers
        rootLogger.handlers = [
            LOG_HANDLER,
            ERROR_REPORTER_HANDLER
        ]

        if storage:
            # Only import the error storage handler if enabled (so `apsw` isn't required)
            from plugin.core.logger.handlers.error_storage import ERROR_STORAGE_HANDLER

            rootLogger.handlers.append(ERROR_STORAGE_HANDLER)

        # Set level
        rootLogger.setLevel(logging.DEBUG)

    @staticmethod
    def setup_raven():
        # Set client name to a hash of `machine_identifier`
        RAVEN.name = md5(Environment.platform.machine_identifier)

        RAVEN.tags.update({
            'server.version': Environment.platform.server_version
        })

    @classmethod
    def refresh(cls):
        for name, option in LOG_OPTIONS.items():
            logger = logging.getLogger(name)

            # Retrieve logger level, check if it has changed
            level = cls.get_level(option)

            if level == logger.level:
                continue

            # Update logger level
            log.debug('Changed %r logger level to %s', name, logging.getLevelName(level))

            logger.setLevel(level)

    @staticmethod
    def get_level(option):
        # Try retrieve preference
        try:
            value = Environment.prefs['level_%s' % option]
        except KeyError:
            # Default to "plugin" preference
            value = Environment.prefs['level_plugin']

        # Parse labels into level attributes
        if value == 'ERROR':
            return logging.ERROR

        if value == 'WARN' or value == 'WARNING':
            return logging.WARNING

        if value == 'INFO':
            return logging.INFO

        if value == 'DEBUG':
            return logging.DEBUG

        if value == "TRACE":
            return TRACE

        log.warn('Unknown logging level "%s"', value)
        return logging.DEBUG

# Get the logging file handler
LOG_HANDLER = LoggerManager.get_handler()
LOG_HANDLER.addFilter(AuthorizationFilter())
LOG_HANDLER.addFilter(RequestsFilter())
