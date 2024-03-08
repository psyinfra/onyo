shared_arg_depth = dict(
    args=('-d', '--depth'),
    metavar='DEPTH',
    type=int,
    required=False,
    default=0,
    help="""
        Descend up to DEPTH levels into the directories specified. DEPTH=0
        descends recursively without limit.
    """
)

shared_arg_match = dict(
    args=('-M', '--match'),
    metavar='MATCH',
    nargs='+',
    type=str,
    default=None,
    help="""
        Matching criteria for assets in the form ``KEY=VALUE``, where VALUE is a
        python regular expression. Pseudo-keys such as ``path`` can also be
        used. Special values supported are:
        - ``<dict>``
        - ``<list>``
        - ``<unset>``
    """
)

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
