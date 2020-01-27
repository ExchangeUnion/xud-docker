#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="utils",
    version="1.0",
    description='Xud-Docker Utilities',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'launcher': ['banner.txt'],
        'launcher.config': ['*.conf']
    },
    scripts=['bin/args_parser', 'bin/config_parser'],
    install_requires=requirements,
)
