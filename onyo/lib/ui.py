import logging
import sys
from pathlib import Path
from typing import Union

from traceback import format_exc

# TODO: remove "Console" prints in commands.py and command_utils.py
#       - add rich to print function?
# TODO: remove logging in other onyo-places?

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')
log.setLevel(logging.INFO)


class UI(object):
    """
    """

    def __init__(self,
                 debug: bool = False,
                 quiet: bool = False,
                 yes: bool = False) -> None:  # TODO: interactive="defaults or autodetect?"):
        """
        Initialize the User Interface object for user communication of Onyo.
        """
        self.debug = debug
        self.quiet = quiet
        self.yes = yes

        # set external logging level
        logging.basicConfig(level=logging.ERROR)
        # set internal logging level
        self.logger = logging.getLogger('onyo')
        self.logger.setLevel(level=logging.INFO)

    def set_debug(self,
                  debug: bool = False) -> None:
        """
        Set the log level to activate debug mode.
        """
        if debug:
            self.debug = debug
            self.logger.setLevel(logging.DEBUG)

    def set_quiet(self,
                  quiet: bool = False) -> None:
        """
        Set the quiet parameter to suppress terminal output.
        """
        if quiet and not self.yes:
            raise ValueError("The --quiet flag requires --yes.")
        self.quiet = quiet

    def set_yes(self,
                yes: bool = False) -> None:
        """
        Set `yes` to answer all requests to user with "yes".
        """
        self.yes = yes

    def error(self,
              error: Union[str, Exception],
              end: str = "\n") -> None:
        """
        Print an error message, if the ui is not set to `quiet`.
        """
        if not self.quiet:
            print(f"ERROR: {error}", file=sys.stderr, end=end)
        # ....
        # if isinstance(error, Exception):
        #    for path in error.paths:
        #        print()
        # elif isinstance(error, Exception):
            # ....
        #    return
        if self.debug:
            # TODO: print whole error stack, not just message
            log.error(format_exc())
            return

    def log(self,
            message: str) -> None:
        """
        """
        # TODO: signature like other logger
        # self.logger.log(*args, **kwargs)
        self.logger.info(message)

    def log_debug(self,
                  message: str) -> None:
        """
        Debug logging
        """
        if self.debug:
            self.logger.debug(message)

    def print(self,
              message: Union[str, list, Path] = "\n",
              end: str = "\n",
              sep: str = "\n") -> None:
        """
        Print a message, if the ui is not set to `quiet`.
        """
        if not self.quiet:
            if isinstance(message, list):
                print(sep.join(message), end=end)
            else:
                print(str(message), end=end)

    def request_user_response(self,
                              question: str) -> bool:
        """
        Opens a dialog for the user and reads an answer from the keyboard.
        Returns True when user answers yes, False when no, and asks again if the
        input is neither.

        If the UI is set to `yes=True` returns automatically True, without
        asking the user.
        """
        # TODO: should tty always return true?
        # if self.yes or not sys.stdout.isatty():
        if self.yes:
            return True

        while True:
            answer = input(question)
            if answer in ['y', 'Y', 'yes']:
                return True
            elif answer in ['n', 'N', 'no']:
                return False
        return False
