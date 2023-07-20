#!/bin/bash
# This file is licensed under the ISC license.
# See the AUTHORS and LICENSE files for more information.

# This script generates a demo Onyo repository.
# It is not meant to be comprehensive, but should cover a wide range of Onyo's
# functionality.
set -e

############
## Variables
############
readonly VERSION=1.0.0
readonly SCRIPT_NAME=${0##*/}
readonly SCRIPT_DIR=$(dirname $(realpath "$0"))
DEMO_DIR=''

# set reproducible commit hashes
export GIT_AUTHOR_NAME='Yoko Onyo'
export GIT_AUTHOR_EMAIL='yoko@onyo.org'
export GIT_AUTHOR_DATE='2023-01-01 00:00:00 +0100'
export GIT_COMMITTER_NAME='Yoko Onyo'
export GIT_COMMITTER_EMAIL='yoko@onyo.org'
export GIT_COMMITTER_DATE='2023-01-01 00:00:00 +0100'


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
cd "$DEMO_DIR"

# initialize a repository
onyo init

# setup basic directory structure
onyo mkdir --yes warehouse
onyo mkdir --yes recycling
onyo mkdir --yes repair

# import some existing hardware
# TSV files can be very useful when adding large amounts of assets
onyo new -y --tsv "${SCRIPT_DIR}/inventory.tsv"

# add a set of newly bought assets
onyo new -y --keys RAM=8GB display=13.3 --path warehouse/laptop_apple_macbook.9r32he
onyo new -y --keys RAM=8GB display=13.3 --path warehouse/laptop_apple_macbook.9r5qlk
onyo new -y --keys RAM=8GB display=14.6 --path warehouse/laptop_lenovo_thinkpad.owh8e2
onyo new -y --keys RAM=8GB display=14.6 --path warehouse/laptop_lenovo_thinkpad.iu7h6d
onyo new -y --keys RAM=8GB display=12.4 touchscreen=yes --path warehouse/laptop_microsoft_surface.oq782j
# NOTE: headphones normally do not have a serial number, and thus a faux serial
# would be generated (e.g. headphones_JBL_pro.faux). However, for the sake of a
# reproducible demo, explicit serials are specified.
onyo new -y --path warehouse/headphones_apple_airpods.7h8f04
onyo new -y --path warehouse/headphones_JBL_pro.325gtt
onyo new -y --path warehouse/headphones_JBL_pro.e98t2p
onyo new -y --path warehouse/headphones_JBL_pro.ph9527

# one of the headphones was added by accident; remove it.
onyo rm -y warehouse/headphones_JBL_pro.ph9527

# a few new users join
onyo mkdir --yes "ethics/Max Mustermann" "ethics/Achilles Book"

# assign equipment to Max and Achilles
onyo mv -y warehouse/laptop_apple_macbook.9r32he "ethics/Max Mustermann"
onyo mv -y warehouse/headphones_apple_airpods.7h8f04 "ethics/Max Mustermann"

onyo mv -y warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Achilles Book"
onyo mv -y warehouse/headphones_JBL_pro.e98t2p "ethics/Achilles Book"

# Achilles' laptop broke; set it aside to repair and give him a new one
onyo mv -y "ethics/Achilles Book/laptop_lenovo_thinkpad.owh8e2" repair
onyo mv -y warehouse/laptop_microsoft_surface.oq782j "ethics/Achilles Book"

# specify number of USB type A ports on all laptops
onyo set -y --keys USB_A=2 --filter type=laptop

# specify the number of USB ports (type A and C) on MacBooks
onyo set -y --keys USB_A=2 USB_C=1 --filter model=macbook

# add three newly purchased laptops; shell brace-expansion can be very useful
onyo new -y --keys RAM=8GB display=13.3 USB_A=2 USB_C=1 \
    --path warehouse/laptop_apple_macbook.{uef82b3,9il2b4,73b2cn}

# Bingo Bob was hired; and new hardware was purchased for him
onyo mkdir --yes "accounting/Bingo Bob"
onyo new -y --keys display=22.0 --path warehouse/monitor_dell_PH123.86JZho
onyo new -y --keys RAM=8GB display=13.3 USB_A=2 --path warehouse/laptop_apple_macbook.oiw629
onyo new -y --path warehouse/headphones_apple_airpods.uzl8e1
onyo mv -y warehouse/monitor_dell_PH123.86JZho warehouse/laptop_apple_macbook.oiw629 warehouse/headphones_apple_airpods.uzl8e1 "accounting/Bingo Bob"

# the broken laptop has been repaired (bad RAM, which has also been increased)
onyo set -y --keys RAM=32GB --path repair/laptop_lenovo_thinkpad.owh8e2
onyo mv -y repair/laptop_lenovo_thinkpad.owh8e2 warehouse

# Max's laptop is old; retire it and replace with a new one
onyo mv -y ethics/Max\ Mustermann/laptop_apple_macbook.9r32he recycling
onyo mv -y warehouse/laptop_apple_macbook.uef82b3 ethics/Max\ Mustermann/

# a new group is created ("management"); transfer people to their new group
onyo mkdir --yes "management"
onyo mv -y "ethics/Max Mustermann" management
onyo mkdir --yes "management/Alice Wonder"
onyo new -y --keys RAM=8GB display=13.3 USB_A=2 --path "management/Alice Wonder/laptop_apple_macbook.83hd0"

# Theo joins; assign them a laptop from the warehouse
onyo mkdir --yes "ethics/Theo Turtle"
onyo mv -y warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Theo Turtle"

# Max retired; return all of his hardware and delete his directory
onyo mv -y management/Max\ Mustermann/* warehouse
onyo rm -y "management/Max Mustermann"

# test the validity of the inventory's state
onyo fsck

# TODO: compare
# git log
# assert
