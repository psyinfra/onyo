# Onyo

![Build Status](https://github.com/psyinfra/onyo/actions/workflows/tests.yaml/badge.svg)
[![Demo Status](https://github.com/psyinfra/onyo/actions/workflows/deploy_demo.yaml/badge.svg)](https://github.com/psyinfra/onyo-demo/)
[![Documentation Status](https://readthedocs.org/projects/onyo/badge/?version=latest)](https://onyo.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/psyinfra/onyo/branch/main/graph/badge.svg?token=Z0VGYCHHAR)](https://codecov.io/gh/psyinfra/onyo)
[![License: ISC](https://img.shields.io/badge/License-ISC-blueviolet.svg)](https://opensource.org/licenses/ISC)

Onyo is a text-based inventory system built on top of git. It uses the filesystem as
the index and git to track history. This allows much of Onyo's functionality to
be just a thin wrapper around git commands.

## Use
See the documentation for [installation instructions](https://onyo.readthedocs.io/en/latest/installation.html)
and general information about Onyo.

### Installation

#### Non-Python Dependencies:
Onyo requires Python >= 3.11 and a few system utilities.

Debian/Ubuntu:
```
apt-get install git tig tree
```

macOS:
```
brew install git tig tree
```

#### Setup and activate virtual environment:
```
python -m venv ~/.venvs/onyo
source ~/.venvs/onyo/bin/activate
```

## Demo
An [example Onyo repository](https://github.com/psyinfra/onyo-demo/) is
available. It's easier to get a feel for how Onyo works with a populated
repository with actual history, rather than starting from scratch. Just install
Onyo, clone the demo repo, and start poking around!

## Report Issues
For general feedback, bug reports, and comments, please [open an issue](https://github.com/psyinfra/onyo/issues/new).
