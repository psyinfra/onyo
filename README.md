# Onyo

![Build Status](https://github.com/psyinfra/onyo/actions/workflows/tests.yaml/badge.svg)
![Demo Status](https://github.com/psyinfra/onyo/actions/workflows/deploy_demo.yaml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/onyo/badge/?version=latest)](https://onyo.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/psyinfra/onyo/branch/main/graph/badge.svg?token=Z0VGYCHHAR)](https://codecov.io/gh/psyinfra/onyo)
[![License: ISC](https://img.shields.io/badge/License-ISC-blueviolet.svg)](https://opensource.org/licenses/ISC)

Onyo is a text-based inventory system built on top of git. It uses the filesystem as
the index and git to track history. This allows much of Onyo's functionality to
be just a thin wrapper around git commands.

## Use
See the documentation for [installation instructions](https://onyo.readthedocs.io/en/latest/installation.html)
and general information about Onyo.

## Report Issues
For general feedback, bug reports, and comments, please [open an issue](https://github.com/psyinfra/onyo/issues/new).

## Develop

### Installation

#### Non-Python Dependencies:
In addition to Python >= 3.9, Onyo depends on a few system utilities.

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

#### Clone the repo and install package and dependencies for tests, documentation:
```
git clone https://github.com/psyinfra/onyo.git
cd onyo
pip install -e ".[tests, docs]"
```

### Tests
Tests are run from the top-level of the repository.
```
pytest -vv
```

Generating code coverage reports requires some small gymnastics due to Onyo's
tests running in different working directories.
```
REPO_ROOT=$PWD pytest -vv --cov
```

Linting uses both flake8 and Pyre.
```
flake8
pyre check
```

### Documentation
Build the docs.
```
make -C docs clean html
```
