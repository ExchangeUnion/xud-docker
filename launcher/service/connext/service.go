package connext

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/service/geth"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"math/rand"
	"strings"
)

type Base = base.Service

const (
	ChainId                       = "1337"
	SimnetChannelFactoryAddress   = "0x09f37Ee0662E13e7d07e84CE77705E981Be79406"
	SimnetTransferRegistryAddress = "0xE70F6686f0AF6a858256B073ABB74fC5C79cE343"
	SimnetEthProvider             = "http://35.234.110.95:8545"
)

var (
	passwordRunes = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
	// This is a placeholder mnemonic that is required for startup, but is not being used since it will be overwritten by xud.
	placeholderMnemonic = "crazy angry east hood fiber awake leg knife entire excite output scheme"
)

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
		t.Environment["VECTOR_CONFIG"] = t.getVectorConfig(ChainId, SimnetChannelFactoryAddress, SimnetTransferRegistryAddress, SimnetEthProvider)
		t.Environment["VECTOR_SQLITE_FILE"] = "/database/store.db"
		t.Environment["VECTOR_PROD"] = "true"
	} else {
		// legacy connext indra stuff

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

func (t *Service) generateAdminToken(length int) string {
	b := make([]rune, length)
	n := len(passwordRunes)
	for i := range b {
		b[i] = passwordRunes[rand.Intn(n)]
	}
	return string(b)
}

func (t *Service) getVectorConfig(chainId, channelFactoryAddress, transferRegistryAddress, ethProvider string) string {
	config := map[string]interface{}{
		"adminToken": t.generateAdminToken(20),
		"chainAddresses": map[string]interface{}{
			chainId: map[string]interface{}{
				"channelFactoryAddress":   channelFactoryAddress,
				"transferRegistryAddress": transferRegistryAddress,
			},
		},
		"chainProviders": map[string]interface{}{
			chainId: ethProvider,
		},
		"domainName":   "",
		"logLevel":     "debug",
		"messagingUrl": "https://messaging.connext.network",
		"production":   true,
		"mnemonic":     placeholderMnemonic,
	}
	j, err := json.MarshalIndent(config, "", "    ")
	if err != nil {
		panic(err)
	}
	return string(j)
}
