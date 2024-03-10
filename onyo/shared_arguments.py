shared_arg_message = dict(
    args=('-m', '--message'),
    metavar='MESSAGE',
    action='append',
    type=str,
    help="""
        Use the given MESSAGE as the commit message (rather than the default).
        If multiple ``-m`` options are given, their values are concatenated as
        separate paragraphs.
    """
)
