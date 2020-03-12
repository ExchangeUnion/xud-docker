FROM python:3.7-alpine3.10 as builder
RUN apk add --no-cache bash git make gcc musl-dev libffi-dev
ARG REPO=ExchangeUnion/raiden
ARG BRANCH=develop
# This is a "hack" to automatically invalidate the cache in case there are new commits
#ADD https://api.github.com/repos/$REPO/commits/$BRANCH /dev/null
RUN git clone -b $BRANCH https://github.com/$REPO /app/raiden
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app/raiden
RUN make install

FROM python:3.7-alpine3.10
RUN apk add --no-cache bash curl
COPY --from=builder /opt/venv /opt/venv
WORKDIR /opt
COPY entrypoint.sh onboarder.py /opt/
ENTRYPOINT ["/opt/entrypoint.sh"]
EXPOSE 5001
VOLUME ["/root/.raiden"]
