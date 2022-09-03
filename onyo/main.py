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
