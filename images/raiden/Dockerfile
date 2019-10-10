ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION} as builder
RUN apk add --no-cache bash git make gcc musl-dev libffi-dev
ARG REPO
ARG BRANCH
# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/${REPO}/commits/${BRANCH} /dev/null
RUN git clone -b ${BRANCH} https://github.com/${REPO} /app/raiden
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app/raiden
RUN make install

FROM python:${PYTHON_VERSION}
RUN apk add --no-cache bash curl supervisor
COPY --from=builder /opt/venv /opt/venv
COPY supervisord.conf /etc/supervisor/conf.d/
COPY entrypoint.sh /
EXPOSE 5001
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
