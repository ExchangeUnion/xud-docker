FROM python:3.8-alpine3.10
ADD . /usr/local/src/utils
WORKDIR /usr/local/src/utils
RUN python setup.py install
WORKDIR /root
