package bitcoind

import (
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type Base = base.Service

type Service struct {
	*Base
	ContainerDataDir string
	RpcParams RpcParams
	Mode Mode
}

type RpcParams struct {
	Type           string `json:"type"`
	Host           string `json:"host"`
	Port           uint16 `json:"port"`
	Username       string `json:"username"`
	Password       string `json:"password"`
	Zmqpubrawblock string `json:"zmqpubrawblock"`
	Zmqpubrawtx    string `json:"zmqpubrawtx"`
}

func New(ctx types.Context, name string) (*Service, error) {
	if ctx.GetNetwork() == types.Simnet {
		return nil, service.ErrForbiddenService
	}

	s, err := base.New(ctx, name)
	if err != nil {
		return nil, err
	}

	return &Service{
		Base:             s,
		ContainerDataDir: "/root/.bitcoind",
		RpcParams: RpcParams{},
	}, nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:%s", t.DataDir, t.ContainerDataDir))

	t.RpcParams.Type = "JSON-RPC"
	t.Mode = Mode(c.Mode)

	network := t.Context.GetNetwork()

	switch t.Mode {
	case Native:
		t.RpcParams.Host = t.Name
		if network == types.Mainnet {
			t.RpcParams.Port = 8332
		} else {
			t.RpcParams.Port = 18332
		}
		t.RpcParams.Username = "xu"
		t.RpcParams.Password = "xu"
		t.RpcParams.Zmqpubrawblock = fmt.Sprintf("tcp://%s:28332", t.Name)
		t.RpcParams.Zmqpubrawtx = fmt.Sprintf("tcp://%s:28333", t.Name)
	case External:
		t.RpcParams.Host = c.Rpchost
		t.RpcParams.Port = c.Rpcport
		t.RpcParams.Username = c.Rpcuser
		t.RpcParams.Password = c.Rpcpass
		t.RpcParams.Zmqpubrawblock = c.Zmqpubrawblock
		t.RpcParams.Zmqpubrawtx = c.Zmqpubrawtx
	case Neutrino:
	case Light:
	}

	return nil
}

func (t *Service) GetRpcParams() (interface{}, error) {
	return t.RpcParams, nil
}

func (t *Service) GetMode() string {
	return string(t.Mode)
}
