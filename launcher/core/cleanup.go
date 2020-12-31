package core

import (
	"context"
	"golang.org/x/sync/errgroup"
	"os"
	"os/exec"
)

func (t *Launcher) stopService(ctx context.Context, name string) error {
	s, err := t.GetService("boltz")
	if err != nil {
		return err
	}
	if err := s.Stop(ctx); err != nil {
		return err
	}
	return nil
}

func (t *Launcher) stopAll(ctx context.Context) error {
	if err := t.stopService(ctx, "boltz"); err != nil {
		return err
	}

	if err := t.stopService(ctx, "xud"); err != nil {
		return err
	}

	g, ctx := errgroup.WithContext(ctx)
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

func (t *Launcher) down(ctx context.Context) error {
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
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr

	return c.Run()
}

func (t *Launcher) removeFiles(ctx context.Context) error {
	if err := os.Chdir(t.HomeDir); err != nil {
		return err
	}
	if err := os.RemoveAll(t.NetworkDir); err != nil {
		return err
	}
	return nil
}

func (t *Launcher) Cleanup(ctx context.Context) error {
	// stop all
	if err := t.stopAll(ctx); err != nil {
		return err
	}

	// down
	if err := t.down(ctx); err != nil {
		return err
	}

	// remove all network dir content
	if err := t.removeFiles(ctx); err != nil {
		return err
	}

	return nil
}
