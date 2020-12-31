package webui

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
		image = "exchangeunion/webui:1.0.0"
	} else {
		image = "exchangeunion/webui:latest"
	}

	return &Config{
		BaseConfig: BaseConfig{
			Image: image,
			Disabled: true,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
	}
}
