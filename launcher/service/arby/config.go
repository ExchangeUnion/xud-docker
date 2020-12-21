package arby

import (
	"github.com/ExchangeUnion/xud-docker/launcher/service/base"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"path/filepath"
)

type BaseConfig = base.Config

type Config struct {
	BaseConfig

	LiveCex                          bool   `usage:"Live CEX (deprecated)"`
	TestMode                         bool   `usage:"Whether to issue real orders on the centralized exchange"`
	BaseAsset                        string `usage:"Base asset"`
	QuoteAsset                       string `usage:"Quote asset"`
	CexBaseAsset                     string `usage:"Centralized exchange base asset"`
	CexQuoteAsset                    string `usage:"Centralized exchange quote asset"`
	TestCentralizedBaseassetBalance  string `usage:"Test centralized base asset balance"`
	TestCentralizedQuoteassetBalance string `usage:"Test centralized quote asset balance"`
	Cex                              string `usage:"Centralized Exchange"`
	CexApiKey                        string `usage:"CEX API key"`
	CexApiSecret                     string `usage:"CEX API secret"`
	Margin                           string `usage:"Trade margin"`
}

func (t *Service) GetDefaultConfig() interface{} {
	network := t.Context.GetNetwork()
	var image string
	if network == types.Mainnet {
		image = "exchangeunion/arby:1.4.0"
	} else {
		image = "exchangeunion/arby:latest"
	}
	return &Config{
		BaseConfig: BaseConfig{
			Image:    image,
			Disabled: true,
			Dir: filepath.Join(t.Context.GetDataDir(), t.Name),
		},
		LiveCex:                          true,
		TestMode:                         true,
		BaseAsset:                        "",
		QuoteAsset:                       "",
		CexBaseAsset:                     "",
		CexQuoteAsset:                    "",
		TestCentralizedBaseassetBalance:  "",
		TestCentralizedQuoteassetBalance: "",
		Cex:                              "binance",
		CexApiKey:                        "123",
		CexApiSecret:                     "abc",
		Margin:                           "0.04",
	}
}
