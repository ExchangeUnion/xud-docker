package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(restartCmd)
}

var restartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart services",
	PreRunE: func(cmd *cobra.Command, args []string) error {
		return launcher.Apply()
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx, cancel := newContext()
		defer cancel()
		return launcher.Restart(ctx)
	},
}
