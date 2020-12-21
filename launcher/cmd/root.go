package cmd

import (
	"context"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/core"
	"github.com/spf13/cobra"
	"math/rand"
	"os"
	"os/signal"
	"time"
)

var (
	rootCmd = &cobra.Command{
		Use:           "launcher",
		Short:         fmt.Sprintf("XUD environment launcher"),
		SilenceUsage:  true,
		SilenceErrors: true,
	}
	launcher *core.Launcher
)

func init() {
	var err error
	launcher, err = core.NewLauncher()
	if err != nil {
		panic(err)
	}
	err = launcher.AddServiceFlags(rootCmd)
	if err != nil {
		panic(err)
	}
}

func Execute() {
	rand.Seed(time.Now().UnixNano())
	err := rootCmd.Execute()
	launcher.Close()
	if err != nil {
		if err.Error() == "interrupted" {
			os.Exit(130) // 128 + SIGINT(2)
		}
		fmt.Printf("ERROR: %s\n", err)
		os.Exit(1)
	}
}

func newContext() (context.Context, func()) {
	ctx, cancel := context.WithCancel(context.Background())
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)
	_cancel := func() {
		signal.Stop(c)
		cancel()
	}

	// cancel ctx when SIGINT
	go func() {
		select {
		case <-c:
			cancel()
		case <-ctx.Done():
		}
	}()

	return ctx, _cancel
}
