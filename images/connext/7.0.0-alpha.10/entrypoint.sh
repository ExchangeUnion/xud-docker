#!/bin/bash
set -m
# use exec to properly respond to SIGINT
exec npm run start
