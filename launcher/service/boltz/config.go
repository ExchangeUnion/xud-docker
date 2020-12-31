package boltz

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type BaseConfig = base.Config

type Config struct {
	BaseConfig
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/boltz:1.2.0"
	} else {
		image = "exchangeunion/boltz:latest"
	}

	return &Config{
		BaseConfig: BaseConfig{
			Image: image,
			Disabled: false,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
	}
}
