from web3 import Web3
import sys

print(Web3.toChecksumAddress(sys.argv[1]))
