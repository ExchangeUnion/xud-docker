package main

import (
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/core"
	"math/rand"
	"os"
	"time"
)

func main() {
	rand.Seed(time.Now().UnixNano())

	launcher, err := core.NewLauncher()
	if err != nil {
		fmt.Printf("Failed to create launcher: %s\n", err)
		os.Exit(1)
	}
	err = launcher.Run()
	if err != nil {
		if err.Error() == "interrupted" {
			os.Exit(130) // 128 + SIGINT(2)
		}
		fmt.Printf("ERROR: %s\n", err)
		os.Exit(1)
	}
}
