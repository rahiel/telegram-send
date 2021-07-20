#!/usr/bin/env python3
from setuptools import setup

from telegram_send.version import __version__

try:
    import pypandoc
    import re
    long_description = pypandoc.convert("README.md", "rst")
    # remove raw html blocks, they're not supported on pypi
    long_description = re.sub("\s+\.\. raw:: html\s*.+? -->", "", long_description, count=2)
except:
    long_description = ""


setup(
    name="telegram-send",
    version=__version__,
    description="Send messages and files over Telegram from the command-line.",
    long_description=long_description,
    url="https://github.com/rahiel/telegram-send",
    license="GPLv3+",

    python_requires=">=3.5",
    packages=['telegram_send'],
    install_requires=["python-telegram-bot>=12.1.1", "colorama", "appdirs"],

    author="Rahiel Kasim",
    author_email="rahielkasim@gmail.com",
    # https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # "Development Status :: 4 - Beta",
        "Development Status :: 5 - Production/Stable",
        # "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities"
    ],
    keywords="telegram send message file"
)
