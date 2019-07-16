ARG version
FROM parity/parity:v$version
USER root
RUN apt-get update && apt-get install -y bash expect
WORKDIR /
COPY entrypoint.sh wallet.exp /
ENTRYPOINT [ "./entrypoint.sh" ]
