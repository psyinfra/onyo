#!/usr/bin/env python3

import logging
import os
import sys
import configparser

from onyo.utils import (
    run_cmd
)
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def prepare_arguments(source, onyo_root):
    problem_str = ""
    # find log/history tools:
    config = configparser.ConfigParser()
    config.read(os.path.join(onyo_root, ".onyo/config"))
    interactive_tool = ""
    non_interactive_tool = ""
    try:
        interactive_tool = config['history']['interactive']
    except KeyError:
        pass
    try:
        non_interactive_tool = config['history']['non-interactive']
    except KeyError:
        pass
    if not interactive_tool:
        problem_str = problem_str + "\n" + "No interactive logging tool is set. Set with e.g:\n\tonyo config history.interactive \"tig --follow\""
    elif run_cmd("which " + interactive_tool.split()[0].rstrip("\n")) == "":
        problem_str = problem_str + "\nLogging tool " + interactive_tool.split()[0] + " is not available. Set with e.g:\n\tonyo config history.interactive \"tig --follow\""
    if not non_interactive_tool:
        problem_str = problem_str + "\n" + "No non-interactive logging tool is set. Set with e.g:\n\tonyo config history.non-interactive \"git --no-pager log --follow\""
    elif run_cmd("which " + non_interactive_tool.split()[0].rstrip("\n")) == "":
        problem_str = problem_str + "\nLogging tool " + non_interactive_tool.split()[0] + " is not available. Set with e.g:\n\tonyo config history.non-interactive \"git --no-pager log --follow\""
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
    return [current_source, interactive_tool, non_interactive_tool]


def history(args, onyo_root):
    # run onyo fsck for read only commands
    read_only_fsck(args, onyo_root, quiet=True)
    # check source, set variables
    [source, interactive_tool, non_interactive_tool] = prepare_arguments(args.source, onyo_root)
    # run history command depending on mode
    if not args.non_interactive and sys.stdout.isatty():
        os.system(interactive_tool + " \"" + source + "\"")
    else:
        os.system(non_interactive_tool + " \"" + source + "\"")
