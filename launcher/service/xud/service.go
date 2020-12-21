package xud

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"os"
	"path/filepath"
	"strings"
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

	return &Service{
		Base:      s,
		RpcParams: RpcParams{},
	}, nil
}

type LndInfo struct {
	Status string
}

type ConnextInfo struct {
	Status string
}

type Info struct {
	Lndbtc  LndInfo
	Lndltc  LndInfo
	Connext ConnextInfo
}

func (t *Service) GetInfo(ctx context.Context) (*Info, error) {
	output, err := t.Exec(ctx, "xucli", "getinfo", "-j")
	if err != nil {
		return nil, err
	}
	var result = make(map[string]interface{})
	err = json.Unmarshal([]byte(output), &result)
	if err != nil {
		return nil, errors.New(output)
	}

	lndbtc := LndInfo{}
	lndltc := LndInfo{}

	for _, item := range result["lndMap"].([]interface{}) {
		info := item.([]interface{})
		switch info[0].(string) {
		case "BTC":
			lndbtc.Status = info[1].(map[string]interface{})["status"].(string)
		case "LTC":
			lndltc.Status = info[1].(map[string]interface{})["status"].(string)
		}
	}

	info := Info{
		Lndbtc: lndbtc,
		Lndltc: lndltc,
		Connext: ConnextInfo{
			Status: result["connext"].(map[string]interface{})["status"].(string),
		},
	}
	return &info, nil
}

func (t *Service) GetStatus(ctx context.Context) (string, error) {
	status, err := t.Base.GetStatus(ctx)
	if err != nil {
		return "", err
	}
	if status != "Container running" {
		return status, nil
	}

	info, err := t.GetInfo(ctx)
	if err != nil {
		if err, ok := err.(service.ErrExec); ok {
			if strings.Contains(err.Output, "xud is locked") {
				nodekey := filepath.Join(t.DataDir, "nodekey.dat")
				if _, err := os.Stat(nodekey); os.IsNotExist(err) {
					return "Wallet missing. Create with xucli create/restore.", nil
				}
				return "Wallet locked. Unlock with xucli unlock.", nil
			} else if strings.Contains(err.Output, "tls cert could not be found at /root/.xud/tls.cert") {
				return "Starting...", nil
			} else if strings.Contains(err.Output, "xud is starting") {
				return "Starting...", nil
			} else if strings.Contains(err.Output, "is xud running?") {
				// could not connect to xud at localhost:18886, is xud running?
				return "Starting...", nil
			}
		}
		return "", fmt.Errorf("get info: %w", err)
	}

	lndbtc := info.Lndbtc.Status
	lndltc := info.Lndltc.Status
	connext := info.Connext.Status

	var notReady []string

	if lndbtc != "Ready" {
		notReady = append(notReady, "lndbtc")
	}

	if lndltc != "Ready" {
		notReady = append(notReady, "lndltc")
	}

	if connext != "Ready" {
		notReady = append(notReady, "connext")
	}

	if len(notReady) == 0 {
		return "Ready", nil
	}

	if strings.Contains(lndbtc, "has no active channels") || strings.Contains(lndltc, "has no active channels") || strings.Contains(connext, "has no active channels") {
		return "Waiting for channels", nil
	}

	return fmt.Sprintf("Waiting for %s", strings.Join(notReady, ", ")), nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}
	t.Environment["NODE_ENV"] = "production"

	if c.PreserveConfig {
		t.Environment["PRESERVE_CONFIG"] = "true"
	} else {
		t.Environment["PRESERVE_CONFIG"] = "false"
	}

	lndbtc, err := t.Context.GetService("lndbtc")
	if err != nil {
		return err
	}

	lndltc, err := t.Context.GetService("lndltc")
	if err != nil {
		return err
	}

	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/.xud", t.DataDir))
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/.lndbtc", lndbtc.GetDataDir()))
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/.lndltc", lndltc.GetDataDir()))
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/backup", t.Context.GetBackupDir()))

	network := t.Context.GetNetwork()

	var port uint16

	switch network {
	case types.Simnet:
		port = 28886
		t.Ports = append(t.Ports, "28885")
	case types.Testnet:
		port = 18886
		t.Ports = append(t.Ports, "18885")
	case types.Mainnet:
		port = 8886
		t.Ports = append(t.Ports, "8885")
	}

	t.RpcParams.Type = "gRPC"
	t.RpcParams.Host = t.Name
	t.RpcParams.Port = port
	dataDir := fmt.Sprintf("/root/network/data/%s", t.Name)
	t.RpcParams.TlsCert = fmt.Sprintf("%s/tls.cert", dataDir)

	return nil
}

type RpcParams struct {
	Type    string `json:"type"`
	Host    string `json:"host"`
	Port    uint16 `json:"port"`
	TlsCert string `json:"tlsCert"`
}

func (t *Service) GetRpcParams() (interface{}, error) {
	return t.RpcParams, nil
}
