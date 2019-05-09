FROM python:3-alpine
RUN apk add --no-cache alpine-sdk
RUN pip install grpcio googleapis-common-protos
WORKDIR /app
ADD a.py lnrpc_pb2_grpc.py lnrpc_pb2.py /app/
ENTRYPOINT python a.py