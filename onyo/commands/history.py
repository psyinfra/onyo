#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    run_cmd
)
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def prepare_arguments(source, tool, onyo_root):
    problem_str = ""
    if tool and run_cmd("which " + tool.split()[0]).rstrip("\n") == "":
        problem_str = problem_str + "\n" + tool.split()[0] + " is not available."
    # find directory/asset to show history of
    current_source = source
    # when no source is given, it uses the onyo root
    if not source:
        current_source = onyo_root
    # either from inside the folder, or from onyo root
    if not os.path.exists(current_source):
        current_source = os.path.join(onyo_root, source)
    # check if path exists
    if not os.path.exists(current_source):
        problem_str = problem_str + "\n" + source + " does not exist."
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return current_source


def history(args, onyo_root):
    # run onyo fsck for read only commands
    read_only_fsck(args, onyo_root, quiet=True)
    # check source
    source = prepare_arguments(args.source, args.tool, onyo_root)
    # run history command depending on mode
    if args.tool:
        os.system(args.tool + " \"" + source + "\"")
    elif not args.non_interactive and sys.stdout.isatty():
        os.system("tig --follow \"" + source + "\"")
    else:
        print(run_cmd("git --no-pager log --follow \"" + source + "\""))
