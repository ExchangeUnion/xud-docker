package litecoind

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/bitcoind"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type BaseConfig = bitcoind.Config

type Config struct {
	BaseConfig
}

func (t *Service) GetDefaultConfig() interface{} {
	base := t.Base.GetDefaultConfig().(*bitcoind.Config)

	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/litecoind:0.18.1"
	} else {
		image = "exchangeunion/litecoind:latest"
	}
	base.BaseConfig.Image = t.Base.GetBranchImage(image)

	return &Config{
		BaseConfig: *base,
	}
}
