FROM ubuntu:18.04
RUN apt-get update
RUN apt-get install -y software-properties-common curl
RUN add-apt-repository ppa:longsleep/golang-backports
RUN add-apt-repository ppa:deadsnakes/ppa
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN apt-get update
RUN apt-get install -y golang-go nodejs python3.7 python3.7-dev git psmisc
WORKDIR /root
RUN git clone https://github.com/ExchangeUnion/xud-simnet.git
VOLUME [ "/root/xud-simnet" ]
COPY entrypoint.sh .
RUN apt-get install -y rsync
ENTRYPOINT ./entrypoint.sh


