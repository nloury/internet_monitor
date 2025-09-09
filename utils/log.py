import logging
import inspect
import datetime as dt
from app import LOGGING_PATH


class CustomLogging(logging.Logger):
    """Extension of logging module"""
    def __init__(self,
                 name,
                 console_level: str='info',
                 file_level: str='all',
                 ):
        super().__init__(name, level=logging.NOTSET)  # initialize at NOT SET, levels set in handlers
        self._console_level = console_level
        self._file_level = file_level

        # set mapping of conversion from string / also used to hold custom level values
        self._level_map = {
            'critical': {'value': logging.CRITICAL, 'color': 'bold_red'}
            , 'error': {'value': logging.ERROR, 'color': 'red'}
            , 'warning': {'value': logging.WARNING, 'color': 'yellow'}
            , 'info': {'value': logging.INFO, 'color': 'white'}
            , 'debug': {'value': logging.DEBUG, 'color': 'grey'}
            , 'notset': {'value': logging.NOTSET, 'color': 'grey'}
            , 'not_set': {'value': logging.NOTSET, 'color': 'grey'}
            , 'off': {'value': 101, 'color': 'bold_red'}  # turn off logging
            , 'all': {'value': -1, 'color': 'bold_red'}  # log everything
        }

        self._post_init()

    def add_log(self,
                base_message=None,
                level: str='info',
                caller_depth: int=0,
                add_tag: str=None,
                override_message: str=None):
        """
        Add message to logger + caller
        add_tag will add some custom text to end of message
        """
        if override_message is None:
            caller = self._get_caller(depth=caller_depth)
            tag_suffix = f" > {add_tag}" if add_tag else ''
            message = f"{base_message} - {caller}{tag_suffix}"
        else:
            message = override_message
        super().log(level=self._level_value(level), msg=message)

    def _post_init(self):
        """Sets initial parameters / handlers"""
        self._add_logging_level(level_number=5, level_name='debug_verbose', color='grey')
        self._add_logging_level(level_number=25, level_name='complete', color='green')

        if not self.handlers:
            self._console_handler()
            self._file_handler()

    def _console_handler(self):
        """Sets up handler for logging to console"""
        level = self._console_level
        if level != 'off':
            handler = logging.StreamHandler()
            handler.setFormatter(ConsoleFormatter(
                fmt='%(message)s - %(asctime)s'
                , datefmt='%#I:%M:%S %p'
                , color_map={i['value']: i['color'] for i in self._level_map.values()}
            ))

            handler.setLevel(self._level_value(level))
            self.addHandler(handler)

    def _file_handler(self):
        """Sets up handler for logging to a file in [base_director].logging with filename = logger __name__"""
        level = self._file_level
        if level != 'off':
            fln = fr"{LOGGING_PATH}\{self.name}.log"
            self._log_separator(fln)

            handler = logging.FileHandler(fln, mode='a')
            handler.setFormatter(FileFormatter(
                fmt='%(levelname)s - %(message)s - %(asctime)s'
                , datefmt='%#I:%M:%S.%f %p', override_timestamp=True
            ))

            handler.setLevel(self._level_value(level))
            self.addHandler(handler)

    @staticmethod
    def _log_separator(log_file):
        """Adds a separator and title to the log file to differentiate log instances"""
        title = f"{dt.datetime.now().strftime('%Y-%m-%d %#I:%M:%S %p')}"
        separator = f"\n{'=' * 50}\n{title}\n{'=' * 50}\n"
        with open(log_file, 'a') as f:
            f.write(separator)

    def _add_logging_level(self, level_number, level_name, color):
        """
        Add custom levels in addition to defaults:
        NOTSET=0
        DEBUG=10
        INFO=20
        WARNING=30
        ERROR=40
        CRITICAL=50
        """
        self._level_map[level_name.lower()] = {'value': level_number, 'color': color}
        logging.addLevelName(level_number, level_name.upper())

    def change_level(self, level):
        """Change logging level after init"""
        self.setLevel(level=self._level_value(level))

    @staticmethod
    def _get_caller(depth):
        """
        Identify function that invokes class/function for tracking/debugging
        depth_offset = 4 (depth=1) will return caller of caller (i.e. game calls throttle calls logger > return game)
        depth_offset = 3 (depth=0) would return throttle (or function that calls logger)
        depth_offset = 2 (depth=-1) or lower returns function of logging class
        """
        depth_offset = 2 + depth
        exclude_module_substrings = ['.threading', 'concurrent.']
        call_stack = inspect.stack()

        for frame in call_stack[depth_offset:]:  # skip n callers (0 is current file)
            module = inspect.getmodule(frame.frame)
            if module:
                module_name = module.__name__
                excluded = any(substr in module_name for substr in exclude_module_substrings)
                if not excluded and module_name != __name__:
                    return f"{module_name}.{frame.function} (line {frame.lineno})"

        # if none found, return unknown
        return "Unknown Caller"

    def _level_value(self, level: str):
        """Convert string to logger level"""
        level = level.lower()
        if level not in self._level_map:
            level = 'info'  # default
        return self._level_map[level]['value']


class ConsoleFormatter(logging.Formatter):
    """Create formatted logging for console"""
    def __init__(self, fmt=None, datefmt=None, color_map: dict=None):
        super().__init__(fmt=fmt, datefmt=datefmt, style='%')
        bold = "1;"  # add after [ and before color code / ; is separator
        self._colors = {
            'white': "\x1b[37m"
            , 'grey': "\x1b[90m"
            , 'blue': "\x1b[34m"
            , 'green': "\x1b[32m"
            , 'bold_green': f"\x1b[{bold}32m"
            , 'yellow': "\x1b[33;20m"
            , 'red': "\x1b[31m"
            , 'bold_red': f"\x1b[{bold}31m"
        }
        self._reset = "\x1b[0m"

        self._color_map = {
            logging.DEBUG: 'grey'
            , logging.INFO: 'white'
            , logging.WARNING: 'yellow'
            , logging.ERROR: 'red'
            , logging.CRITICAL: 'bold_red'
        } if color_map is None else color_map

    def format(self, record):
        color_name = self._color_map.get(record.levelno, 'white')
        color = self._colors[color_name]
        log_fmt = f"{color}{self._fmt}{self._reset}"  # Apply color to the entire format
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)

class FileFormatter(logging.Formatter):
    """Create formatted logging for file"""
    def __init__(self, fmt=None, datefmt=None, override_timestamp: bool=True):
        super().__init__(fmt=fmt, datefmt=datefmt, style='%')
        self._override_timestamp = override_timestamp

    def formatTime(self, record, datefmt=None):
        if self._override_timestamp:
            return dt.datetime.now().strftime(datefmt)  # Custom format for time
        return super().formatTime(record, datefmt)  # Default behavior

    def format(self, record):
        if self._override_timestamp:
            created_time = dt.datetime.fromtimestamp(record.created)
            record.asctime = f"{created_time.strftime('%#I:%M:%S.%f %p')}"  # replace asctime with custom format
        return super().format(record)
