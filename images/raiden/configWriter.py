import sys
import os
import io

network = sys.argv[1]
configPath = "/home/root/.raiden/config.toml"

class ConfigVariables:
    def __init__(self, endpointRegistry, secretRegistry, tokenNetworkRegistry, matrixServer):
        self.endpointRegistry = endpointRegistry
        self.secretRegistry = secretRegistry
        self.tokenNetworkRegistry = tokenNetworkRegistry
        self.matrixServer = matrixServer

def writeConfigLine(file: io.TextIOWrapper, key: str, value: str):
    file.write("{key} = \"{value}\"\n".format(key = key, value = value))

def writeConfig(variables: ConfigVariables):
    file = open(configPath, "w")

    writeConfigLine(file, "endpoint-registry-contract-address", variables.endpointRegistry)
    writeConfigLine(file, "secret-registry-contract-address", variables.secretRegistry)
    writeConfigLine(file, "tokennetwork-registry-contract-address", variables.tokenNetworkRegistry)

    writeConfigLine(file, "matrix-server", variables.matrixServer)

    file.close()

# TODO: add contract addresses for mainnet
mainnetConfig = ConfigVariables(
    "",
    "",
    "",
    "http://raidentransport.exchangeunion.com"
)

testnetConfig = ConfigVariables(
    "0xc890fF7f17A8C27651c1dC9483D941Bec5EDB386",
    "0x10e6e104ff8D8a8AB019F0daA88aDa06f4DeF84D",
    "0x84485026e44f0deF6965BA4bB1aDaEb9d0D695DA",
    "http://transport01.raiden.network"
)

# TODO: add simnet values?

# Terminate the script if the config file exists already
if os.path.exists(configPath):
    print("Raiden config exists already")
    sys.exit()

if network == "mainnet":
    writeConfig(mainnetConfig)
elif network == "testnet":
    writeConfig(testnetConfig)
else:
    print("Could not find network {}".format(network))
