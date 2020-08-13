FROM python:3.8.5-alpine3.12
RUN apk add --no-cache docker-compose
RUN pip install toml docker demjson pyyaml
WORKDIR /root
ADD launcher launcher
ENTRYPOINT ["python", "-m", "launcher"]
