#!/bin/sh
set -ex
flake8
mypy .
python test_expecttest.py
