package proxy

import (
	"context"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"net"
	"runtime"
	"time"
)

type Base = base.Service

type Service struct {
	*Base
	RpcParams RpcParams
}

func New(ctx types.Context, name string) (*Service, error) {
	s, err := base.New(ctx, name)
	if err != nil {
		return nil, err
	}

	var port uint16
	switch ctx.GetNetwork() {
	case types.Simnet:
		port = 28889
	case types.Testnet:
		port = 18889
	case types.Mainnet:
		port = 8889
	}

	return &Service{
		Base: s,
		RpcParams: RpcParams{
			Type: "HTTP",
			Port: port,
		},
	}, nil
}

func (t *Service) checkApiPort() error {
	addr := fmt.Sprintf("127.0.0.1:%d", t.RpcParams.Port)
	conn, err := net.DialTimeout("tcp", addr, 3*time.Second)
	if err != nil {
		return err
	}
	if conn == nil {
		return fmt.Errorf("failed to connect to %s", addr)
	}
	return nil
}

func (t *Service) GetStatus(ctx context.Context) (string, error) {
	status, err := t.Base.GetStatus(ctx)
	if err != nil {
		return "", err
	}
	if status != "Container running" {
		return status, nil
	}

	if err := t.checkApiPort(); err == nil {
		return "Ready", nil
	}

	return "Starting...", nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}

	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/.proxy", t.DataDir))
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/network", t.Context.GetNetworkDir()))
	if runtime.GOOS == "windows" {
		t.Volumes = append(t.Volumes, "//var/run/docker.sock:/var/run/docker.sock")
	} else {
		t.Volumes = append(t.Volumes, "/var/run/docker.sock:/var/run/docker.sock")
	}

	if c.Tls {
		t.Command = append(t.Command, "--tls")
		t.RpcParams.Scheme = "https"
	} else {
		t.RpcParams.Scheme = "http"
	}

	t.Ports = append(t.Ports, fmt.Sprintf("127.0.0.1:%d:8080", t.RpcParams.Port))

	return nil
}

type RpcParams struct {
	Type   string `json:"type"`
	Scheme string `json:"scheme"`
	Port   uint16 `json:"port"`
}

func (t *Service) GetRpcParams() (interface{}, error) {
	return t.RpcParams, nil
}
