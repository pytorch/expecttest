#!/bin/sh
set -ex
flake8
mypy --exclude=smoketests .
python test_expecttest.py
