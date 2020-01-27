FROM python:3.8-alpine3.10
RUN apk add --no-cache docker-cli
RUN pip install toml docker demjson
ADD . /src
WORKDIR /src
RUN python setup.py install
