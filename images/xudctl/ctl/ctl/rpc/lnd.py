import grpc
import codecs
from . import lnrpc_pb2 as ln
from .lnrpc_pb2_grpc import LightningStub
import logging

class Lnd:
    def __init__(self, connstr, cert, macaroon):
        macaroon_bytes = macaroon
        macaroon = codecs.encode(macaroon_bytes, 'hex')

        def metadata_callback(context, callback):
            callback([('macaroon', macaroon)], None)

        cert_creds = grpc.ssl_channel_credentials(cert)
        auth_creds = grpc.metadata_call_credentials(metadata_callback)
        combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

        connstr = connstr.replace('grpc://', '')

        channel = grpc.secure_channel(connstr, combined_creds)
        self.client = LightningStub(channel)

    @property
    def status(self):
        try:
            info = self.client.GetInfo(ln.GetInfoRequest())
            if info.synced_to_chain:
                return "OK"
            return "Waiting for sync"
        # except grpc.RpcError as e:
        #     return "Error: (gRPC) %s" % e.details()
        # except Exception as e:
        #     return "Error: %s" % type(e)
        except:
            return "Waiting for sync"
