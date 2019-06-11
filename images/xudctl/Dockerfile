# build stage
FROM python:3-alpine AS builder
ADD ctl /ctl
WORKDIR /ctl
RUN python setup.py bdist_wheel

# final stage
FROM exchangeunion/xud:1.0.0-alpha.11
RUN apk add --no-cache python3-dev alpine-sdk
COPY --from=builder /ctl/dist/ctl-0.1.0-py3-none-any.whl /tmp/ctl-0.1.0-py3-none-any.whl
RUN pip3 install /tmp/ctl-0.1.0-py3-none-any.whl
COPY status /usr/local/bin/
