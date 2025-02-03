from importlib import resources
from pathlib import Path

import pytest

from ..commands import onyo_tsv_to_yaml


def test_onyo_tsv_to_yaml_errors(tmp_path: Path) -> None:
    # tsv must exist
    pytest.raises(FileNotFoundError,
                  onyo_tsv_to_yaml,
                  tsv=Path(tmp_path / "does-not-exist.tsv"))

    # empty file
    input_tsv = resources.files('onyo.tests.tables').joinpath('error_empty.tsv')
    with resources.as_file(input_tsv) as tsv_path:
        pytest.raises(ValueError, onyo_tsv_to_yaml, tsv=tsv_path)

    # headers but no content
    input_tsv = resources.files('onyo.tests.tables').joinpath('error_only_header.tsv')
    with resources.as_file(input_tsv) as tsv_path:
        pytest.raises(ValueError, onyo_tsv_to_yaml, tsv=tsv_path)


def test_onyo_tsv_to_yaml() -> None:
    # valid table runs without error
    input_tsv = resources.files('onyo.tests.tables').joinpath('table.tsv')
    with resources.as_file(input_tsv) as tsv_path:
        onyo_tsv_to_yaml(tsv=tsv_path)
