FROM golang:alpine AS build-stage
RUN apk add --no-cache alpine-sdk
RUN git clone https://github.com/lightninglabs/neutrino $GOPATH/src/github.com/lightninglabs/neutrino
WORKDIR $GOPATH/src/github.com/lightninglabs/neutrino
RUN GO111MODULE=on go install .

# Final stage
FROM alpine
COPY --from=build-stage /go/bin/neutrino /bin/
COPY entrypoint.sh /
ENTRYPOINT [ "./entrypoint.sh" ]
EXPOSE 18556
