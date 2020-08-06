FROM python:3.8.2-alpine3.11
RUN pip install toml docker demjson pyyaml
ADD . /usr/local/src/utils
WORKDIR /usr/local/src/utils
RUN python setup.py install
WORKDIR /root
