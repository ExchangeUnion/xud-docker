FROM python:3-alpine3.10
WORKDIR /app
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ADD launcher /usr/local/lib/python3.8/site-packages/launcher
ADD config_parser.py /usr/local/bin/config_parser
ADD args_parser.py /usr/local/bin/args_parser
RUN chmod u+x /usr/local/bin/config_parser
RUN chmod u+x /usr/local/bin/args_parser
RUN echo b
