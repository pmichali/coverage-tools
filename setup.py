# -*- coding: utf-8 -*-


"""setup.py: setuptools control."""


import re
from setuptools import setup


version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('whodunit/whodunit.py').read(),
    re.M
    ).group(1)


with open("README.rst", "rb") as f:
    long_descr = f.read().decode("utf-8")


setup(
    name="commit-coverage",
    packages=["whodunit"],
    entry_points={
        "console_scripts": ['whodunit = whodunit.whodunit:main']
        },
    version=version,
    description="Identifies owner(s) for module lines in a git repo.",
    long_description=long_descr,
    author="Paul Michali",
    author_email="pc@michali.net",
    )
