import logging
import sys
import traceback
from typing import Any

from rich.console import Console

from onyo.lib.exceptions import UIInputError
logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


# TODO:
# - Logging: Provide Formatter/Handler raise default level and maybe target file (~/.onyo/logs/  (config))?
#          logging errors -> print (rich) + actual log? Nope. Do both from within code - > different phrasing/details
#          special log_exception? Log when raised or when catched? (we have the traceback!)
# - How does the quiet flag behave (with and w/o to-be- introduced non-interactive)? What about "result" outputs that
# could be piped? Does it suppress everything but these? How to distinguish? Commands could return (or yield) a
# result object.
# - main.py could tell `UI` that we are in CLI (Paths -> render relative to CWD, otherwise absolute)


class UI(object):
    r"""An object to handle user interaction.

    Includes printing, errors, requests, etc.
    """

    def __init__(self,
                 debug: bool = False,
                 quiet: bool = False,
                 yes: bool = False) -> None:
        # TODO: interactive mode with default values or autodetecting tty? And
        # should this be unified with the whole business of rich-coloring etc?
        r"""Initialize the User Interface object for user communication of Onyo.

        Parameters
        ----------
        debug
            Activate the debug mode to display additional information via Onyo,
            and to print the full traceback stack if errors occur.
        quiet
            Suppress all output. Requires ``yes=True``.
        yes
            Answer "yes" to all user-interactive prompts.
        """

        # set the attributes of the UI object
        self.logger: logging.Logger = logging.getLogger('onyo')
        r"""The logger to display information with."""
        self.quiet: bool = quiet
        r"""Suppress all output. Requires ``yes=True``.
        """
        self.yes: bool = yes
        r"""Answer "yes" to all user-interactive prompts."""

        self.debug = debug
        # set the debug level
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        self.stderr_console = Console(stderr=True, highlight=False, soft_wrap=True)
        self.stdout_console = Console(stderr=False, highlight=False, soft_wrap=True)

        # count reported errors; this allows to assess whether errors occurred
        # even when no exception bubbles up.
        self.error_count: int = 0

    def set_debug(self,
                  debug: bool = False) -> None:
        r"""Toggle debug mode.

        Parameters
        ----------
        debug
            Activate debug mode, and configure the log level of the logger.
        """

        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

    def set_quiet(self,
                  quiet: bool = False) -> None:
        r"""Toggle quiet mode.

        Parameters
        ----------
        quiet
            Suppress all output. Requires ``yes=True``.

        Raises
        ------
        ValueError
            Tried to activate quiet mode without ``yes=True``.
        """

        if quiet and not self.yes:
            # TODO: This condition would need to be triggered from __init__ as well.
            raise ValueError("The --quiet flag requires --yes.")

        self.quiet = quiet

    def set_yes(self,
                yes: bool = False) -> None:
        r"""Toggle auto-response "yes" to all user-interactive prompts.

        Parameters
        ----------
        yes
            Answer "yes" to all user-interactive prompts.
        """

        self.yes = yes

    def format_traceback(self,
                         e: Exception) -> str:
        r"""Format an Exception's traceback suitable for logging.

        Parameters
        ----------
        e
            Exception to extract the traceback from.
        """

        tb = traceback.TracebackException.from_exception(
            e, lookup_lines=True, capture_locals=False
        )
        if e.__traceback__:
            traceback.clear_frames(e.__traceback__)

        return ''.join(tb.format())

    def error(self,
              error: str | Exception,
              end: str = '\n') -> None:
        r"""Print an error message.

        When provided, Exceptions will print tracebacks in debug mode.

        Nothing is printed when :py:data:`quiet` is ``True``.

        Parameters
        ----------
        error
            Error message to print. Exceptions will have their ``message``
            printed and traceback added to the debug log.
        end
            String to end the message with. Default is ``"\n"``.
        """

        self.error_count += 1
        if not self.quiet:
            print(f"ERROR: {error}", file=sys.stderr, end=end)
        if isinstance(error, Exception):
            self.log_debug(self.format_traceback(error))

    def log(self,
            message: str,
            level: int = logging.INFO) -> None:
        r"""Log a message.

        Parameters
        ----------
        message
            Message to log.
        level
            Level to log at.
        """

        self.logger.log(level=level, msg=message)

    def log_debug(self,
                  *args,
                  **kwargs) -> None:
        r"""Log at ``DEBUG`` level.

        Parameters
        ----------
        args
            Passed to :py:meth:`logging.Logger.debug`
        kwargs
            Passed to :py:meth:`logging.Logger.debug`
        """

        self.logger.debug(*args, **kwargs)

    def print(self,
              *args,
              **kwargs) -> None:
        r"""Print a message.

        Nothing is printed when :py:data:`quiet` is ``True``.

        Parameters
        ----------
        args
            Passed to builtin :py:func:`print`
        kwargs
            Passed to builtin :py:func:`print`
        """

        if not self.quiet:
            print(*args, **kwargs)

    def request_user_response(self,
                              question: str,
                              default: str = 'yes',
                              answers: list[tuple] | None = None) -> Any:
        r"""Print a question and read a response from ``stdin``.

        When :py:data:`yes` is ``True``, the ``default`` answer is used without
        prompting the user.

        When a user's response matches any of the ``answers``, the corresponding
        return value is returned. If the user's response doesn't match any
        answers, the question is repeated.

        Parameters
        ----------
        question
            Question that the user should respond to.
        default
            Default answer used when the answer is empty (user hit only enter)
            or :py:data:`yes` is ``True``.
        answers
            List of answers and corresponding value to return for those answers.
            The first element is the return value, and the second is a list of
            strings.

            Default is 'y', 'Y', or 'yes' return ``True`` and 'n', 'N', or 'no'
            return ``False``.
        """

        # TODO: When use of rich is streamlined, we'd probably want to change how the default
        #       and possible ways to respond are indicated.
        answers = answers or [(True, ['y', 'Y', 'yes']),
                              (False, ['n', 'N', 'no'])]
        question += f"[Default: {default}] "
        while True:
            if self.yes:
                answer = default
            else:
                try:
                    answer = input(question) or default  # empty answer (hit return) gives the default answer
                except EOFError as e:
                    raise UIInputError("Failed to read user input.") from e

            for response, options in answers:
                if answer in options:
                    return response

            self.log_debug(f"Invalid user response: {answer}. Retry.")

    def rich_print(self, *args, **kwargs) -> None:
        r"""Print via the ``rich`` module.

        A proxy for ``rich.Console.print``.

        Parameters
        ----------
        stderr
            Bool to use a ``stderr`` Rich Console instead of a ``stdout`` Rich
            Console.
        args
            Passed to :py:func:`rich.Console.print`
        kwargs
            Passed to :py:func:`rich.Console.print`
        """

        # TODO: This should be fused with the regular `UI.print` and `UI.error`,
        #       so that `UI` decides whether and how to use `rich`. The stderr
        #       option should consequently be replaced by `print`'s standard
        #       `file` option.

        if not self.quiet:
            stderr = kwargs.pop('stderr') if 'stderr' in kwargs.keys() else False
            console = self.stderr_console if stderr else self.stdout_console
            console.print(*args, **kwargs)


# create a shared UI object to import by classes/commands
ui = UI()
