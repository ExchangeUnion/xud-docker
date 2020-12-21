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

	if strings.Contains(t.Image, "vector_node") {
		t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/database", t.DataDir))
	} else {
		t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/app/connext-store", t.DataDir))
	}

	network := t.Context.GetNetwork()

	ethProvider, err := t.getEthProvider()
	if err != nil {
		return err
	}

	if strings.Contains(c.Image, "vector_node") {
		var chainId string
		var channelFactoryAddress string
		var transferRegistryAddress string

		switch network {
		case types.Simnet:
			chainId = "1337"
			channelFactoryAddress = "0x2b19530c81E97FBc2feD79E813E4723D9bA7343B"
			transferRegistryAddress = "0xD74aafE4e2E723C53c82eb0ba8716eD386389123"
		case types.Testnet:
			chainId = "4"
		case types.Mainnet:
			chainId = "1"
		}

		t.Environment["VECTOR_CONFIG"] = t.getVectorConfig(chainId, channelFactoryAddress, transferRegistryAddress, ethProvider)
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
			t.Environment["CONNEXT_ETH_PROVIDER_URL"] = ethProvider
			t.Environment["CONNEXT_NODE_URL"] = "https://connext.testnet.exchangeunion.com"
		case types.Mainnet:
			t.Environment["CONNEXT_ETH_PROVIDER_URL"] = ethProvider
			t.Environment["CONNEXT_NODE_URL"] = "https://connext.boltz.exchange"
		}
	}

	return nil
}

func (t *Service) getEthProvider() (string, error) {
	s, err := t.Context.GetService("geth")
	if err != nil {
		return "", err
	}

	params, err := s.GetRpcParams()
	if err != nil {
		return "", err
	}

	return params.(geth.RpcParams).ToUri(), nil
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
	if chainId != "1337" {
		// we only need chainAddresses for simnet where the contract
		// addresses need to be specified manually
		delete(config, "chainAddresses")
	}
	j, err := json.MarshalIndent(config, "", "    ")
	if err != nil {
		panic(err)
	}
	return string(j)
}
