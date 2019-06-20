ARG version=2.4.7-stable
FROM parity/parity:v${version}
#RUN apk add --no-cache bash expect
USER root
RUN apt-get update && apt-get install -y bash expect
WORKDIR /
COPY entrypoint.sh wallet.exp /
ENTRYPOINT [ "./entrypoint.sh" ]
