FROM python:3.8.2-alpine3.12
RUN pip install toml docker demjson
ADD . /usr/local/src/utils
WORKDIR /usr/local/src/utils
RUN python setup.py install
WORKDIR /root
