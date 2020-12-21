package litecoind

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/bitcoind"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type Base = bitcoind.Service

type Service struct {
	*Base
}

func New(ctx types.Context, name string) (*Service, error) {
	s, err := bitcoind.New(ctx, name)
	if err != nil {
		return nil, err
	}
	s.ContainerDataDir = "/root/.litecoind"

	return &Service{
		Base: s,
	}, nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(&c.BaseConfig); err != nil {
		return err
	}

	network := t.Context.GetNetwork()

	if t.Mode == bitcoind.Native {
		if network == types.Mainnet {
			t.RpcParams.Port = 9332
		} else {
			t.RpcParams.Port = 19332
		}
	}

	return nil
}
