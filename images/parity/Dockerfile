ARG VERSION

FROM parity/parity:v$VERSION
USER root
RUN apt-get update && apt-get install -y bash expect
WORKDIR /
COPY entrypoint.sh wallet.exp /
ENTRYPOINT [ "./entrypoint.sh" ]
