package proxy

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type BaseConfig = base.Config

type Config struct {
	BaseConfig

	Tls bool `usage:"Enabled TLS support"`
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/proxy:1.2.0"
	} else {
		image = "exchangeunion/proxy:latest"
	}

	return &Config{
		BaseConfig: BaseConfig{
			Image: image,
			Disabled: false,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
		Tls: true,
	}
}
