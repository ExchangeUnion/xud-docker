import grpc
from . import xurpc_pb2 as xu
from .xurpc_pb2_grpc import XudStub
import logging


class Xud:
    def __init__(self, connstr, cert):
        creds = grpc.ssl_channel_credentials(cert)
        connstr = connstr.replace('grpc://', '')
        channel = grpc.secure_channel(connstr, creds)
        self.client = XudStub(channel)

    @property
    def status(self):
        try:
            self.client.GetInfo(xu.GetInfoRequest())
            return "OK"
        # except grpc.RpcError as e:
        #     return "Error: (gRPC) %s" % e.details()
        # except Exception as e:
        #     return "Error: %s" % type(e)
        except:
            return "Waiting for sync"
