#!/bin/bash
# This file is licensed under the ISC license.
# See the AUTHORS and LICENSE files for more information.

# This script generates a demo Onyo repository.
# It is not meant to be comprehensive, but should cover a wide range of Onyo's
# functionality.

############
## Variables
############
readonly VERSION=0.0.1
readonly SCRIPT_NAME=${0##*/}
DEMO_DIR=''

# set reproducible commit hashes
export GIT_AUTHOR_NAME='Yoko Onyo'
export GIT_AUTHOR_EMAIL='yoko@onyo.org'
export GIT_AUTHOR_DATE='2023-01-01T00:00:00'
export GIT_COMMITTER_NAME='Yoko Onyo'
export GIT_COMMITTER_EMAIL='yoko@onyo.org'
export GIT_COMMITTER_DATE='2023-01-01T00:00:00'


############
## FUNCTIONS
############
Help() {
    cat << EOF
$SCRIPT_NAME v${VERSION} - generate a demo Onyo repository

Syntax:
$SCRIPT_NAME [-h] [-V] DIRECTORY

OPTIONS:
  -h, --help                     = Print this help and exit
  -V, --version                  = Print the version number and exit

EOF
}

# print message to stderr and exit 1
Fatal() {
    printf '%s\n' "$*" >&2
    exit 1
}


#############################
# PARSE OPTIONS AND ARGUMENTS
#############################
# help out if the number of arguments is wrong
[ -n "$1" ] || { Help; exit 1; }
[ -z "$2" ] || Fatal 'Only one argument is allowed.'

# options and arguments
case "$1" in
    '-h'|'--help')
        Help
        exit 0
        ;;
    '-V'|'--version')
        printf '%s v%s\n' "$SCRIPT_NAME" "$VERSION"
        exit 0
        ;;
    -*)
        Fatal "'$1' is not a valid '$SCRIPT_NAME' option."
        ;;
    *)
        DEMO_DIR=$1
        [ -e "$DEMO_DIR" ] || mkdir -v "$DEMO_DIR"
        [ -d "$DEMO_DIR" ] || Fatal "'$DEMO_DIR' must be a directory."
        [ -e "${DEMO_DIR}/.onyo" ] && Fatal "'$DEMO_DIR' cannot be an onyo repo"
        [ -e "${DEMO_DIR}/.git" ] && Fatal "'$DEMO_DIR' cannot be a git repo"
        ;;
esac


######
# MAIN
######
ONYO_REPO_DIR=$(pwd)
cd "$DEMO_DIR"

# initialize a repository
onyo init

# setup basic folder structure
onyo mkdir warehouse
onyo mkdir recycling
onyo mkdir repair

# add existing inventory from a table
onyo new -y --tsv "$ONYO_REPO_DIR/demo/inventory.tsv"

# add a set of newly bought assets
# TODO Update all serials
onyo new -y RAM=8GB display=13.3 warehouse/laptop_apple_macbook.9r32he
onyo new -y RAM=8GB display=13.3 warehouse/laptop_apple_macbook.9r5qlk
onyo new -y RAM=8GB display=14.6 warehouse/laptop_lenovo_thinkpad.owh8e2
onyo new -y RAM=8GB display=14.6 warehouse/laptop_lenovo_thinkpad.iu7h6d
onyo new -y RAM=8GB display=12.4 touchscreen=yes warehouse/laptop_microsoft_surface.oq782j
# NOTE: headphones normally do not have a serial, and a faux serial would be
# generated (e.g. headphones_JBL_pro.faux). However, for the sake of a
# reproducible demo, serials are specified.
onyo new -y warehouse/headphones_apple_airpods.7h8f04
onyo new -y warehouse/headphones_JBL_pro.325gtt
onyo new -y warehouse/headphones_JBL_pro.e98t2p
onyo new -y warehouse/headphones_JBL_pro.ph9527

# one pair of headphones was added by accident; remove it
onyo rm -y warehouse/headphones_JBL_pro.ph9527

# a few new users join
onyo mkdir "ethics/Max Mustermann" "ethics/Achilles Book"
onyo mkdir "accounting/Bingo Bob"

# assign equipment to new users
onyo mv -y warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Achilles Book"
onyo mv -y warehouse/headphones_JBL_pro.e98t2p "ethics/Achilles Book"

onyo mv -y warehouse/laptop_apple_macbook.9r32he "ethics/Max Mustermann"
onyo mv -y warehouse/headphones_apple_airpods.7h8f04 "ethics/Max Mustermann"

# give a broken device to repair and replace with another laptop
onyo mv -y "ethics/Achilles Book/laptop_lenovo_thinkpad.owh8e2" repair
onyo mv -y warehouse/laptop_microsoft_surface.oq782j "ethics/Achilles Book"

# give macbooks information about number of USB C ports
onyo set -y USB_A=2 USB_C=1 */laptop_apple_macbook.* */*/laptop_apple_macbook.*

# give all laptops information about USB A ports
onyo set -y USB_A=2 */laptop_*.* */*/laptop_*.*

# buy some new laptops
onyo new -y RAM=8GB display=13.3 USB_A=2 USB_C=1 \
    warehouse/laptop_apple_macbook.{uef82b3,9il2b4,73b2cn}

# buy new equipment give it to a user
onyo new -y display=22.0 warehouse/monitor_dell_PH123.86JZho
onyo new -y RAM=8GB display=13.3 USB_A=2 warehouse/laptop_apple_macbook.oiw629
onyo new -y warehouse/headphones_apple_airpods.uzl8e1
onyo mv -y warehouse/monitor_dell_PH123.86JZho warehouse/laptop_apple_macbook.oiw629 warehouse/headphones_apple_airpods.uzl8e1 "accounting/Bingo Bob"

# update and return a repaired device back into the warehouse
onyo set -y RAM=32GB repair/laptop_lenovo_thinkpad.owh8e2
onyo mv -y repair/laptop_lenovo_thinkpad.owh8e2 warehouse

# update a device to have more RAM
onyo set -y RAM=16GB "ethics/Achilles Book/laptop_microsoft_surface.oq782j"

# a device of a user is too old; replace it with a new one
onyo mv -y ethics/Max\ Mustermann/laptop_apple_macbook.9r32he recycling
onyo mv -y warehouse/laptop_apple_macbook.uef82b3 ethics/Max\ Mustermann/

# a new group gets created, users move there and take their equipment with them
onyo mkdir "management"
onyo mv -y "ethics/Max Mustermann" management
onyo mkdir "management/Alice Wonder"
onyo new -y RAM=8GB display=13.3 USB_A=2 "management/Alice Wonder/laptop_apple_macbook.83hd0"

# a new user joins; give repaired laptop from warehouse
onyo mkdir "ethics/Theo Turtle"
onyo mv -y warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Theo Turtle"

# a user retires; return the hardware and delete the user folder
onyo mv -y management/Max\ Mustermann/* warehouse
onyo rm -y "management/Max Mustermann"

# A test; Not intended to merge
onyo mkdir "Horatio Hornblower"

# test the validity of the inventory's state
onyo fsck

# TODO: compare
# git log
# assert
