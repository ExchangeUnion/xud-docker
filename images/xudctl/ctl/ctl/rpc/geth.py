from web3 import Web3
from requests.exceptions import ConnectionError
import traceback


class Geth:
    def __init__(self, connstr):
        p = Web3.HTTPProvider(connstr)
        self.client = Web3(p)

    @property
    def status(self):
        try:
            # isRunning = False
            # try:
            #     w3.admin.nodeInfo
            #     isRunning = True
            # except:
            #     return "Stopped"
            syncing = self.client.eth.syncing
            if not syncing:
                return "Preparing sync (can take several minutes)"
            blocks = syncing["currentBlock"]
            headers = syncing["highestBlock"]
            progress = blocks / headers * 100
            if progress > 95:
                return "OK"
            else:
                return "Syncing: {:.2f}% ({}/{})".format(progress, blocks, headers)
        # except ConnectionError:
        #     return "(connecting...)"
        # except Exception as e:
        #     return "Error: %s" % type(e)
        except:
            return "Preparing sync (can take several minutes)"
