#!/usr/bin/env python

from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="utils",
    version="1.0",
    description='Xud-Docker Utilities',
    packages=['launcher'],
    scripts=['bin/args_parser', 'bin/config_parser'],
    install_requires=requirements,
)
