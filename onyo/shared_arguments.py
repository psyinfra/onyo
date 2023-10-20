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
    action='append',
    type=str,
    help=(
        'Use the given MESSAGE as the commit message (rather than the '
        'default). If multiple -m options are given, their values are '
        'concatenated as separate paragraphs'))
