# Contributing to Onyo

## Reporting issues

For bug reports and suggestions, please [open an issue](https://github.com/psyinfra/onyo/issues/new).

## Getting started with development

### Setup

> **Note**
> Onyo requires Python 3.11 or higher.

#### (1) Fork the Onyo repository

Navigate to <https://github.com/psyinfra/onyo/> and fork the repository.

#### (2) Clone the forked repository and enter into it

```bash
git clone git@github.com:<your_username>/onyo.git
cd onyo
```

#### (3) Create then activate a virtual environment

```bash
python -m venv ~/.venvs/onyo
source ~/.venvs/onyo/bin/activate
```

#### (4) Install non-Python dependencies

Debian/Ubuntu:
```bash
apt-get install git tig tree
```

macOS ([Homebrew](https://brew.sh):
```bash
brew install git tig tree
```

#### (5) Install Onyo and test dependencies

```bash
pip install -e ".[tests, docs]"
```

### Running tests

Tests are run from the top-level of the repository.
```bash
pytest -vv
```

Generating code coverage reports requires some small gymnastics due to Onyo's
tests running in individual working directories.
```bash
REPO_ROOT=$PWD pytest -vv --cov
```

### Linting and type checking

Linting uses both flake8 and Pyre.
```bash
flake8
pyre check
```

### Building documentation

```bash
make -C docs clean html
```

Navigate to <file:///<repo_dir>/docs/build/html/index.html>

## Code Conventions

Onyo follows a set of development and coding conventions throughout its code
base. For linting and type checking, Onyo uses flake8 and Pyre. The following
sections describe conventions followed in this project, additionally to the
[PEP 8 Style Guide](https://peps.python.org/pep-0008/).

### The Complete Code Base:
- All classes, functions and properties (including tests) have a docstring
  following the [Numpy standard](https://numpydoc.readthedocs.io/en/latest/format.html).
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
