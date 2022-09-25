#!/usr/bin/env python3

from onyo import commands  # noqa: F401
from onyo.utils import parse_args

import logging
import sys

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.INFO)


def main():
    parser = parse_args()

    # NOTE: this unfortunately located hack is so "onyo config" args will pass
    # through uninterpreted. Otherwise, anything starting with - or -- errors as
    # an unknown option flag.
    # nargs=argparse.REMAINDER is in theory the correct solution, but is
    # deprecated as of Python 3.8 (due to being buggy) and did not work for me
    # in 3.10.
    # For more information, see https://docs.python.org/3.10/library/argparse.html#arguments-containing
    if 'config' in sys.argv:
        if not any(x in sys.argv for x in ['-h', '--help']):
            index = sys.argv.index('config')
            sys.argv.insert(index + 1, '--')

    args = parser.parse_args()

    if args.onyopath:
        onyo_root = args.onyopath

    # TODO: Do onyo fsck here, test if onyo_root exists, .onyo exists, is git repo, other checks

    if args.debug:
        logger.setLevel(logging.DEBUG)
    if len(sys.argv) > 1 and not args.debug:
        args.run(args, onyo_root)
    elif len(sys.argv) > 2:
        args.run(args, onyo_root)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
