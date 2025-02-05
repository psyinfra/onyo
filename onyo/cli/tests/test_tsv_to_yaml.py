from __future__ import annotations

import subprocess
from importlib import resources
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_onyo_tsv_to_yaml_errors(tmp_path: Path) -> None:
    # argument is required
    ret = subprocess.run(["onyo", "tsv-to-yaml"],
                          capture_output=True, text=True)
    assert ret.returncode == 2

    # tsv must exist
    ret = subprocess.run(["onyo", "tsv-to-yaml", tmp_path / "does-not-exist.tsv"],
                          capture_output=True, text=True)
    assert ret.returncode == 1


def test_cli_onyo_tsv_to_yaml() -> None:
    input_tsv = resources.files('onyo.tests.tables').joinpath('table.tsv')
    reference = resources.files('onyo.tests.tables').joinpath('table.yaml')

    #
    # compare the output against the reference; it should be identical
    #
    with resources.as_file(input_tsv) as tsv_path:
        ret = subprocess.run(["onyo", "tsv-to-yaml", tsv_path],
                              capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout == reference.read_text()
