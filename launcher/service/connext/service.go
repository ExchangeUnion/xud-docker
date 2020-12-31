package connext

import (
	"context"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/service/geth"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"strings"
)

type Base = base.Service

type Service struct {
	*Base
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

func (t *Service) IsHealthy(ctx context.Context) bool {
	output, err := t.Exec(ctx, "curl", "-s", "http://localhost:5040/health")
	if err != nil {
		return false
	}
	return string(output) == ""
}

func (t *Service) GetStatus(ctx context.Context) (string, error) {
	status, err := t.Base.GetStatus(ctx)
	if err != nil {
		return "", err
	}
	if status != "Container running" {
		return status, nil
	}

	if t.IsHealthy(ctx) {
		return "Ready", nil
	}

	return "Starting...", nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}

	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/app/connext-store", t.DataDir))

	network := t.Context.GetNetwork()

	if strings.Contains(c.Image, "vector_node") {
		t.Environment["VECTOR_CONFIG"] = `{
	"adminToken": "ddrWR8TK8UMTyR",
	"chainAddresses": {
		"1337": {
		"channelFactoryAddress": "0x2eC39861B9Be41c20675a1b727983E3F3151C576",
		"channelMastercopyAddress": "0x7AcAcA3BC812Bcc0185Fa63faF7fE06504D7Fa70",
		"transferRegistryAddress": "0xB2b8A1d98bdD5e7A94B3798A13A94dEFFB1Fe709",
		"TestToken": ""
		}
	},
	"chainProviders": {
		"1337": "http://35.234.110.95:8545"
	},
	"domainName": "",
	"logLevel": "debug",
	"messagingUrl": "https://messaging.connext.network",
	"production": true,
	"mnemonic": "crazy angry east hood fiber awake leg knife entire excite output scheme"
}`
		t.Environment["VECTOR_SQLITE_FILE"] = "/database/store.db"
		t.Environment["VECTOR_PROD"] = "true"
	} else {
		t.Environment["LEGACY_MODE"] = "true"
		switch network {
		case types.Simnet:
			t.Environment["CONNEXT_ETH_PROVIDER_URL"] = "http://connext.simnet.exchangeunion.com:8545"
			t.Environment["CONNEXT_NODE_URL"] = "https://connext.simnet.exchangeunion.com"
		case types.Testnet:
			t.Environment["CONNEXT_NODE_URL"] = "https://connext.testnet.exchangeunion.com"
		case types.Mainnet:
			t.Environment["CONNEXT_NODE_URL"] = "https://connext.boltz.exchange"
		}
	}

	if network != types.Simnet {
		s, err := t.Context.GetService("geth")
		if err != nil {
			return err
		}

		params, err := s.GetRpcParams()
		if err != nil {
			return err
		}

		t.Environment["CONNEXT_ETH_PROVIDER_URL"] = params.(geth.RpcParams).ToUri()
	}

	return nil
}

func (t *Service) GetRpcParams() (interface{}, error) {
	var params = make(map[string]interface{})
	params["type"] = "HTTP"
	params["host"] = "connext"
	params["port"] = 5040
	return params, nil
}
