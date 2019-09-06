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
COPY --from=builder /opt/venv /opt/venv
COPY entrypoint.sh checksum.py onboarder.py configWriter.py /
EXPOSE 5001
ENTRYPOINT [ "./entrypoint.sh" ]
