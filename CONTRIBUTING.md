# Contributing to Onyo

## Reporting issues

For bug reports and suggestions, please [open an issue](https://github.com/psyinfra/onyo/issues/new).

## Getting started with development

### Setup

> **Note**
> Onyo requires Python 3.13 or higher.

#### (1) Fork the Onyo repository

Navigate to <https://github.com/psyinfra/onyo/> and fork the repository.

#### (2) Clone the forked repository and enter into it

```bash
git clone git@github.com:<your_username>/onyo.git
cd onyo
```

#### (3) Create then activate a virtual environment

```bash
python3 -m venv ~/.venvs/onyo
source ~/.venvs/onyo/bin/activate
```

#### (4) Install non-Python dependencies

Debian/Ubuntu:
```bash
apt-get install git tig python3-pip
```

macOS ([Homebrew](https://brew.sh):
```bash
brew install git tig
```

#### (5) Install Onyo and test dependencies

```bash
pip3 install -e ".[tests, docs]"
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

Linting uses both ruff and Pyre.
```bash
ruff check
pyre check
```

### Benchmarks

Benchmarks use pytest-benchmark.
```bash
pytest -p no:randomly -p no:cov --benchmark-autosave --benchmark-time-unit=s --benchmark-max-time=5 --benchmark-min-rounds=5 --benchmark-sort=name --benchmark-group-by=func --benchmark-columns=min,max,mean,stddev,median,rounds -vv onyo/tests/benchmark.py
```
To compare to previous runs:
```
pytest-benchmark compare .benchmarks/[...] [...]
```

### Building documentation

```bash
make -C docs clean html
```

Navigate to <file:///<repo_dir>/docs/build/html/index.html>

## Code Conventions

Onyo follows a set of development and coding conventions throughout its code
base. For linting and type checking, Onyo uses ruff and Pyre. The following
sections describe conventions followed in this project, additionally to the
[PEP 8 Style Guide](https://peps.python.org/pep-0008/).

- Classes, functions and properties (including tests) have a docstring
  following the [Numpy standard](https://numpydoc.readthedocs.io/en/latest/format.html).
- Functions have type hinting for parameters and return types.
- Code style follows [PEP 8](https://peps.python.org/pep-0008/).

### lib Tests (`tests/lib/`)

- define the public Python API behavior
  - comprehensively test combinations of parameters
- use only the Python API (no usage of `subprocess.run(["onyo", ...])`)

### CLI Tests (`tests/cli/`)

- define the CLI behavior
  - comprehensively test combinations of arguments/flags
- use only CLI commands (e.g. call `subprocess.run(["onyo", ...])`) and are
  independent entirely of the Python API
