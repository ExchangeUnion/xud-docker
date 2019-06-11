from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import logging
import traceback

class Bitcoind:
    def __init__(self, connstr):
        self.client = AuthServiceProxy(connstr)

    @property
    def status(self):
        """
        -28: Loading block index...
        -28: Rewinding blocks

        :return:
        """
        try:
            info = self.client.getblockchaininfo()
            blocks = info["blocks"]
            headers = info["headers"]
            progress = blocks / headers * 100
            if progress == 100:
                return "OK"
            else:
                return "Syncing: {:.2f}% ({}/{})".format(progress, blocks, headers)
        except JSONRPCException as e:
            # -28: Loading block index...
            msg = str(e)
            parts = msg.split(":")
            return parts[1].strip()
        except ConnectionResetError:
            return "(connecting...)"
        except Exception as e:
            return "Error (%s)" % type(e)
