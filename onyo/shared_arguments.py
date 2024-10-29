shared_arg_message = dict(
    args=('-m', '--message'),
    metavar='MESSAGE',
    action='append',
    type=str,
    help=r"""
        Append **MESSAGE** to the commit message.
        If multiple ``--message`` options are given, their values are
        concatenated as separate paragraphs.
    """
)

shared_arg_no_auto_message = dict(
    args=('--no-auto-message',),
    action='store_true',
    help=r"""
        Do not auto-generate the commit message subject.
        If no **MESSAGE** is given, the subject line
        will be ``[Empty subject]``.
        This does not disable the inventory operations record
        at the end of a commit message.
        The default is configured via 'onyo.commit.auto-message'.
    """
)
