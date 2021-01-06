package boltz

import (
	"context"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type Base = base.Service

type Service struct {
	*Base
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
		Base: s,
	}, nil
}

type Info struct {
	Bitcoin  string
	Litecoin string
}

func (t *Service) GetInfo(ctx context.Context) (*Info, error) {
	var err error
	info := Info{}

	_, err = t.Exec(ctx, "wrapper", "btc", "getinfo")
	if err != nil {
		info.Bitcoin = "down"
	} else {
		info.Bitcoin = "up"
	}

	_, err = t.Exec(ctx, "wrapper", "ltc", "getinfo")
	if err != nil {
		info.Litecoin = "down"
	} else {
		info.Litecoin = "up"
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
		return "", err
	}

	if info.Bitcoin == "up" && info.Litecoin == "up" {
		return "Ready", nil
	}

	return fmt.Sprintf("btc %s; ltc %s", info.Bitcoin, info.Litecoin), nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}
	var lndbtc, lndltc types.Service
	var err error
	lndbtc, err = t.Context.GetService("lndbtc")
	if err != nil {
		return err
	}
	lndltc, err = t.Context.GetService("lndltc")
	if err != nil {
		return err
	}

	t.Volumes = append(t.Volumes,
		fmt.Sprintf("%s:/root/.boltz", t.DataDir),
		fmt.Sprintf("%s:/root/.lndbtc", lndbtc.GetDataDir()),
		fmt.Sprintf("%s:/root/.lndltc", lndltc.GetDataDir()),
	)

	return nil
}

func (t *Service) GetRpcParams() (interface{}, error) {
	var btc = make(map[string]interface{})
	var ltc = make(map[string]interface{})
	var params = make(map[string]interface{})

	params["bitcoin"] = btc
	params["litecoin"] = ltc

	//proxy, err := t.Context.GetService("proxy")
	//if err != nil {
	//	return nil, err
	//}

	dataDir := fmt.Sprintf("/root/network/data/%s", t.Name)

	btc["type"] = "gRPC"
	btc["host"] = "boltz"
	btc["port"] = 9002
	btc["tlsCert"] = fmt.Sprintf("%s/bitcoin/tls.cert", dataDir)
	btc["macaroon"] = fmt.Sprintf("%s/bitcoin/admin.macaroon", dataDir)

	ltc["type"] = "gRPC"
	ltc["host"] = "boltz"
	ltc["port"] = 9102
	ltc["tlsCert"] = fmt.Sprintf("%s/litecoin/tls.cert", dataDir)
	ltc["macaroon"] = fmt.Sprintf("%s/litecoin/admin.macaroon", dataDir)

	return params, nil
}
