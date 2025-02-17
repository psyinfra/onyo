from __future__ import annotations

import random
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from onyo.lib.commands import (
    onyo_cat,
    onyo_get,
    onyo_new,
    onyo_set,
)
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.lib.utils import DotNotationWrapper

if TYPE_CHECKING:
    from typing import Generator


@pytest.mark.ui({'yes': True, 'quiet': True})
@pytest.mark.parametrize('num', [100, 1000])
class TestOnyoBenchmark:
    r"""Run a suite of benchmarks for Onyo."""

    @pytest.fixture(scope='function')
    def benchmark_inventory(self,
                            num: int,
                            request,
                            tmp_path: Path,
                            fake,
                            monkeypatch) -> Generator[Inventory, None, None]:
        r"""Yield an Inventory, populated with ``num`` of fake assets.

        The generated repositories are cached. A clone is produced for
        subsequent requests of Inventories with the same population count.
        """

        repo_path = tmp_path

        if not getattr(request.cls, '_class_repo_path', False):
            request.cls._class_repo_path = {}
        if not getattr(request.cls, '_class_old_hexsha', False):
            request.cls._class_old_hexsha = {}

        class_repo_path = request.cls._class_repo_path.get(num, False)
        if class_repo_path:
            # clone existing repo
            subprocess.run(['git', 'clone', str(class_repo_path), str(repo_path)])

            repo = OnyoRepo(repo_path)
            inventory = Inventory(repo=repo)
        else:
            # initialize new repo
            repo = OnyoRepo(repo_path, init=True)
            repo.set_config("onyo.assets.name-format", "{type}_{make}_{model.name}.{serial}")
            repo.git.commit(repo.git.root / repo.ONYO_CONFIG, message="Asset name config w/ dot")
            inventory = Inventory(repo=repo)

            # populate the repo
            assets = [DotNotationWrapper(a) for a in fake.onyo_asset_dicts(num=num)]
            directories = fake.onyo_directories(num=num)
            assets = [a | {'directory': d} for a, d in zip(assets, directories)]
            onyo_new(inventory, keys=assets)  # pyre-ignore[6]

            # store location of repo dir
            request.cls._class_repo_path[num] = repo_path
            # store pre-benchmark sha
            request.cls._class_old_hexsha[num] = inventory.repo.git.get_hexsha()

        # cd into the repo dir
        monkeypatch.chdir(repo_path)

        # reset to a known state (no leftovers from other benchmark runs)
        subprocess.run(['git', 'reset', '--hard', request.cls._class_old_hexsha[num]])

        # yield
        yield inventory


    def test_cli_onyo_new_fifty(self,
                                num: int,
                                benchmark_inventory: Inventory,
                                benchmark,
                                fake) -> None:
        r"""Create 50 assets in the repo."""

        inventory = benchmark_inventory
        # fifty additional assets
        fifty_assets = [DotNotationWrapper(a) for a in fake.onyo_asset_dicts(num=50)]
        fifty_assets_as_keys = [f'{k}={v}' for a in fifty_assets for k, v in a.items()]

        def setup():
            """
            Benchmark in a consistent-state repo.

            The benchmarked function is run multiple times, but without re-running
            the entire test function. This can create conflicts, etc.
            """

            inventory.repo.git._git(["reset", "--hard", self._class_old_hexsha[num]])
            # gc the repo
            inventory.repo.git._git(["gc", "--aggressive", "--quiet", "--prune=now"])

        benchmark.pedantic(subprocess.run,
                           args=[['onyo', '--yes', 'new', '--keys', *fifty_assets_as_keys]],
                           kwargs={'capture_output': True, 'check': True},
                           rounds=5,  # does not honor CLI flag values
                           setup=setup)

        # sanity checks
        assert len(onyo_get(inventory)) == (num + 50)


    def test_cli_onyo_get_all(self,
                              num: int,
                              benchmark_inventory: Inventory,
                              benchmark) -> None:
        r"""Get all assets in the repo."""

        inventory = benchmark_inventory

        # Per default, this will return all keys in the asset name + path and
        # sort by path.
        @benchmark
        def bench():
            subprocess.run(["onyo", "get"], capture_output=True, check=True)

        # sanity checks
        assert len(onyo_get(inventory)) == num


    def test_cli_onyo_get_fifty(self,
                                num: int,
                                benchmark_inventory: Inventory,
                                benchmark) -> None:
        r"""Get 50 assets from the repo."""

        from onyo.lib.filters import Filter

        inventory = benchmark_inventory
        # get 50 random assets
        assets = [a["onyo.path.absolute"]
                  for a in random.sample(onyo_get(inventory, keys=["onyo.path.absolute"]), k=50)]
        # set 50
        onyo_set(inventory, assets=assets, keys={'fifty': 'fifty'})

        # Per default, this will return all keys in the asset name + path and
        # sort by path.
        @benchmark
        def bench():
            subprocess.run(["onyo", "get", '--match', 'fifty=fifty'], capture_output=True, check=True)

        # sanity checks
        assert len(onyo_get(inventory)) == num
        filters = [Filter('fifty=fifty').match]
        assert len(onyo_get(inventory, match=filters)) == 50  # pyre-ignore[6]


    def test_cli_onyo_set_fifty(self,
                                num: int,
                                benchmark_inventory: Inventory,
                                benchmark) -> None:
        r"""Set 50 assets in the repo."""

        from onyo.lib.filters import Filter

        inventory = benchmark_inventory
        # get 50 assets
        assets = [str(a["onyo.path.absolute"])
                  for a in random.sample(onyo_get(inventory, keys=["onyo.path.absolute"]), k=50)]

        def setup():
            """
            Benchmark in a consistent-state repo.

            The benchmarked function is run multiple times, but without re-running
            the entire test function. This can create conflicts, etc.
            """

            inventory.repo.git._git(["reset", "--hard", self._class_old_hexsha[num]])
            # gc the repo
            inventory.repo.git._git(["gc", "--aggressive", "--quiet", "--prune=now"])

        benchmark.pedantic(subprocess.run,
                           args=[['onyo', '--yes', 'set', '--keys', 'fifty=fifty', '--asset', *assets]],
                           kwargs={'capture_output': True, 'check': True},
                           rounds=5,  # does not honor CLI flag values
                           setup=setup)

        # sanity checks
        assert len(onyo_get(inventory)) == num
        filters = [Filter('fifty=fifty').match]
        assert len(onyo_get(inventory, match=filters)) == 50  # pyre-ignore[6]


    def test_api_onyo_cat_one(self,
                              num: int,
                              benchmark_inventory: Inventory,
                              benchmark) -> None:
        r"""Cat 1 asset in the repo."""

        inventory = benchmark_inventory
        # get 1 asset
        assets = [a["onyo.path.absolute"]
                  for a in random.sample(onyo_get(inventory, keys=["onyo.path.absolute"]), k=1)]

        benchmark(onyo_cat, inventory, assets=assets)

        # sanity checks
        assert len(onyo_get(inventory)) == num


    def test_cli_onyo_cat_one(self,
                              num: int,
                              benchmark_inventory: Inventory,
                              benchmark) -> None:
        r"""Cat 1 asset from the CLI."""

        inventory = benchmark_inventory
        # get 1 asset
        asset = random.sample(onyo_get(inventory, keys=["onyo.path.absolute"]), k=1)[0]['onyo.path.absolute']

        @benchmark
        def bench():
            subprocess.run(["onyo", "cat", str(asset)], capture_output=True, check=True)

        # sanity checks
        assert len(onyo_get(inventory)) == num
