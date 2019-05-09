import grpc
import os
import lnrpc_pb2 as ln
import lnrpc_pb2_grpc as lnrpc

def lndbtc_getinfo():
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser('~/.lndbtc/tls.cert'), 'rb').read()
    creds = grpc.ssl_channel_credentials(cert)
    channel = grpc.secure_channel('lndbtc:10009', creds)
    stub = lnrpc.LightningStub(channel)
    return stub.GetInfo(ln.GetInfoRequest())

lndbtc_getinfo()

