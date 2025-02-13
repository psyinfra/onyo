from __future__ import annotations

from typing import TYPE_CHECKING

from faker.providers import python

if TYPE_CHECKING:
    from typing import Generator


class OnyoProvider(python.Provider):
    r"""Faker Provider for Onyo.

    Onyo-related provider functions are all prefixed with ``onyo_``.
    """

    def onyo_asset_dicts(self,
                         num: int = 1,
                         override: dict | None = None) -> Generator[dict, None, None]:
        r"""Yield asset dictionaries suitable for populating realistic assets."""

        if override is None:
            override = {}

        for _ in range(num):
            yield {
                'type': next(self.onyo_types()),
                'make': next(self.onyo_manufacturers()),
                'model': { 'name': self.numerify(text='Wizbang %##!') },
                'serial': self.pystr(min_chars=15),
                'keyboard': next(self.onyo_keyboards()),
                'display': {
                    'size': self.numerify(text='%#'),
                    'resolution': self.numerify(text='%##! x %##!'),
                    'hz': self.numerify(text='%#!'),
                },
                'RAM': self.numerify(text='%#!!G'),
                'CPU': {
                    'vendor': next(self.onyo_cpu_vendors()),
                    'cores': self.numerify(text='%#!'),
                    'arch': next(self.onyo_cpu_archs()),
                    'model': self.numerify(text='Speedy % %%##Z'),
                },
                'disk': { 'size': self.numerify(text='%#!T') },
            } | override


    def onyo_cpu_archs(self,
                       num: int = 1) -> Generator[str, None, None]:
        r"""Yield CPU architectures."""

        cpu_archs = (
            'aarch64',
            'amd64',
            'ppc64',
            'x86',
        )
        yield self.random_element(elements=cpu_archs)


    def onyo_cpu_vendors(self,
                         num: int = 1) -> Generator[str, None, None]:
        r"""Yield CPU vendors."""

        cpu_vendors = (
            'amd',
            'apple',
            'intel',
            'ibm',
        )
        yield self.random_element(elements=cpu_vendors)


    def onyo_directories(self,
                         num: int = 1) -> Generator[str, None, None]:
        r"""Yield directory names.

        Useful for ``onyo.path.directory``.
        """

        locations = (
            'repair',
            'shelf',
            'warehouse',
            'group',
            'group/Accounting',
            'group/Creative',
            'group/HR',
            'group/IT',
            'group/Operations',
            'group/Purchasing',
            'group/Sales',
        )
        for _ in range(num):
            yield self.random_element(elements=locations)


    def onyo_keyboards(self,
                       num: int = 1) -> Generator[str, None, None]:
        r"""Yield keyboard layout names."""

        keyboards = (
            'azerty',
            'qwerty',
            'qwertz',
            'qzerty',
            'qüerty',
            'ąžerty',
        )
        yield self.random_element(elements=keyboards)


    def onyo_manufacturers(self,
                           num: int = 1) -> Generator[str, None, None]:
        r"""Yield manufacturers."""

        manufacturers = (
            'apple',
            'asus',
            'cisco',
            'dell',
            'eizo',
            'framework',
            'hp',
            'lenovo',
            'samsung',
            'sun',
            'toshiba',
            'zebra',
        )
        yield self.random_element(elements=manufacturers)


    def onyo_types(self,
                   num: int = 1) -> Generator[str, None, None]:
        r"""Yield asset types."""

        types = (
            'desktop',
            'display',
            'laptop',
            'pdu',
            'server',
            'switch',
            'ups',
        )
        yield self.random_element(elements=types)
