package lnd

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/service/bitcoind"
	"github.com/ExchangeUnion/xud-docker/launcher/service/litecoind"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"regexp"
	"strconv"
	"strings"
)

type Base = base.Service

type Chain string

const (
	Bitcoin  Chain = "bitcoin"
	Litecoin       = "litecoin"
)

var (
	reNeutrinoSyncingNew   = regexp.MustCompile(`^.*New block: height=(?P<Height>\d+),.*$`)
	reNeutrinoSyncingBegin = regexp.MustCompile(`^.*Syncing to block height (\d+) from peer.*$`)
	reNeutrinoSyncingEnd   = regexp.MustCompile(`^.*Fully caught up with cfheaders at height (\d+), waiting at tip for new blocks.*$`)
	reNeutrinoSyncing      = regexp.MustCompile(`^.*Fetching set of checkpointed cfheaders filters from height=(\d+).*$`)
)

type Service struct {
	*Base
	Chain Chain
}

func New(ctx types.Context, name string, chain Chain) (*Service, error) {
	s, err := base.New(ctx, name)
	if err != nil {
		return nil, err
	}

	return &Service{
		Base:  s,
		Chain: chain,
	}, nil
}

type Info struct {
	SyncedToChain bool `json:"synced_to_chain"`
	BlockHeight   uint `json:"block_height"`
}

func (t *Service) GetInfo(ctx context.Context) (*Info, error) {
	output, err := t.Exec(ctx, "lncli", "-n", string(t.Context.GetNetwork()), "-c", string(t.Chain), "getinfo")
	if err != nil {
		return nil, err
	}
	var info Info
	err = json.Unmarshal([]byte(output), &info)
	if err != nil {
		return nil, fmt.Errorf("failed to parse output as JSON: %#v", output)
	}
	return &info, nil
}

func (t *Service) getNeutrinoSyncingStatus(ctx context.Context) (string, error) {
	pEnd := reNeutrinoSyncingEnd
	pBegin := reNeutrinoSyncingBegin
	p := reNeutrinoSyncing
	pNew := reNeutrinoSyncingNew

	startedAt, err := t.GetStartedAt(ctx)
	if err != nil {
		return "", err
	}

	lines, err := t.GetLogs(ctx, startedAt, "")
	if err != nil {
		return "", err
	}
	var total uint64
	var synced uint64

	total = 0
	synced = 0

	for i := len(lines) - 1; i >= 0; i-- {
		line := lines[i]
		m := pEnd.FindStringSubmatch(line)
		if m != nil {
			height, err := strconv.ParseUint(m[1], 10, 64)
			if err != nil {
				return "", fmt.Errorf("failed to parse height: %s", err)
			}
			total = height
			synced = height
			break
		}

		if synced == 0 {
			m = p.FindStringSubmatch(line)
			if m != nil {
				height, err := strconv.ParseUint(m[1], 10, 64)
				if err != nil {
					return "", fmt.Errorf("failed to parse height: %s", err)
				}
				synced = height
			} else {
				m = pNew.FindStringSubmatch(line)
				if m != nil {
					height, err := strconv.ParseUint(m[1], 10, 64)
					if err != nil {
						return "", fmt.Errorf("failed to parse height: %s", err)
					}
					synced = height
				}
			}
		}

		if total == 0 {
			m = pBegin.FindStringSubmatch(line)
			if m != nil {
				height, err := strconv.ParseUint(m[1], 10, 64)
				if err != nil {
					return "", fmt.Errorf("failed to parse height: %s", err)
				}
				total = height
			}
		}

		if synced != 0 && total != 0 {
			break
		}
	}

	return t.getSyncingText(synced, total), nil
}

func (t *Service) getSyncingText(synced uint64, total uint64) string {
	if total < synced {
		total = synced
	}
	p := float32(synced) / float32(total) * 100.0
	if p > 0.005 {
		p = p - 0.005
	} else {
		p = 0
	}
	return fmt.Sprintf("Syncing %.2f%% (%d/%d)", p, synced, total)
}

func (t *Service) getSyncedHeight(ctx context.Context) (uint, error) {
	startedAt, err := t.Base.GetStartedAt(ctx)
	if err != nil {
		return 0, err
	}
	lines, err := t.GetLogs(ctx, startedAt, "")
	if err != nil {
		return 0, err
	}
	for i := len(lines) - 1; i >= 0; i-- {
		m := reNeutrinoSyncingNew.FindStringSubmatch(lines[i])
		if m != nil {
			height, err := strconv.ParseUint(m[1], 10, 64)
			if err != nil {
				return 0, fmt.Errorf("failed to parse height: %s", err)
			}
			return uint(height), nil
		}
	}
	return 0, nil
}

func (t *Service) UseNeutrino() bool {
	if t.Context.GetNetwork() == types.Simnet {
		return true
	}
	switch t.Chain {
	case Bitcoin:
		s, err := t.Context.GetService("bitcoind")
		if err != nil {
			panic(err)
		}
		if s.GetMode() == "neutrino" || s.GetMode() == "light" {
			return true
		}
	case Litecoin:
		s, err := t.Context.GetService("litecoind")
		if err != nil {
			panic(err)
		}
		if s.GetMode() == "neutrino" || s.GetMode() == "light" {
			return true
		}
	}
	return false
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
			if strings.Contains(err.Output, "Wallet is encrypted") {
				return "Wallet locked. Unlock with xucli unlock.", nil
			}
			if strings.Contains(err.Output, "admin.macaroon: no such file") {
				if t.UseNeutrino() {
					return t.getNeutrinoSyncingStatus(ctx)
				}
			}
			if strings.Contains(err.Output, "open /root/.lnd/tls.cert: no such file or directory") {
				return "Starting...", nil
			}
			if strings.Contains(err.Output, "connection refused") {
				return "Starting...", nil
			}
			t.Logger.Errorf("%s", strings.TrimSpace(err.Output))
		}
		return "", err
	}
	if info.SyncedToChain {
		return "Ready", nil
	} else {
		total := info.BlockHeight
		synced, err := t.getSyncedHeight(ctx)
		if err != nil {
			return "", err
		}
		return t.getSyncingText(uint64(synced), uint64(total)), nil
	}
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}
	t.Volumes = append(t.Volumes, fmt.Sprintf("%s:/root/.lnd", t.DataDir))
	t.Environment["CHAIN"] = string(t.Chain)

	if c.PreserveConfig {
		t.Environment["PRESERVE_CONFIG"] = "true"
	} else {
		t.Environment["PRESERVE_CONFIG"] = "false"
	}

	if t.Context.GetExternalIp() != "" {
		t.Environment["EXTERNAL_IP"] = t.Context.GetExternalIp()
	}

	network := t.Context.GetNetwork()

	if network == types.Simnet {
		switch t.Chain {
		case Bitcoin:
			t.Command = append(t.Command,
				"--debuglevel=debug",
				"--nobootstrap",
				"--minbackoff=30s",
				"--maxbackoff=24h",
				"--bitcoin.active",
				"--bitcoin.simnet",
				"--bitcoin.node=neutrino",
				"--bitcoin.defaultchanconfs=6",
				"--routing.assumechanvalid",
				"--neutrino.connect=btcd.simnet.exchangeunion.com:38555",
				"--chan-enable-timeout=0m10s",
				"--max-cltv-expiry=5000",
			)
		case Litecoin:
			t.Command = append(t.Command,
				"--debuglevel=debug",
				"--nobootstrap",
				"--minbackoff=30s",
				"--maxbackoff=24h",
				"--litecoin.active",
				"--litecoin.simnet",
				"--litecoin.node=neutrino",
				"--litecoin.defaultchanconfs=6",
				"--routing.assumechanvalid",
				"--neutrino.connect=btcd.simnet.exchangeunion.com:39555",
				"--chan-enable-timeout=0m10s",
				"--max-cltv-expiry=20000",
			)
		}
	} else {
		switch t.Chain {
		case Bitcoin:
			s, err := t.Context.GetService("bitcoind")
			if err != nil {
				return err
			}
			mode := s.(*bitcoind.Service).Mode
			if mode == bitcoind.External {
				params, err := s.GetRpcParams()
				if err != nil {
					return err
				}
				p := params.(bitcoind.RpcParams)
				t.Environment["RPCHOST"] = p.Host
				t.Environment["RPCPORT"] = fmt.Sprintf("%d", p.Port)
				t.Environment["RPCUSER"] = p.Username
				t.Environment["RPCPASS"] = p.Password
				t.Environment["ZMQPUBRAWBLOCK"] = p.Zmqpubrawblock
				t.Environment["ZMQPUBRAWTX"] = p.Zmqpubrawtx
			} else {
				t.Environment["NEUTRINO"] = "True"
			}
		case Litecoin:
			s, err := t.Context.GetService("litecoind")
			if err != nil {
				return err
			}
			mode := s.(*litecoind.Service).Mode
			if mode == bitcoind.External {
				params, err := s.GetRpcParams()
				if err != nil {
					return err
				}
				p := params.(bitcoind.RpcParams)
				t.Environment["RPCHOST"] = p.Host
				t.Environment["RPCPORT"] = fmt.Sprintf("%d", p.Port)
				t.Environment["RPCUSER"] = p.Username
				t.Environment["RPCPASS"] = p.Password
				t.Environment["ZMQPUBRAWBLOCK"] = p.Zmqpubrawblock
				t.Environment["ZMQPUBRAWTX"] = p.Zmqpubrawtx
			} else {
				t.Environment["NEUTRINO"] = "True"
			}
		}
	}

	return nil
}

func (t *Service) GetRpcParams() (interface{}, error) {
	var params = make(map[string]interface{})
	params["type"] = "gRPC"
	params["host"] = t.Name
	params["port"] = 10009
	dataDir := fmt.Sprintf("/root/network/data/%s", t.Name)
	params["tlsCert"] = fmt.Sprintf("%s/tls.cert", dataDir)
	params["macaroon"] = fmt.Sprintf("%s/data/chain/%s/%s/readonly.macaroon", dataDir, t.Chain, t.Context.GetNetwork())
	return params, nil
}
