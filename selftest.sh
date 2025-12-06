#!/bin/bash

if [ -z "$1" ]; then
    echo "Call this script with the path of a python interpreter as argument"
    echo "Example:"
    echo "$ selftest.sh python3.11"
    echo ""
    exit 1
fi

PY="$1"

if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Error: '$PY' not found or not executable."
    exit 1
fi

if "$PY" - << EOF >/dev/null 2>&1
print("ok")
EOF
then
    echo "OK: '$PY' is a working Python interpreter."
else
    echo "Error: '$PY' is not a usable Python interpreter."
    exit 1
fi

$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt
$PY -m pip install -r test/requirements.txt
$PY -m pytest
