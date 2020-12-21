package types

type Context interface {
	GetNetwork() Network
	GetNetworkDir() string
	GetService(name string) (Service, error)
	GetExternalIp() string
	GetBackupDir() string
	GetDataDir() string
}
