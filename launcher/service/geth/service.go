package geth

import (
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type Base = base.Service

type Mode string

const (
	Native   Mode = "native"
	External      = "external"
	Infura        = "infura"
	Light         = "light"
)

type RpcParams struct {
	Type   string `json:"type"`
	Scheme string `json:"scheme"`
	Host   string `json:"host"`
	Path   string `json:"path"`
	Port   uint16 `json:"port"`
}

func (t RpcParams) ToUri() string {
	if t.Port == 0 {
		return fmt.Sprintf("%s://%s%s", t.Scheme, t.Host, t.Path)
	}
	return fmt.Sprintf("%s://%s:%d%s", t.Scheme, t.Host, t.Port, t.Path)
}

type Service struct {
	*Base

	Mode      Mode
	RpcParams RpcParams
}

func New(ctx types.Context, name string) (*Service, error) {
	s, err := base.New(ctx, name)
	if err != nil {
		return nil, err
	}

	return &Service{
		Base: s,
	}, nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)

	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}

	t.RpcParams.Type = "JSON-RPC"

	if t.Context.GetNetwork() == types.Simnet {
		// simnet PoA eth provider
		t.RpcParams.Scheme = "http"
		t.RpcParams.Host = "35.234.110.95"
		t.RpcParams.Port = 8545
	} else {
		t.Mode = Mode(c.Mode)
		switch t.Mode {
		case External:
			t.RpcParams.Scheme = "http"
			t.RpcParams.Host = c.Rpchost
			t.RpcParams.Port = c.Rpcport
		case Infura:
			proj := c.InfuraProjectId
			network := t.Context.GetNetwork()
			if network == types.Mainnet {
				t.RpcParams.Scheme = "https"
				t.RpcParams.Host = "mainnet.infura.io"
				t.RpcParams.Path = fmt.Sprintf("/v3/%s", proj)
			} else if network == types.Testnet {
				t.RpcParams.Scheme = "https"
				t.RpcParams.Host = "rinkeyby.infura.io"
				t.RpcParams.Path = fmt.Sprintf("/v3/%s", proj)
			} else {
				return fmt.Errorf("no Infura Ethereum prodiver for %s", network)
			}
		case Light:
			network := t.Context.GetNetwork()
			if network == types.Mainnet {
				t.RpcParams.Scheme = "http"
				t.RpcParams.Host = "eth.kilrau.com"
				t.RpcParams.Port = 41007
			} else if network == types.Testnet {
				t.RpcParams.Scheme = "http"
				t.RpcParams.Host = "eth.kilrau.com"
				t.RpcParams.Port = 52041
			} else {
				return fmt.Errorf("no Light ethereum provider for %s", network)
			}
		case Native:
			t.RpcParams.Scheme = "http"
			t.RpcParams.Host = "geth"
			t.RpcParams.Port = 8545
		}
	}

	return nil
}

func (t *Service) GetRpcParams() (interface{}, error) {
	return t.RpcParams, nil
}

func (t *Service) GetMode() string {
	return string(t.Mode)
}
