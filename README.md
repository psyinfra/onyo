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
In addition to Python >= 3.11, Onyo depends on a few system utilities.

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

## Develop

### Clone the repo and install package and dependencies for tests, documentation:
```
git clone https://github.com/psyinfra/onyo.git
cd onyo
pip install -e ".[tests, docs]"
```

### Code Conventions

Onyo follows a set of development and coding conventions throughout its code
base. For linting and type checking, Onyo uses flake8 and Pyre. The following
sections describe conventions followed in this project, additionally to the
[PEP 8 Style Guide](https://peps.python.org/pep-0008/).

#### The Complete Code Base:
- All classes, functions and properties (including tests) have a doc-string that
  describes their functionality.
- All functions have type hinting (including explicit return type for `None`).
- The code conforms to [PEP 8](https://peps.python.org/pep-0008/).

#### lib Tests (`tests/lib/`):
- define the expected behavior for all use-cases of the different consumers
  (i.e. CLI, demos)
- use the API functions (no usage of `subprocess.run(["onyo", ...])`)
- all public functions and properties of all classes are tested with all
  possible combinations of input:
  - single valid inputs, including different data-types (if allowed)
  - multiple valid inputs (if allowed)
  - without input (if allowed)
  - one test for each possible error
  - one test for each possible conflict with other inputs

#### CLI Tests (`tests/commands/`):
- define the expected behavior which the user can expect from Onyo
- are created completely independent and without any consideration of the code
  base
- cover a large variety of use-cases to verify that Onyo works as intended,
  even if large parts of the code would be modified
- call `subprocess.run(["onyo", ...])` to simulate how Onyo behaves
- verify the correct behavior for all possible combinations of arguments/flags:
  - single valid argument
  - multiple valid arguments (if allowed)
  - without the flag
  - one test per different error
  - one test per possible conflict with other arguments

### Run Tests
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
