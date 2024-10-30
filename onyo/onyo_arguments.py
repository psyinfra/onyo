import sys
from pathlib import Path

from onyo._version import __version__
from onyo.lib.ui import ui


def get_cwd() -> Path:
    # HACK: avoid dumping a traceback to the user, if CWD doesn't exist.
    # Needed early on, before we have a general exception handler.
    try:
        return Path.cwd()
    except FileNotFoundError as e:
        ui.error(e)
        sys.exit(1)


args_onyo = {
    'opdir': dict(
        args=('-C', '--onyopath'),
        metavar='DIR',
        required=False,
        default=get_cwd(),
        help=r"""
            Run Onyo from **DIR** instead of the current working directory.
        """
    ),

    'debug': dict(
        args=('-d', '--debug'),
        required=False,
        default=False,
        action='store_true',
        help=r"""
            Enable debug logging.
        """
    ),

    'version': dict(
        args=('-v', '--version'),
        action='version',
        version='%(prog)s {version}'.format(version=__version__),
        help=r"""
            Print Onyo's version and exit.
        """
    ),

    'quiet': dict(
        args=('-q', '--quiet'),
        required=False,
        default=False,
        action='store_true',
        help=r"""
            Silence messages printed to stdout; does not suppress interactive
            editors. Requires the ``--yes`` flag.
        """
    ),

    'yes': dict(
        args=('-y', '--yes'),
        required=False,
        default=False,
        action='store_true',
        help=r"""
            Respond "yes" to any prompts.
        """
    ),
}
