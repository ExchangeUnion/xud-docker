package lnd

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type BaseConfig = base.Config

type Mode string

const (
	Native   Mode = "native"
	External      = "external"
)

type Config struct {
	BaseConfig

	Mode string

	PreserveConfig bool
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	switch t.Chain {
	case Bitcoin:
		switch network {
		case types.Mainnet:
			image = "exchangeunion/lndbtc:0.11.1-beta"
		case types.Simnet:
			image = "exchangeunion/lndbtc-simnet:latest"
		case types.Testnet:
			image = "exchangeunion/lndbtc:latest"
		}
	case Litecoin:
		switch network {
		case types.Mainnet:
			image = "exchangeunion/lndltc:0.11.0-beta.rc1"
		case types.Simnet:
			image = "exchangeunion/lndltc-simnet:latest"
		case types.Testnet:
			image = "exchangeunion/lndltc:latest"
		}
	}

	return &Config{
		BaseConfig: BaseConfig{
			Image: image,
			Disabled: false,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
		Mode: string(Native),
		PreserveConfig: false,
	}
}
