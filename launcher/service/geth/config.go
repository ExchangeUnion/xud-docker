package geth

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type BaseConfig = base.Config

type Config struct {
	BaseConfig

	Mode                string `usage:"%(name)s service mode"`
	Rpcscheme           string `usage:"External %(name)s RPC scheme (http, https)"`
	Rpchost             string `usage:"External %(name)s RPC hostname"`
	Rpcport             uint16 `usage:"External %(name)s RPC port"`
	InfuraProjectId     string `usage:"Infura %(name)s provider project ID"`
	InfuraProjectSecret string `usage:"Infura %(name)s provider project secret"`
	Cache               string `usage:"%(name)s cache size"`
	AncientChaindataDir string `usage:"Specify the container's volume mapping ancient chaindata directory. Can be located on a slower HDD."`
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/geth:1.9.24"
	} else {
		image = "exchangeunion/arby:latest"
	}
	return &Config{
		BaseConfig: BaseConfig{
			Image: image,
			Disabled: true,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
		Mode: Light,
	}
}
