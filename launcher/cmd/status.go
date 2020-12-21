package cmd

import (
	"errors"
	"fmt"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(statusCmd)
}

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Get service status",
	PreRunE: func(cmd *cobra.Command, args []string) error {
		return launcher.Apply()
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx, cancel := newContext()
		defer cancel()
		if len(args) < 1 {
			return errors.New("service name required")
		}
		status, err := launcher.Status(ctx, args[0])
		if err != nil {
			return err
		}
		fmt.Println(status)
		return nil
	},
}
