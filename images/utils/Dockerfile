FROM python:3-alpine3.10
RUN pip install --no-cache-dir toml
ADD config-parser.py /usr/local/bin/config-parser
RUN chmod u+x /usr/local/bin/config-parser
