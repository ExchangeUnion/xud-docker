from typing import Literal, NewType

XudNetwork = NewType("XudNetwork", Literal["simnet", "testnet", "mainnet"])
LndChain = NewType("LndChain", Literal["bitcoin", "litecoin"])
