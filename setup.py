#!/usr/bin/env python3
from setuptools import setup

from telegram_send import __version__


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

    py_modules=["telegram_send"],
    install_requires=["python-telegram-bot>=2.8.3", "colorama", "appdirs"],
    entry_points={"console_scripts": ["telegram-send=telegram_send:main"]},

    author="Rahiel Kasim",
    author_email="rahielkasim@gmail.com",
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        # "Development Status :: 5 - Production/Stable",
        # "Development Status :: 6 - Mature",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Communications :: Chat",
        "Topic :: Utilities"
    ],
    keywords="telegram send message file"
)
