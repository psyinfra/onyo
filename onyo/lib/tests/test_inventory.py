import pytest
from pathlib import Path

from onyo.lib.consts import TEMPLATE_DIR
from onyo.lib.inventory import Inventory
from onyo.lib.items import Item


@pytest.mark.ui({'yes': True})
def test_get_items_types(inventory: Inventory, capsys) -> None:

    assets = [a for a in inventory.get_items(types=['assets'])]
    assert len(assets) == 1
    asset = assets[0]
    assert isinstance(asset, Item)
    assert asset["onyo.path.relative"] == Path("somewhere") / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    assert asset["onyo.is.asset"] is True
    assert asset["onyo.is.directory"] is False
    assert asset["onyo.is.template"] is False

    fixture_dirs = [Path("."),
                    Path("empty"),
                    Path("somewhere"),
                    Path("somewhere") / "nested",
                    Path("different"),
                    Path("different") / "place"]
    dirs = [d for d in inventory.get_items(types=['directories'])]
    assert len(dirs) == len(fixture_dirs)
    assert all(d["onyo.path.relative"] in fixture_dirs for d in dirs)
    assert all(p in [d["onyo.path.relative"] for d in dirs] for p in fixture_dirs)
    for d in dirs:
        assert isinstance(d, Item)
        assert d["onyo.is.directory"] is True
        assert d["onyo.is.asset"] is False
        assert d["onyo.is.template"] is False

    fixture_templates = [TEMPLATE_DIR / "empty",
                         TEMPLATE_DIR / "laptop.example"]

    templates = [t for t in inventory.get_items(include=[inventory.repo.template_dir])]
    assert len(templates) == len(fixture_templates)
    assert all(t["onyo.path.relative"] in fixture_templates for t in templates)
    assert all(p in [t["onyo.path.relative"] for t in templates] for p in fixture_templates)
    for t in templates:
        assert isinstance(t, Item)
        assert t["onyo.is.asset"] is (t["onyo.path.name"] != "empty")
        assert t["onyo.is.directory"] is False
        assert t["onyo.is.template"] is True
