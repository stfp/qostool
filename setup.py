#!/usr/bin/env python

import os
from setuptools import setup, find_packages

setup(
    name="qostool",
    version="1.0",
    author="Stefan Praszalowicz",
    author_email="prasza@gmail.com",
    url="https://github.com/stefanp/qostool",
    packages = [ "qostool"],
    scripts=["bin/qostool"]
)
