package arby

import (
	"context"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	_xud "github.com/ExchangeUnion/xud-docker/launcher/service/xud"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
)

type Base = base.Service
type Xud = _xud.Service
type XudRpcParams = _xud.RpcParams

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

func (t *Service) getXud() (*Xud, error) {
	s, err := t.Context.GetService("xud")
	if err != nil {
		return nil, err
	}
	sXud, ok := s.(*Xud)
	if !ok {
		return nil, errors.New("cannot convert to *xud.Service")
	}
	return sXud, nil
}

func (t *Service) Apply(cfg interface{}) error {
	c := cfg.(*Config)
	if err := t.Base.Apply(c.BaseConfig); err != nil {
		return err
	}

	xud, err := t.getXud()
	if err != nil {
		return err
	}

	t.Volumes = append(t.Volumes,
		fmt.Sprintf("%s:/root/.arby", t.DataDir),
		fmt.Sprintf("%s:/root/.xud", xud.DataDir),
	)

	params, err := xud.GetRpcParams()
	if err != nil {
		return err
	}

	xudRpc := params.(XudRpcParams)

	t.Environment["NODE_ENV"] = "production"
	t.Environment["LOG_LEVEL"] = "trace"
	t.Environment["OPENDEX_CERT_PATH"] = "/root/.xud/tls.cert"
	t.Environment["OPENDEX_RPC_HOST"] = xudRpc.Host
	t.Environment["OPENDEX_RPC_PORT"] = fmt.Sprintf("%d", xudRpc.Port)
	t.Environment["BASEASSET"] = c.BaseAsset
	t.Environment["QUOTEASSET"] = c.QuoteAsset
	t.Environment["CEX_BASEASSET"] = c.CexBaseAsset
	t.Environment["CEX_QUOTEASSET"] = c.CexQuoteAsset
	t.Environment["CEX"] = fmt.Sprintf("%s", c.Cex)
	t.Environment["CEX_API_SECRET"] = c.CexApiSecret
	t.Environment["CEX_API_KEY"] = c.CexApiKey
	t.Environment["TEST_MODE"] = fmt.Sprintf("%t", c.TestMode)
	t.Environment["MARGIN"] = c.Margin
	t.Environment["TEST_CENTRALIZED_EXCHANGE_BASEASSET_BALANCE"] = c.TestCentralizedBaseassetBalance
	t.Environment["TEST_CENTRALIZED_EXCHANGE_QUOTEASSET_BALANCE"] = c.TestCentralizedQuoteassetBalance

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

	return "Ready", nil
}
