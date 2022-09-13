# Onyo

## --- UNDER DEVELOPMENT ---

*This repository is undergoing continuous development. It is not yet complete.*

Onyo is a text-based inventory system backed by git. It uses the filesystem as
the index and git to track history. This allows much of Onyo's functionality to
be just a thin wrapper around git commands (see the documentation for more
information).

## Installation

### Setup and activate virtual environment

With your virtual environment manager of choice, create a virtual environment
and ensure you have a recent version of Python installed. Then activate the
environment. E.g. with `venv`:

```
python -m venv ~/.venvs/onyo
source ~/.venvs/onyo/bin/activate
```

### Clone the repo and install the package

Run the following from your command line:
```
git clone https://github.com/psyinfra/onyo.git
cd onyo
pip install -e .
```
