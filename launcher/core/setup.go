package core

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/proxy"
	"github.com/ExchangeUnion/xud-docker/launcher/utils"
	"github.com/gorilla/websocket"
	"golang.org/x/sync/errgroup"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const (
	DefaultWalletPassword = "OpenDEX!Rocks"
)

var (
	errInterrupted = errors.New("interrupted")
)

func (t *Launcher) Pull(ctx context.Context) error {
	t.Logger.Debugf("Pulling images")
	cmd := exec.Command("docker-compose", "pull")
	return utils.Run(ctx, cmd)
}

func (t *Launcher) Setup(ctx context.Context) error {
	t.Logger.Debugf("Setup %s (%s)", t.Network, t.NetworkDir)

	wd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("get working directory: %w", err)
	}
	defer os.Chdir(wd)

	if err := os.Chdir(t.NetworkDir); err != nil {
		return fmt.Errorf("change directory: %w", err)
	}

	logfile := filepath.Join(t.NetworkDir, "logs", fmt.Sprintf("%s.log", t.Network))
	f, err := os.Create(logfile)
	if err != nil {
		return fmt.Errorf("create %s: %w", logfile, err)
	}
	defer f.Close()

	_, err = f.WriteString("Waiting for XUD dependencies to be ready\n")
	if err != nil {
		return fmt.Errorf("write log: %w", err)
	}

	if err := t.Gen(ctx); err != nil {
		return fmt.Errorf("generate files: %w", err)
	}

	if err := t.Pull(ctx); err != nil {
		return fmt.Errorf("pull: %w", err)
	}

	t.Logger.Debugf("Start proxy")
	if err := t.upProxy(ctx); err != nil {
		return fmt.Errorf("up proxy: %w", err)
	}

	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		defer wg.Done()
		t.Logger.Debugf("Attach to proxy")
		if err := t.attachToProxy(ctx); err != nil {
			t.Logger.Errorf("Attach to proxy: %s", err)
		}
	}()

	t.Logger.Debugf("Start lndbtc, lndltc and connext")
	if err := t.upLayer2(ctx); err != nil {
		return fmt.Errorf("up layer2: %w", err)
	}

	t.Logger.Debugf("Start xud")
	if err := t.upXud(ctx); err != nil {
		return fmt.Errorf("up xud: %w", err)
	}

	t.Logger.Debugf("Start boltz")
	if err := t.upBoltz(ctx); err != nil {
		return fmt.Errorf("up boltz: %w", err)
	}

	_, err = f.WriteString("Start shell\n")
	if err != nil {
		return fmt.Errorf("write log: %w", err)
	}
	_ = f.Close()

	fmt.Println("Attached to proxy. Press Ctrl-C to detach from it.")
	wg.Wait()

	return nil
}

func (t *Launcher) upProxy(ctx context.Context) error {
	return t.upService(ctx, "proxy", func(status string) bool {
		if status == "Ready" {
			return true
		}
		return false
	})
}

func (t *Launcher) upLnd(ctx context.Context, name string) error {
	return t.upService(ctx, name, func(status string) bool {
		if status == "Ready" {
			return true
		}
		if strings.HasPrefix(status, "Syncing 100.00%") {
			return true
		}
		if strings.HasPrefix(status, "Syncing 99.99%") {
			return true
		}
		if strings.HasPrefix(status, "Wallet locked") {
			return true
		}
		return false
	})
}

func (t *Launcher) upConnext(ctx context.Context) error {
	return t.upService(ctx, "connext", func(status string) bool {
		if status == "Ready" {
			return true
		}
		return false
	})
}

func (t *Launcher) getProxyApiUrl() (string, error) {
	s, err := t.GetService("proxy")
	if err != nil {
		return "", fmt.Errorf("get service: %w", err)
	}
	rpc, err := s.GetRpcParams()
	if err != nil {
		return "", fmt.Errorf("get rpc params: %w", err)
	}
	return rpc.(proxy.RpcParams).ToUri(), nil
}

type ApiError struct {
	Message string `json:"message"`
}

func (t *Launcher) createWallets(ctx context.Context, password string) error {
	apiUrl, err := t.getProxyApiUrl()
	if err != nil {
		return fmt.Errorf("get proxy api url: %w", err)
	}
	createUrl := fmt.Sprintf("%s/api/v1/xud/create", apiUrl)
	payload := map[string]interface{}{
		"password": password,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("encode payload: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, "POST", createUrl, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := t.client.Do(req)
	if err != nil {
		return fmt.Errorf("do reqeust: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var body ApiError
		err := json.NewDecoder(resp.Body).Decode(&body)
		if err != nil {
			return fmt.Errorf("[http %d] decode error: %w", resp.StatusCode, err)
		}
		return fmt.Errorf("[http %d] %s", resp.StatusCode, body.Message)
	}

	return nil
}

func (t *Launcher) unlockWallets(ctx context.Context, password string) error {
	apiUrl, err := t.getProxyApiUrl()
	if err != nil {
		return fmt.Errorf("get proxy api url: %w", err)
	}
	createUrl := fmt.Sprintf("%s/api/v1/xud/unlock", apiUrl)
	payload := map[string]interface{}{
		"password": password,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("encode payload: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, "POST", createUrl, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := t.client.Do(req)
	if err != nil {
		return fmt.Errorf("do reqeust: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var body ApiError
		err := json.NewDecoder(resp.Body).Decode(&body)
		if err != nil {
			return fmt.Errorf("[http %d] decode error: %w", resp.StatusCode, err)
		}
		return fmt.Errorf("[http %d] %s", resp.StatusCode, body.Message)
	}

	return nil
}

func (t *Launcher) upService(ctx context.Context, name string, checkFunc func(string) bool) error {
	s, err := t.GetService(name)
	if err != nil {
		return fmt.Errorf("get service: %w", err)
	}
	if err := s.Up(ctx); err != nil {
		return fmt.Errorf("up: %s", err)
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			t.Logger.Errorf("Failed to get status: %s", err)
		} else {
			t.Logger.Debugf("[status] %s: %s", name, status)

			if status == "Container missing" || status == "Container exited" {
				return fmt.Errorf("%s: %s", name, status)
			}

			if checkFunc(status) {
				break
			}
		}
		select {
		case <-ctx.Done(): // context cancelled
			return errInterrupted
		case <-time.After(3 * time.Second): // retry
		}
	}
	return nil
}

func (t *Launcher) upXud(ctx context.Context) error {
	return t.upService(ctx, "xud", func(status string) bool {
		if status == "Ready" {
			return true
		}
		if status == "Waiting for channels" {
			return true
		}
		if strings.HasPrefix(status, "Wallet missing") {
			if err := t.createWallets(ctx, DefaultWalletPassword); err != nil {
				t.Logger.Errorf("Failed to create: %s", err)
				return false
			}
			_, err := os.Create(t.DefaultPasswordMarkFile)
			if err != nil {
				t.Logger.Errorf("Failed to create .default-password: %s", err)
				return false
			}
			return false
		}
		if strings.HasPrefix(status, "Wallet locked") {
			if err := t.unlockWallets(ctx, DefaultWalletPassword); err != nil {
				t.Logger.Errorf("Failed to unlock: %s", err)
				return false
			}
			return false
		}
		return false
	})
}

func (t *Launcher) upBoltz(ctx context.Context) error {
	return t.upService(ctx, "boltz", func(status string) bool {
		return true
	})
}

type Request struct {
	Id     uint64   `json:"id"`
	Method string   `json:"method"`
	Params []string `json:"params"`
}

func (t *Launcher) serve(ctx context.Context, c *websocket.Conn) {
	for {
		_, message, err := c.ReadMessage()
		if err != nil {
			t.Logger.Errorf("read: %s", err)
			return
		}
		t.Logger.Debugf("recv: %s", message)

		if err := t.handleMessage(ctx, c, message); err != nil {
			t.Logger.Errorf("handle %s: %s", message, err)
		}
	}
}

func (t *Launcher) handleMessage(ctx context.Context, c *websocket.Conn, msg []byte) error {
	var req Request
	if err := json.Unmarshal(msg, &req); err != nil {
		return err
	}

	switch req.Method {
	case "getinfo":
		return t.hookGetInfo(ctx, c, req.Id)
	case "backupto":
		return t.hookBackupTo(ctx, c, req.Id, req.Params[0])
	}

	return nil
}

type WalletsInfo struct {
	DefaultPassword bool `json:"defaultPassword"`
	MnemonicShown   bool `json:"mnemonicShown"`
}

type BackupInfo struct {
	Location        string `json:"location"`
	DefaultLocation bool   `json:"defaultLocation"`
}

type Info struct {
	Wallets WalletsInfo `json:"wallets"`
	Backup  BackupInfo  `json:"backup"`
}

func (t *Launcher) GetInfo() Info {
	defaultPassword := true
	if _, err := os.Stat(t.DefaultPasswordMarkFile); os.IsNotExist(err) {
		defaultPassword = false
	}

	return Info{
		Wallets: WalletsInfo{
			DefaultPassword: defaultPassword,
			MnemonicShown:   !defaultPassword,
		},
		Backup: BackupInfo{
			Location:        t.BackupDir,
			DefaultLocation: t.BackupDir == t.DefaultBackupDir,
		},
	}
}

func (t *Launcher) BackupTo(ctx context.Context, location string) error {
	t.BackupDir = location
	if err := t.Apply(); err != nil {
		return err
	}
	if err := t.Gen(ctx); err != nil {
		return err
	}
	if err := t.upXud(ctx); err != nil {
		return err
	}
	return nil
}

func (t *Launcher) hookGetInfo(ctx context.Context, c *websocket.Conn, id uint64) error {
	var resp = make(map[string]interface{})

	info, err := json.Marshal(t.GetInfo())
	if err != nil {
		return err
	}
	resp["result"] = string(info)
	resp["error"] = nil
	resp["id"] = id

	j, err := json.Marshal(resp)
	if err != nil {
		return err
	}

	t.Logger.Debugf("send: %s", j)

	err = c.WriteMessage(websocket.TextMessage, j)
	if err != nil {
		return err
	}

	return nil
}

func (t *Launcher) hookBackupTo(ctx context.Context, c *websocket.Conn, id uint64, location string) error {
	return t.BackupTo(ctx, location)
}

func (t *Launcher) attachToProxy(ctx context.Context) error {
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)

	s, err := t.GetService("proxy")
	if err != nil {
		return err
	}

	params, err := s.GetRpcParams()
	if err != nil {
		return err
	}

	port := params.(proxy.RpcParams).Port

	u := url.URL{Scheme: "wss", Host: fmt.Sprintf("127.0.0.1:%d", port), Path: "/launcher"}
	t.Logger.Debugf("Connecting to %s", u.String())

	config := tls.Config{RootCAs: nil, InsecureSkipVerify: true}

	dialer := websocket.DefaultDialer
	dialer.TLSClientConfig = &config
	c, _, err := dialer.Dial(u.String(), nil)
	if err != nil {
		return err
	}
	defer c.Close()

	t.Logger.Debugf("Attached to proxy")

	done := make(chan struct{})

	go func() {
		defer close(done)
		t.serve(ctx, c)
	}()

	for {
		select {
		case <-done:
			return nil
		case <-interrupt:
			t.Logger.Debugf("Interrupted")
			err := c.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
			if err != nil {
				t.Logger.Errorf("write close: %s", err)
				return nil
			}
			select {
			case <-done:
			case <-time.After(time.Second):
			}
			return nil
		}
	}
}

func (t *Launcher) upLayer2(ctx context.Context) error {
	g, ctx := errgroup.WithContext(ctx)

	g.Go(func() error {
		return t.upLnd(ctx, "lndbtc")
	})

	g.Go(func() error {
		return t.upLnd(ctx, "lndltc")
	})

	g.Go(func() error {
		return t.upConnext(ctx)
	})

	if err := g.Wait(); err != nil {
		return err
	}

	return nil
}
