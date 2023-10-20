import logging
import os
import sys
import traceback
from typing import Union


logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


class UI(object):
    """
    An object handling user interaction, including printing, errors, requests,
    and others.

    Attributes
    ----------
    log: Logger
        The logger to display information with.
    quiet: boolean
        Activate the quiet mode (requires that `yes=True`).
        This will suppresses all output generation.
    yes: boolean
        Activate the yes mode, which suppresses all interactive requests to the
        user, and instead answers them with yes.
    """

    def __init__(self,
                 debug: bool = False,
                 quiet: bool = False,
                 yes: bool = False) -> None:
        # TODO: interactive mode with default values or autodetecting tty? And
        # should this be unified with the whole business of rich-coloring etc?
        """
        Initialize the User Interface object for user communication of Onyo.

        Parameters
        ----------
        debug: boolean
            Activate the debug mode to display additional information via Onyo,
            and to print the full traceback stack if errors occur.

        quiet: boolean
            Activate the quiet mode (requires that `yes=True`) to suppress all
            output generation.

        yes: boolean
            Activate the yes mode to suppress all interactive requests to the
            user, and instead answers them with yes.
        """
        # set the the attributes of the UI object
        self.quiet = quiet
        self.yes = yes
        self.logger = logging.getLogger('onyo')

        self.debug = debug
        # set the debug level
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def set_debug(self,
                  debug: bool = False) -> None:
        """
        Set the log level to activate debug mode.

        Parameters
        ----------
        debug: boolean
            Activates debug mode, and configures the log level of the logger.
        """
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def set_quiet(self,
                  quiet: bool = False) -> None:
        """
        Set `quiet` to suppress terminal output.

        Parameters
        ----------
        quiet: boolean
            `True` suppresses of all user output.
            Requires `yes` mode to be active.

        Raises
        ------
        ValueError
            If tried to activate quiet mode without `yes=True`.
        """
        if quiet and not self.yes:
            # TODO: This condition would need to be triggered from __init__ as well.
            raise ValueError("The --quiet flag requires --yes.")
        self.quiet = quiet

    def set_yes(self,
                yes: bool = False) -> None:
        """
        Set `yes` to answer all requests to user with "yes".

        Parameters
        ----------
        yes: boolean
            Activate yes mode, which suppresses all user requests and answers
            them positively. Allows the activation of the quiet mode.
        """
        self.yes = yes

    def error(self,
              error: Union[str, Exception],
              end: str = os.linesep) -> None:
        """
        Print an error message, if the UI is not set to `quiet`.

        Parameters
        ----------
        error: string or Exception
            Prints the string, or the message of an error.
            If debug mode is activated, displays the full traceback of an
            exception.

        end: str
            Specify the string at the end of prints.
            Per default, prints end with a line break.
        """
        if not self.quiet:
            print(f"ERROR: {error}", file=sys.stderr, end=end)
        if isinstance(error, Exception):
            tb = traceback.TracebackException.from_exception(
                error, lookup_lines=True, capture_locals=False
            )
            if error.__traceback__:
                traceback.clear_frames(error.__traceback__)
            self.logger.debug(''.join(tb.format()))

    def log(self,
            message: str) -> None:
        """
        Display a message via the logger if the log level is at least `info`.

        Parameters
        ----------
        message: string
            The string to display as an info.
        """
        self.logger.info(message)

    def log_debug(self, *args, **kwargs) -> None:
        """
        Display debug information if debug mode is activated.

        Parameters
        ----------
        args:
            passed to Logger.debug
        kwargs:
            passed to Logger.debug
        """
        self.logger.debug(*args, **kwargs)

    def print(self, *args, **kwargs) -> None:
        """
        Print a message, if the UI is not set to `quiet`.

        Parameters
        ----------
        args, kwargs: passed on to builtin `print`
        """
        if not self.quiet:
            print(*args, **kwargs)

    def request_user_response(self,
                              question: str) -> bool:
        """
        Opens a dialog for the user and reads an answer from the keyboard.
        Returns True when user answers yes, False when no, and asks again if the
        input is neither.

        If the UI is set to `yes=True` returns automatically True, without
        asking the user.

        Parameters
        ----------
        question: string
            A string asking the question to which the user should respond.
        """
        if self.yes:
            return True

        while True:
            answer = input(question)
            if answer in ['y', 'Y', 'yes']:
                return True
            elif answer in ['n', 'N', 'no']:
                return False


# create a shared UI object to import by classes/commands
ui = UI()
