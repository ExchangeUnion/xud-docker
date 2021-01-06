package core

import (
	"bufio"
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/logging"
	"github.com/ExchangeUnion/xud-docker/launcher/service/arby"
	"github.com/ExchangeUnion/xud-docker/launcher/service/bitcoind"
	"github.com/ExchangeUnion/xud-docker/launcher/service/boltz"
	"github.com/ExchangeUnion/xud-docker/launcher/service/connext"
	"github.com/ExchangeUnion/xud-docker/launcher/service/geth"
	"github.com/ExchangeUnion/xud-docker/launcher/service/litecoind"
	"github.com/ExchangeUnion/xud-docker/launcher/service/lnd"
	"github.com/ExchangeUnion/xud-docker/launcher/service/proxy"
	"github.com/ExchangeUnion/xud-docker/launcher/service/webui"
	"github.com/ExchangeUnion/xud-docker/launcher/service/xud"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"github.com/iancoleman/strcase"
	"github.com/mitchellh/go-homedir"
	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
)

type Launcher struct {
	Logger         *logrus.Entry
	Services       map[string]types.Service
	ServicesOrder  []string
	ServicesConfig map[string]interface{}

	HomeDir string

	Network types.Network

	NetworkDir       string
	DataDir          string
	LogsDir          string
	BackupDir        string
	DefaultBackupDir string

	DockerComposeFile string
	ConfigFile        string

	DefaultPasswordMarkFile string
	ExternalIp              string

	UsingDefaultPassword bool

	rootCmd *cobra.Command
	client  *http.Client
}

func defaultHomeDir() (string, error) {
	homeDir, err := homedir.Dir()
	if err != nil {
		return "", fmt.Errorf("failed to get home directory: %s", err)
	}
	switch runtime.GOOS {
	case "linux":
		return filepath.Join(homeDir, ".xud-docker"), nil
	case "darwin":
		return filepath.Join(homeDir, "Library", "Application Support", "XudDocker"), nil
	case "windows":
		return filepath.Join(homeDir, "AppData", "Local", "XudDocker"), nil
	default:
		return "", fmt.Errorf("unsupported operating system: %s", runtime.GOOS)
	}
}

func getNetwork() types.Network {
	if value, ok := os.LookupEnv("NETWORK"); ok {
		return types.Network(value)
	}
	return "mainnet"
}

func getNetworkDir(homeDir string, network types.Network) string {
	if value, ok := os.LookupEnv("NETWORK_DIR"); ok {
		return value
	}
	return filepath.Join(homeDir, string(network))
}

func getBackupDir(networkDir string, dockerComposeFile string) string {
	dir := getDefaultBackupDir(networkDir)

	// TODO parse backup location from 1) xud container 2) docker-compose file 3) config.json
	f, err := os.Open(dockerComposeFile)
	if err != nil {
		return dir
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, "/root/backup") {
			line = strings.TrimSpace(line)
			// fix broken colon (before) in backup location (
			line = strings.ReplaceAll(line, "::", ":")
			line = strings.TrimPrefix(line, "- ")
			line = strings.TrimSuffix(line, ":/root/backup")
			return line
		}
	}
	return dir
}

func getDefaultBackupDir(networkDir string) string {
	return filepath.Join(networkDir, "backup")
}

func getExternalIp(networkDir string) string {
	// Backward compatible with lnd.env
	lndEnv := filepath.Join(networkDir, "lnd.env")
	f, err := os.Open(lndEnv)
	if err != nil {
		return ""
	}
	defer f.Close()
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		parts := strings.Split(line, "=")
		if len(parts) == 2 {
			key := strings.TrimSpace(parts[0])
			value := strings.TrimSpace(parts[1])
			if key == "EXTERNAL_IP" {
				return value
			}
		}
	}
	return ""
}

func NewLauncher() (*Launcher, error) {
	homeDir, err := defaultHomeDir()
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(homeDir); os.IsNotExist(err) {
		if err := os.Mkdir(homeDir, 0755); err != nil {
			return nil, err
		}
	}

	network := getNetwork()
	networkDir := getNetworkDir(homeDir, network)

	if _, err := os.Stat(networkDir); os.IsNotExist(err) {
		if err := os.Mkdir(networkDir, 0755); err != nil {
			return nil, err
		}
	}

	dataDir := filepath.Join(networkDir, "data")

	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		if err := os.Mkdir(dataDir, 0755); err != nil {
			return nil, err
		}
	}

	logsDir := filepath.Join(networkDir, "logs")

	if _, err := os.Stat(logsDir); os.IsNotExist(err) {
		if err := os.Mkdir(logsDir, 0755); err != nil {
			return nil, err
		}
	}

	dockerComposeFile := filepath.Join(networkDir, "docker-compose.yml")
	configFile := filepath.Join(networkDir, "config.json")
	defaultPasswordMarkFile := filepath.Join(networkDir, ".default-password")
	backupDir := getBackupDir(networkDir, dockerComposeFile)
	defaultBackupDir := getDefaultBackupDir(networkDir)

	externalIp := getExternalIp(networkDir)

	rootCmd := &cobra.Command{
		Use:           "launcher",
		Short:         fmt.Sprintf("XUD environment launcher (%s)", network),
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	logrus.StandardLogger().SetLevel(logrus.DebugLevel)
	logrus.StandardLogger().SetFormatter(&logging.Formatter{})

	config := tls.Config{RootCAs: nil, InsecureSkipVerify: true}

	l := Launcher{
		Logger:   logrus.NewEntry(logrus.StandardLogger()).WithField("name", "core"),
		Services: make(map[string]types.Service),

		HomeDir:                 homeDir,
		Network:                 network,
		NetworkDir:              networkDir,
		DataDir:                 dataDir,
		LogsDir:                 logsDir,
		BackupDir:               backupDir,
		DefaultBackupDir:        defaultBackupDir,
		DockerComposeFile:       dockerComposeFile,
		ConfigFile:              configFile,
		DefaultPasswordMarkFile: defaultPasswordMarkFile,
		ExternalIp:              externalIp,
		UsingDefaultPassword:    true,
		rootCmd:                 rootCmd,
		client: &http.Client{
			Transport: &http.Transport{
				TLSClientConfig: &config,
			},
		},
	}

	l.Services, l.ServicesOrder, err = initServices(&l, network)
	if err != nil {
		return nil, err
	}

	if err := l.addServiceFlags(rootCmd); err != nil {
		return nil, err
	}

	setupCmd := &cobra.Command{
		Use:   "setup",
		Short: "Bring up your XUD environment in one command",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}
			if err := l.Setup(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	cleanupCmd := &cobra.Command{
		Use:   "cleanup",
		Short: "Cleanup the XUD environment",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}
			if err := l.Cleanup(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	genCmd := &cobra.Command{
		Use:   "gen",
		Short: "Generate docker-compose.yml and config.json files",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}

			if err := l.Gen(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	downCmd := &cobra.Command{
		Use:   "down",
		Short: "Shutdown the XUD environment",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}

			if err := l.Down(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	stopCmd := &cobra.Command{
		Use:   "stop",
		Short: "Stop services",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}

			if err := l.Stop(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	startCmd := &cobra.Command{
		Use:   "start",
		Short: "Start services",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}

			if err := l.Start(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	restartCmd := &cobra.Command{
		Use:   "restart",
		Short: "Restart services",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx, cancel := context.WithCancel(context.Background())
			c := make(chan os.Signal, 1)
			signal.Notify(c, os.Interrupt)
			defer func() {
				signal.Stop(c)
				cancel()
			}()

			// cancel ctx when SIGINT
			go func() {
				select {
				case <-c:
					cancel()
				case <-ctx.Done():
				}
			}()

			if err := l.Apply(); err != nil {
				return err
			}

			if err := l.Restart(ctx); err != nil {
				return err
			}
			return nil
		},
	}

	rootCmd.AddCommand(setupCmd)
	rootCmd.AddCommand(cleanupCmd)
	rootCmd.AddCommand(genCmd)
	rootCmd.AddCommand(downCmd)
	rootCmd.AddCommand(stopCmd)
	rootCmd.AddCommand(startCmd)
	rootCmd.AddCommand(restartCmd)

	return &l, nil
}

func getDefaultValue(dv reflect.Value, fieldName string) interface{} {
	f := dv.FieldByName(fieldName)
	return f.Interface()
}

func (t *Launcher) addFlags(serviceName string, configType reflect.Type, defaultValues reflect.Value, cmd *cobra.Command, config reflect.Value) error {
	for i := 0; i < configType.NumField(); i++ {
		field := configType.Field(i)

		fieldName := field.Name
		fieldType := field.Type
		value := getDefaultValue(defaultValues, fieldName)

		if fieldType.Kind() == reflect.Struct {
			if err := t.addFlags(serviceName, fieldType, reflect.ValueOf(value), cmd, config.FieldByIndex([]int{i})); err != nil {
				return err
			}
			continue
		}

		p := config.FieldByName(fieldName).Addr().Interface()

		key := fmt.Sprintf("%s.%s", serviceName, strcase.ToKebab(fieldName))

		usage := field.Tag.Get("usage")

		// t.Logger.Debugf("[flag] --%s (%#v)", key, value)

		switch fieldType.Kind() {
		case reflect.String:
			cmd.PersistentFlags().StringVar(p.(*string), key, value.(string), usage)
		case reflect.Bool:
			cmd.PersistentFlags().BoolVar(p.(*bool), key, value.(bool), usage)
		case reflect.Uint16:
			cmd.PersistentFlags().Uint16Var(p.(*uint16), key, value.(uint16), usage)
		case reflect.Slice:
			// FIXME differentiate slice item type
			cmd.PersistentFlags().StringSliceVar(p.(*[]string), key, value.([]string), usage)
		default:
			return errors.New("unsupported config struct field type: " + fieldType.Kind().String())
		}
		if err := viper.BindPFlag(key, cmd.PersistentFlags().Lookup(key)); err != nil {
			return err
		}
	}

	return nil
}

func (t *Launcher) addServiceFlags(cmd *cobra.Command) error {

	t.ServicesConfig = make(map[string]interface{})

	for _, name := range t.ServicesOrder {
		s := t.Services[name]

		defaultConfig := s.GetDefaultConfig()

		configPtr := reflect.TypeOf(defaultConfig)
		if configPtr.Kind() != reflect.Ptr {
			return errors.New("GetDefaultConfig should return a reference of config struct")
		}
		configType := configPtr.Elem() // real config type
		//t.Logger.Debugf("%s: %s.%s", s.GetName(), configType.PkgPath(), configType.Name())

		dv := reflect.ValueOf(defaultConfig).Elem()

		config := reflect.New(configType)

		t.ServicesConfig[name] = config.Interface()

		if err := t.addFlags(name, configType, dv, cmd, reflect.Indirect(config)); err != nil {
			return err
		}
	}
	return nil
}

func initServices(ctx types.Context, network types.Network) (map[string]types.Service, []string, error) {
	var services []types.Service
	var order []string

	proxy_, err := proxy.New(ctx, "proxy")
	if err != nil {
		return nil, nil, err
	}

	lndbtc, err := lnd.New(ctx, "lndbtc", lnd.Bitcoin)
	if err != nil {
		return nil, nil, err
	}

	lndltc, err := lnd.New(ctx, "lndltc", lnd.Litecoin)
	if err != nil {
		return nil, nil, err
	}

	connext_, err := connext.New(ctx, "connext")
	if err != nil {
		return nil, nil, err
	}

	xud_, err := xud.New(ctx, "xud")
	if err != nil {
		return nil, nil, err
	}

	arby_, err := arby.New(ctx, "arby")
	if err != nil {
		return nil, nil, err
	}

	webui_, err := webui.New(ctx, "webui")
	if err != nil {
		return nil, nil, err
	}

	switch network {
	case "simnet":
		services = []types.Service{
			proxy_,
			lndbtc,
			lndltc,
			connext_,
			xud_,
			arby_,
			webui_,
		}
		order = []string{
			"proxy",
			"lndbtc",
			"lndltc",
			"connext",
			"xud",
			"arby",
			"webui",
		}
	case "testnet":
		bitcoind_, err := bitcoind.New(ctx, "bitcoind")
		if err != nil {
			return nil, nil, err
		}

		litecoind_, err := litecoind.New(ctx, "litecoind")
		if err != nil {
			return nil, nil, err
		}

		geth_, err := geth.New(ctx, "geth")
		if err != nil {
			return nil, nil, err
		}

		boltz_, err := boltz.New(ctx, "boltz")
		if err != nil {
			return nil, nil, err
		}

		services = []types.Service{
			proxy_,
			bitcoind_,
			litecoind_,
			geth_,
			lndbtc,
			lndltc,
			connext_,
			xud_,
			arby_,
			boltz_,
			webui_,
		}
		order = []string{
			"proxy",
			"bitcoind",
			"litecoind",
			"geth",
			"lndbtc",
			"lndltc",
			"connext",
			"xud",
			"arby",
			"boltz",
			"webui",
		}
	case "mainnet":
		bitcoind_, err := bitcoind.New(ctx, "bitcoind")
		if err != nil {
			return nil, nil, err
		}

		litecoind_, err := litecoind.New(ctx, "litecoind")
		if err != nil {
			return nil, nil, err
		}

		geth_, err := geth.New(ctx, "geth")
		if err != nil {
			return nil, nil, err
		}

		boltz_, err := boltz.New(ctx, "boltz")
		if err != nil {
			return nil, nil, err
		}

		services = []types.Service{
			proxy_,
			bitcoind_,
			litecoind_,
			geth_,
			lndbtc,
			lndltc,
			connext_,
			xud_,
			arby_,
			boltz_,
			webui_,
		}
		order = []string{
			"proxy",
			"bitcoind",
			"litecoind",
			"geth",
			"lndbtc",
			"lndltc",
			"connext",
			"xud",
			"arby",
			"boltz",
			"webui",
		}
	}

	result := make(map[string]types.Service)
	for _, s := range services {
		result[s.GetName()] = s
	}

	return result, order, nil
}

func (t *Launcher) Run() error {
	err := t.rootCmd.Execute()
	if err != nil {
		return err
	}
	return nil
}

func (t *Launcher) GetService(name string) (types.Service, error) {
	if s, ok := t.Services[name]; ok {
		return s, nil
	}
	return nil, fmt.Errorf("service not found: %s", name)
}

// apply configurations into services
func (t *Launcher) Apply() error {
	for _, name := range t.ServicesOrder {
		s := t.Services[name]
		//t.Logger.Debugf("Apply %s", s.GetName())
		if err := s.Apply(t.ServicesConfig[name]); err != nil {
			return err
		}
	}
	return nil
}

func (t *Launcher) GetNetwork() types.Network {
	return t.Network
}

func (t *Launcher) GetExternalIp() string {
	return ""
}

func (t *Launcher) GetNetworkDir() string {
	return t.NetworkDir
}

func (t *Launcher) GetBackupDir() string {
	return t.BackupDir
}

func (t *Launcher) GetDataDir() string {
	return t.DataDir
}
