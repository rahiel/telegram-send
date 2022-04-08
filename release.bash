#!/usr/bin/env bash
set -euo pipefail


echo "Running in $VIRTUAL_ENV"

rm -rf dist/
python setup.py sdist bdist_wheel  # source distribution and built package

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
