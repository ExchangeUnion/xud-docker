import grpc
import os
import lnrpc_pb2 as ln
import lnrpc_pb2_grpc as lnrpc
import codecs
import time

# Lnd admin macaroon is at ~/.lnd/data/chain/bitcoin/simnet/admin.macaroon on Linux and
# ~/Library/Application Support/Lnd/data/chain/bitcoin/simnet/admin.macaroon on Mac
with open(os.path.expanduser('~/.lndbtc/data/chain/bitcoin/simnet/admin.macaroon'), 'rb') as f:
    macaroon_bytes = f.read()
    macaroon = codecs.encode(macaroon_bytes, 'hex')

def metadata_callback(context, callback):
    # for more info see grpc docs
    callback([('macaroon', macaroon)], None)

os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
cert = open(os.path.expanduser('~/.lndbtc/tls.cert'), 'rb').read()
# build ssl credentials using the cert the same as before
cert_creds = grpc.ssl_channel_credentials(cert)
# now build meta data credentials
auth_creds = grpc.metadata_call_credentials(metadata_callback)
# combine the cert credentials and the macaroon auth credentials
# such that every call is properly encrypted and authenticated
combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
channel = grpc.secure_channel('lndbtc:10009', combined_creds)
stub = lnrpc.LightningStub(channel)

def lndbtc_getinfo():
    return stub.GetInfo(ln.GetInfoRequest())

def lndbtc_connect():
    return stub.ConnectPeer(ln.ConnectPeerRequest())

while not lndbtc_getinfo().synced_to_chain:
    time.sleep(1)
    print('Retry getinfo to see if synced_to_chain')

print('Synced!')

lndbtc_connect()
