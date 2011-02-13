#!/bin/sh

pylint -f colorized --max-line-length=120  --disable=C0111 qostool/

nosetests
