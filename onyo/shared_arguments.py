def directory(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def file(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def git_config(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def path(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def template(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


shared_arg_depth = dict(
    args=('-d', '--depth'),
    metavar='DEPTH',
    type=int,
    required=False,
    default=0,
    help=(
        'Descent up to DEPTH levels into directories specified. DEPTH=0 '
        'descends recursively without limit'))

shared_arg_dry_run = dict(
    args=('-n', '--dry-run'),
    required=False,
    default=False,
    action='store_true',
    help='Perform a non-interactive trial-run without making any changes')

shared_arg_filter = dict(
    args=('-f', '--filter'),
    metavar='FILTER',
    nargs='+',
    type=str,
    default=None,
    help=(
        'Add a filter to only show assets matching KEY=VALUE. Multiple '
        'filters, regular expressions, and pseudo-keys can be used.'))

shared_arg_message = dict(
    args=('-m', '--message'),
    metavar='MESSAGE',
    nargs=1,
    action='append',
    type=str,
    help=(
        'Use the given MESSAGE as the commit message (rather than the '
        'default). If multiple -m options are given, their values are '
        'concatenated as separate paragraphs')
)

shared_arg_quiet = dict(
    args=('-q', '--quiet'),
    required=False,
    default=False,
    action='store_true',
    help=(
        'Silence messages printed to stdout. Does not suppress interactive '
        'editors. Requires the --yes flag')
)

shared_arg_yes = dict(
    args=('-y', '--yes'),
    required=False,
    default=False,
    action='store_true',
    help=(
        'Respond "yes" to any prompts. The --yes flag is required to use '
        '--quiet')
)
