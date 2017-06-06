#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'


echo "Running in $VIRTUAL_ENV"
python3 -c 'import pypandoc'

rm -rf dist/
python3 setup.py sdist             # source distribution
python3 setup.py bdist_wheel       # built package

read -s -p "Password: " password
printf "\n"
twine upload dist/* -p "$password"

# Make documentation
rm -rf docs/ docs.zip
pydocmd build
cd docs/site/
zip -r docs.zip ./*
cd -
mv ./docs/site/docs.zip ./
echo -e "\n\nUpload docs.zip at: https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=telegram-send"
