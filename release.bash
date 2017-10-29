#!/usr/bin/env bash
set -euo pipefail


echo "Running in $VIRTUAL_ENV"
python3 -c 'import pypandoc'

rm -rf dist/
python3 setup.py sdist             # source distribution
python3 setup.py bdist_wheel       # built package

read -s -p "Password: " password
printf "\n"
twine upload dist/* -p "$password"

# Make documentation
rm -rf docs/
pydocmd build

# Upload docs
cd docs/site/
rsync -acrhvzP --delete ./ rahiel@ghazali:~/cpu.re/public/telegram-send/docs
# archive, checksum, recursive, human readable, verbose, compress, partial/progress
cd -
