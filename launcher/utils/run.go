package utils

import (
	"bytes"
	"context"
	"fmt"
	"github.com/sirupsen/logrus"
	"os/exec"
	"strings"
)

var (
	logger = initLogger()
)

func initLogger() *logrus.Entry {
	logger := logrus.NewEntry(logrus.StandardLogger()).WithField("name", "utils")
	return logger
}

func Run(ctx context.Context, cmd *exec.Cmd) error {
	var buf bytes.Buffer

	cmd.Stdout = &buf
	cmd.Stderr = &buf

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start: %w", err)
	}
	done := make(chan error)
	go func() { done <- cmd.Wait() }()
	select {
	case err := <-done:
		// exited
		output := strings.TrimSpace(buf.String())
		if output != "" {
			output = "\n" + output
		}
		if err != nil {
			if exitErr, ok := err.(*exec.ExitError); ok {
				logger.Errorf("[run] %s (exit %d)%s", cmd.String(), exitErr.ExitCode(), output)
			}
			return fmt.Errorf("[run] %s: %w", cmd.String(), err)
		} else {
			logger.Debugf("[run] %s%s", cmd.String(), output)
		}
	case <-ctx.Done():
		// cancelled
		if err := cmd.Process.Kill(); err != nil {
			return fmt.Errorf("kill: %w", err)
		}
	}
	return nil
}
