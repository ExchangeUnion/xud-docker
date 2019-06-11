import requests
from requests.exceptions import ConnectionError
import logging

class Raiden:
    def __init__(self, connstr):
        self.prefix = connstr
        pass

    @property
    def status(self):
        try:
            r = requests.get(self.prefix + "/api/v1/address")
            logging.info('Raiden status: %s', r)
            return "OK"
        # except ConnectionError:
        #     return "(connecting...)"
        # except Exception as e:
        #     return "Error: %s" % type(e)
        except:
            return "Waiting for sync"
