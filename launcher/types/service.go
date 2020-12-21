package types

import "context"

type Service interface {
	GetName() string
	GetStatus(ctx context.Context) (string, error)
	Start(ctx context.Context) error
	Stop(ctx context.Context) error
	Restart(ctx context.Context) error
	Create(ctx context.Context) error
	Remove(ctx context.Context) error
	Up(ctx context.Context) error
	GetLogs(ctx context.Context, since string, tail string) ([]string, error)
	FollowLogs(ctx context.Context, since string, tail string) (<-chan string, func(), error)
	Exec(ctx context.Context, name string, args ...string) (string, error)

	GetImage() string
	GetHostname() string
	GetCommand() []string
	GetEnvironment() map[string]string
	GetPorts() []string
	GetVolumes() []string
	IsDisabled() bool
	IsRunning() bool

	GetRpcParams() (interface{}, error)
	GetDefaultConfig() interface{}
	Apply(cfg interface{}) error

	GetDataDir() string
	GetMode() string

	Rescue(ctx context.Context) bool
}
