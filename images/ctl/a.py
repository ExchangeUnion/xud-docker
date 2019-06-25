import grpc
import os
import lnrpc_pb2 as ln
import lnrpc_pb2_grpc as lnrpc
import codecs
import time

def create_stub(cert, macaroon, rpcaddr):
    with open(os.path.expanduser(macaroon), 'rb') as f:
        macaroon_bytes = f.read()
        macaroon = codecs.encode(macaroon_bytes, 'hex')

    def metadata_callback(context, callback):
        callback([('macaroon', macaroon)], None)

    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser(cert), 'rb').read()
    # build ssl credentials using the cert the same as before
    cert_creds = grpc.ssl_channel_credentials(cert)
    # now build meta data credentials
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    # combine the cert credentials and the macaroon auth credentials
    # such that every call is properly encrypted and authenticated
    combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel(rpcaddr, combined_creds)
    return lnrpc.LightningStub(channel)

lndbtc = create_stub('~/.lndbtc/tls.cert',
                     '~/.lndbtc/data/chain/bitcoin/simnet/admin.macaroon', 'lndbtc:10009')
lndltc = create_stub('~/.lndltc/tls.cert',
                     '~/.lndltc/data/chain/litecoin/simnet/admin.macaroon', 'lndltc:10009')

def is_synced_to_chain(stub):
    try:
        return stub.GetInfo(ln.GetInfoRequest()).synced_to_chain
    except Exception as e:
        print(e)
        return False

def connect(stub, addr):
    try:
        parts = addr.split('@')
        request = ln.ConnectPeerRequest(
            addr=ln.LightningAddress(
                pubkey=parts[0],
                host=parts[1]
            )
        )
        return stub.ConnectPeer(request)
    except Exception as e:
        print(e)


while not is_synced_to_chain(lndbtc):
    time.sleep(1)
    print('Retry lndbtc getinfo to see if synced_to_chain')

connect(lndbtc, '030c2ffd29a92e2dd2fb6fb046b0d9157e0eda8b11caa0e439d0dd6a46a444381c@35.229.81.83:10012')

while not is_synced_to_chain(lndltc):
    time.sleep(1)
    print('Retry lndltc getinfo to see if synced_to_chain')

connect(lndltc, '02f5e0324909bdb635d4d6a50aa07c517db59f5d18219fd058f9faa3ef3a1fd83a@35.229.81.83:10011')
