package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(cleanupCmd)
}

var cleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "Clean up OpenDEX environment",
	PreRunE: func(cmd *cobra.Command, args []string) error {
		return launcher.Apply()
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx, cancel := newContext()
		defer cancel()
		return launcher.Cleanup(ctx)
	},
}
