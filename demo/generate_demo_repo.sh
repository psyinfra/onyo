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
onyo --yes mkdir warehouse
onyo --yes mkdir recycling
onyo --yes mkdir repair

# import some existing hardware
# TSV files can be very useful when adding large amounts of assets
onyo --yes new --tsv "${SCRIPT_DIR}/inventory.tsv"

# add a set of newly bought assets
onyo --yes new --keys type=laptop make=apple model=macbook serial=9r32he RAM=8GB display=13.3 --directory warehouse/
onyo --yes new --keys type=laptop make=apple model=macbook serial=9r5qlk RAM=8GB display=13.3 --directory warehouse/
onyo --yes new --keys type=laptop make=lenovo model=thinkpad serial=owh8e2 RAM=8GB display=14.6 --directory warehouse/
onyo --yes new --keys type=laptop make=lenovo model=thinkpad serial=iu7h6d RAM=8GB display=14.6 --directory warehouse/
onyo --yes new --keys type=laptop make=microsoft model=surface serial=oq782j RAM=8GB display=12.4 touchscreen=yes --directory warehouse/

# NOTE: headphones normally do not have a serial number, and thus a faux serial
# would be generated (e.g. headphones_JBL_pro.faux). However, for the sake of a
# reproducible demo, explicit serials are specified.
onyo --yes new --keys type=headphones make=apple model=airpods serial=7h8f04 --directory warehouse/
onyo --yes new --keys type=headphones make=JBL model=pro serial=325gtt --directory warehouse/
onyo --yes new --keys type=headphones make=JBL model=pro serial=e98t2p --directory warehouse/
onyo --yes new --keys type=headphones make=JBL model=pro serial=ph9527 --directory warehouse/

# one of the headphones was added by accident; remove it.
onyo --yes rm warehouse/headphones_JBL_pro.ph9527

# a few new users join
onyo --yes mkdir "ethics/Max Mustermann" "ethics/Achilles Book"

# assign equipment to Max and Achilles
onyo --yes mv warehouse/laptop_apple_macbook.9r32he "ethics/Max Mustermann"
onyo --yes mv warehouse/headphones_apple_airpods.7h8f04 "ethics/Max Mustermann"

onyo --yes mv warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Achilles Book"
onyo --yes mv warehouse/headphones_JBL_pro.e98t2p "ethics/Achilles Book"

# Achilles' laptop broke; set it aside to repair and give him a new one
onyo --yes mv "ethics/Achilles Book/laptop_lenovo_thinkpad.owh8e2" repair
onyo --yes mv warehouse/laptop_microsoft_surface.oq782j "ethics/Achilles Book"

# specify number of USB type A ports on all laptops
onyo get --match type=laptop --machine-readable --keys path | tr "\n" "\0" | xargs -0 onyo --yes set --keys USB_A=2 --asset

# specify the number of USB ports (type A and C) on MacBooks
onyo get --match model=macbook --machine-readable --keys path | tr "\n" "\0" | xargs -0 onyo --yes set --keys USB_A=2 USB_C=1 --asset

# add three newly purchased laptops; shell brace-expansion can be very useful
onyo --yes new --keys type=laptop make=apple model=macbook serial={uef82b3,9il2b4,73b2cn} RAM=8GB display=13.3 USB_A=2 USB_C=1 \
    --directory warehouse/

# Bingo Bob was hired; and new hardware was purchased for him
onyo --yes mkdir "accounting/Bingo Bob"
onyo --yes new --keys type=monitor make=dell model=PH123 serial=86JZho display=22.0 --directory warehouse/
onyo --yes new --keys type=laptop make=apple model=macbook serial=oiw629 RAM=8GB display=13.3 USB_A=2 --directory warehouse/
onyo --yes new --keys type=headphones make=apple model=airpods serial=uzl8e1 --directory warehouse/
onyo --yes mv warehouse/monitor_dell_PH123.86JZho warehouse/laptop_apple_macbook.oiw629 warehouse/headphones_apple_airpods.uzl8e1 "accounting/Bingo Bob"

# the broken laptop has been repaired (bad RAM, which has also been increased)
onyo --yes set --keys RAM=32GB --asset repair/laptop_lenovo_thinkpad.owh8e2
onyo --yes mv repair/laptop_lenovo_thinkpad.owh8e2 warehouse

# Max's laptop is old; retire it and replace with a new one
onyo --yes mv ethics/Max\ Mustermann/laptop_apple_macbook.9r32he recycling
onyo --yes mv warehouse/laptop_apple_macbook.uef82b3 ethics/Max\ Mustermann/

# a new group is created ("management"); transfer people to their new group
onyo --yes mkdir "management"
onyo --yes mv "ethics/Max Mustermann" management
onyo --yes mkdir "management/Alice Wonder"
onyo --yes new --keys type=laptop make=apple model=macbook serial=83hd0 RAM=8GB display=13.3 USB_A=2 --directory "management/Alice Wonder/"

# Theo joins; assign them a laptop from the warehouse
onyo --yes mkdir "ethics/Theo Turtle"
onyo --yes mv warehouse/laptop_lenovo_thinkpad.owh8e2 "ethics/Theo Turtle"

# Max retired; return all of his hardware and delete his directory
onyo --yes mv management/Max\ Mustermann/* warehouse
onyo --yes rm "management/Max Mustermann"

# TODO: add "onyo fsck"
# TODO: compare
# git log
# assert
