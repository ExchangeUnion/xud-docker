package core

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ExchangeUnion/xud-docker/launcher/service/proxy"
	"github.com/gorilla/websocket"
	"golang.org/x/sync/errgroup"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"time"
)

const (
	DefaultWalletPassword = "OpenDEX!Rocks"
)

func (t *Launcher) Setup(ctx context.Context) error {
	t.Logger.Debugf("Setup %s (%s)", t.Network, t.NetworkDir)

	wd, err := os.Getwd()
	if err != nil {
		return err
	}
	defer os.Chdir(wd)

	if err := os.Chdir(t.NetworkDir); err != nil {
		return err
	}

	if err := t.Gen(ctx); err != nil {
		return err
	}

	t.Logger.Debugf("Start proxy")
	if err := t.upProxy(ctx); err != nil {
		return err
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
		return err
	}

	t.Logger.Debugf("Start xud")
	if err := t.upXud(ctx); err != nil {
		return err
	}

	t.Logger.Debugf("Start boltz")
	if err := t.upBoltz(ctx); err != nil {
		return err
	}

	fmt.Println("Attached to proxy. Press Ctrl-C to detach from it.")
	wg.Wait()

	return nil
}

func (t *Launcher) upProxy(ctx context.Context) error {
	s, err := t.GetService("proxy")
	if err != nil {
		return fmt.Errorf("failed to start proxy: %s", err)
	}
	if err := s.Up(ctx); err != nil {
		return err
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("%s: %s\n", s.GetName(), status)
		if status == "Ready" {
			break
		}
		if status == "Container missing" || status == "Container exited" {
			return fmt.Errorf("failed to start proxy: %s", status)
		}
		select {
		case <-ctx.Done(): // context cancelled
			return errors.New("interrupted")
		case <-time.After(3 * time.Second): // retry
		}
	}
	return nil
}

func (t *Launcher) upLnd(ctx context.Context, name string) error {
	s, err := t.GetService(name)
	if err != nil {
		return err
	}
	if err := s.Up(ctx); err != nil {
		return err
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("%s: %s\n", name, status)
		if status == "Ready" {
			break
		}
		if strings.HasPrefix(status, "Syncing 100.00%") {
			break
		}
		if strings.HasPrefix(status, "Syncing 99.99%") {
			break
		}
		if strings.HasPrefix(status, "Wallet locked") {
			break
		}
		if status == "Container missing" || status == "Container exited" {
			return fmt.Errorf("failed to start proxy: %s", status)
		}
		select {
		case <-ctx.Done(): // context cancelled
			return errors.New("interrupted")
		case <-time.After(3 * time.Second): // retry
		}
	}
	return nil
}

func (t *Launcher) upConnext(ctx context.Context) error {
	s, err := t.GetService("connext")
	if err != nil {
		return err
	}
	if err := s.Up(ctx); err != nil {
		return err
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("%s: %s\n", s.GetName(), status)
		if status == "Ready" {
			break
		}
		select {
		case <-ctx.Done(): // context cancelled
			return errors.New("interrupted")
		case <-time.After(3 * time.Second): // retry
		}
	}
	return nil
}

func (t *Launcher) createWallets(ctx context.Context, password string) error {
	s, err := t.GetService("proxy")
	if err != nil {
		return err
	}
	rpc, err := s.GetRpcParams()
	if err != nil {
		return err
	}
	createUrl := fmt.Sprintf("%s/api/v1/xud/create", rpc.(proxy.RpcParams).ToUri())
	payload := map[string]interface{}{
		"password": password,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, "POST", createUrl, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var body map[string]interface{}
		err := json.NewDecoder(resp.Body).Decode(&body)
		if err != nil {
			return err
		}
		return errors.New(body["message"].(string))
	}

	return nil
}

func (t *Launcher) unlockWallets(ctx context.Context, password string) error {
	s, err := t.GetService("proxy")
	if err != nil {
		return err
	}
	rpc, err := s.GetRpcParams()
	if err != nil {
		return err
	}
	createUrl := fmt.Sprintf("%s/api/v1/xud/unlock", rpc.(proxy.RpcParams).ToUri())
	payload := map[string]interface{}{
		"password": password,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, "POST", createUrl, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var body map[string]interface{}
		err := json.NewDecoder(resp.Body).Decode(&body)
		if err != nil {
			return err
		}
		return errors.New(body["message"].(string))
	}

	return nil
}

func (t *Launcher) upXud(ctx context.Context) error {
	s, err := t.GetService("xud")
	if err != nil {
		return err
	}
	if err := s.Up(ctx); err != nil {
		return err
	}
	for {
		status, err := s.GetStatus(ctx)
		if err != nil {
			return err
		}
		fmt.Printf("%s: %s\n", s.GetName(), status)
		if status == "Ready" {
			break
		}
		if status == "Waiting for channels" {
			break
		}
		if strings.HasPrefix(status, "Wallet missing") {
			if err := t.createWallets(ctx, DefaultWalletPassword); err != nil {
				return err
			}
			break
		}
		if strings.HasPrefix(status, "Wallet locked") {
			if err := t.unlockWallets(ctx, DefaultWalletPassword); err != nil {
				return err
			}
			break
		}
		select {
		case <-ctx.Done(): // context cancelled
			return errors.New("interrupted")
		case <-time.After(3 * time.Second): // retry
		}
	}
	return nil
}

func (t *Launcher) upBoltz(ctx context.Context) error {
	s, err := t.GetService("boltz")
	if err != nil {
		return err
	}
	if err := s.Up(ctx); err != nil {
		return err
	}
	//for {
	//	status, err := s.GetStatus(ctx)
	//	if err != nil {
	//		return err
	//	}
	//	fmt.Printf("%s: %s\n", s.GetName(), status)
	//	if status == "Ready" {
	//		break
	//	}
	//	select {
	//	case <-ctx.Done(): // context cancelled
	//		return errors.New("interrupted")
	//	case <-time.After(3 * time.Second): // retry
	//	}
	//}
	return nil
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
	return Info{
		Wallets: WalletsInfo{
			DefaultPassword: true,
			MnemonicShown:   false,
		},
		Backup: BackupInfo{
			Location:        t.BackupDir,
			DefaultLocation: true,
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

	u := url.URL{Scheme: "wss", Host: "127.0.0.1:8889", Path: "/launcher"}
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
