from onyo._version import __version__
from pathlib import Path

from onyo.argparse_helpers import directory

args_onyo = {
    'opdir': dict(
        args=('-C', '--onyopath'),
        metavar='DIR',
        required=False,
        default=Path.cwd(),
        type=directory,
        help='Run Onyo commands from inside of DIR'),

    'debug': dict(
        args=('-d', '--debug'),
        required=False,
        default=False,
        action='store_true',
        help='Enable debug logging'),

    'version': dict(
        args=('-v', '--version'),
        action='version',
        version='%(prog)s {version}'.format(version=__version__),
        help="Print onyo's version and exit"),

    'quiet': dict(
        args=('-q', '--quiet'),
        required=False,
        default=False,
        action='store_true',
        help=(
            'Silence messages printed to stdout. Does not suppress interactive '
            'editors. Requires the --yes flag')),

    'yes': dict(
        args=('-y', '--yes'),
        required=False,
        default=False,
        action='store_true',
        help=(
            'Respond "yes" to any prompts. The --yes flag is required to use '
            '--quiet')),
}
