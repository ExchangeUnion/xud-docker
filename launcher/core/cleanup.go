package core

import (
	"context"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/types"
	"github.com/ExchangeUnion/xud-docker/launcher/utils"
	dt "github.com/docker/docker/api/types"
	docker "github.com/docker/docker/client"
	"golang.org/x/sync/errgroup"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

func (t *Launcher) stopService(ctx context.Context, name string) error {
	t.Logger.Debugf("Stopping %s", name)
	s, err := t.GetService(name)
	if err != nil {
		return err
	}
	if err := s.Stop(ctx); err != nil {
		if strings.Contains(err.Error(), "No such container") {
			t.Logger.Debugf("Service %s stopped already", name)
			return nil
		}
		return err
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			return err
		}
		t.Logger.Debugf("%s: %s", name, status)

		if status == "Container exited" {
			break
		}

		select {
		case <-ctx.Done():
			return errors.New("interrupted")
		case <-time.After(3 * time.Second):
		}
	}

	return nil
}

func (t *Launcher) Create(ctx context.Context) error {
	return nil
}

func (t *Launcher) Start(ctx context.Context) error {
	return nil
}

func (t *Launcher) Restart(ctx context.Context) error {
	return nil
}

func (t *Launcher) Stop(ctx context.Context) error {
	if t.Network != types.Simnet {
		if err := t.stopService(ctx, "boltz"); err != nil {
			return err
		}
	}

	if err := t.stopService(ctx, "xud"); err != nil {
		return err
	}

	g, _ := errgroup.WithContext(ctx)
	g.Go(func() error {
		return t.stopService(ctx, "lndbtc")
	})
	g.Go(func() error {
		return t.stopService(ctx, "lndltc")
	})
	g.Go(func() error {
		return t.stopService(ctx, "connext")
	})
	if err := g.Wait(); err != nil {
		return err
	}

	if err := t.stopService(ctx, "proxy"); err != nil {
		return err
	}

	return nil
}

func (t *Launcher) Down(ctx context.Context) error {
	wd, err := os.Getwd()
	if err != nil {
		return err
	}
	defer os.Chdir(wd)

	if err := os.Chdir(t.NetworkDir); err != nil {
		return err
	}

	if _, err := os.Stat("docker-compose.yml"); os.IsNotExist(err) {
		if err := t.Gen(ctx); err != nil {
			return err
		}
	}
	c := exec.Command("docker-compose", "down")
	return utils.Run(ctx, c)
}

func (t *Launcher) removeFiles(ctx context.Context) error {
	t.Logger.Debugf("homedir=%s", t.HomeDir)
	if err := os.Chdir(t.HomeDir); err != nil {
		return err
	}
	fmt.Printf("Do you want to remove all %s files (%s)? [y/N] ", t.Network, t.NetworkDir)
	var reply string
	_, err := fmt.Scanln(&reply)
	if err != nil {
		if runtime.GOOS == "windows" && err.Error() == "unexpected newline" {
			return nil
		}
		return err
	}
	reply = strings.ToLower(reply)
	if reply == "y" || reply == "yes" {
		if err := os.RemoveAll(t.NetworkDir); err != nil {
			return err
		}
	}
	return nil
}

func (t *Launcher) finalDown(ctx context.Context) error {
	var err error

	client, err := docker.NewClientWithOpts(docker.FromEnv)
	if err != nil {
		return fmt.Errorf("create docker client: %w", err)
	}

	for _, service := range t.ServicesOrder {
		containerName := fmt.Sprintf("%s_%s_1", t.Network, service)
		_, err := client.ContainerInspect(ctx, containerName)
		if err != nil {
			continue
		}
		t.Logger.Debugf("Removing container %s", containerName)
		err = client.ContainerRemove(ctx, containerName, dt.ContainerRemoveOptions{
			RemoveVolumes: false,
			RemoveLinks:   false,
			Force:         false,
		})
		if err != nil {
			err = client.ContainerRemove(ctx, containerName, dt.ContainerRemoveOptions{
				RemoveVolumes: false,
				RemoveLinks:   false,
				Force:         true,
			})
			if err != nil {
				return fmt.Errorf("remove container %s: %w", containerName, err)
			}
		}
	}

	networkName := fmt.Sprintf("%s_default", t.Network)
	_, err = client.NetworkInspect(ctx, networkName, dt.NetworkInspectOptions{})
	if err == nil {
		t.Logger.Debugf("Removing network %s", networkName)
		err = client.NetworkRemove(ctx, networkName)
		if err != nil {
			return fmt.Errorf("remove network %s: %w", networkName, err)
		}
	}

	return nil
}

func (t *Launcher) Cleanup(ctx context.Context) error {
	// stop all running services
	if err := t.Stop(ctx); err != nil {
		return fmt.Errorf("stop: %w", err)
	}

	// docker-compose down
	if err := t.Down(ctx); err != nil {
		return fmt.Errorf("down: %w", err)
	}

	// make sure no more containers and docker network existed
	if err := t.finalDown(ctx); err != nil {
		return fmt.Errorf("final down: %w", err)
	}

	// remove all network dir content
	if err := t.removeFiles(ctx); err != nil {
		return fmt.Errorf("remove files: %w", err)
	}

	return nil
}
