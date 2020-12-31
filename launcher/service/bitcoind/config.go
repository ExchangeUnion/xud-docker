package bitcoind

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type Mode string

const (
	Native   Mode = "native"
	External      = "external"
	Neutrino      = "neutrino"
	Light         = "light"
)

type BaseConfig = base.Config

type Config struct {
	BaseConfig

	Mode           string   `usage:"%(name)s service mode"`
	Rpchost        string `usage:"External %(name)s RPC hostname"`
	Rpcport        uint16 `usage:"External %(name)s RPC port"`
	Rpcuser        string `usage:"External %(name)s RPC username"`
	Rpcpass        string `usage:"External %(name)s RPC password"`
	Zmqpubrawblock string `usage:"External %(name)s ZeroMQ raw blocks publication address"`
	Zmqpubrawtx    string `usage:"External %(name)s ZeroMQ raw transactions publication address"`
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/bitcoind:0.20.1"
	} else {
		image = "exchangeunion/bitcoind:latest"
	}

	return &Config{
		BaseConfig: BaseConfig{
			Image:    image,
			Disabled: true,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
		Mode:           Light,
		Rpchost:        "",
		Rpcport:        0,
		Rpcuser:        "",
		Rpcpass:        "",
		Zmqpubrawblock: "",
		Zmqpubrawtx:    "",
	}
}
