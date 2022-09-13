#!/usr/bin/env python3
''' setup file for installation of onyo '''
from setuptools import setup, find_packages

setup(
    name='onyo',
    version='0.0.1',
    description='Textual inventory system backed by git.',
    author='Tobias Kadelka',
    author_email='t.kadelka@fz-juelich.de',
    packages=find_packages(),
    license='ISC',
    install_requires=[
        'GitPython',
        'pyyaml',
        'ruamel.yaml'
    ],
    extras_require={
        'tests': ['pytest', 'pytest-shell-utilities', 'flake8'],
        'docs': ['sphinx', 'sphinx-argparse', 'sphinx-rtd-theme']},
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'onyo=onyo.main:main'
        ],
    },
    include_package_data=True,
)
