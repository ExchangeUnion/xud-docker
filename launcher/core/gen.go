package core

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

func (t *Launcher) exportDockerComposeYaml() (string, error) {
	var b strings.Builder
	b.WriteString("version: \"2.4\"\n")
	b.WriteString("services:\n")
	for _, name := range t.ServicesOrder {
		s := t.Services[name]
		if s.IsDisabled() {
			continue
		}

		//t.Logger.Debugf("[docker-compose] Generate service %s", name)

		b.WriteString(fmt.Sprintf("  %s:\n", name))
		b.WriteString(fmt.Sprintf("    image: %s\n", s.GetImage()))
		if s.GetHostname() != "" {
			b.WriteString(fmt.Sprintf("    hostname: %s\n", s.GetHostname()))
		}
		if len(s.GetCommand()) > 0 {
			b.WriteString("    command: >\n")
			for _, arg := range s.GetCommand() {
				b.WriteString(fmt.Sprintf("      %s\n", arg))
			}
		}
		if len(s.GetEnvironment()) > 0 {
			b.WriteString("    environment:\n")
			for k, v := range s.GetEnvironment() {
				if strings.Contains(v, "\n") {
					// multiline string
					b.WriteString("      - >\n")
					b.WriteString(fmt.Sprintf("        %s=\n", k))
					for _, line := range strings.Split(v, "\n") {
						b.WriteString(fmt.Sprintf("        %s\n", line))
					}
				} else {
					b.WriteString(fmt.Sprintf("      - %s=%s\n", k, v))
				}
			}
		}
		if len(s.GetVolumes()) > 0 {
			b.WriteString("    volumes:\n")
			for _, v := range s.GetVolumes() {
				b.WriteString(fmt.Sprintf("      - %s\n", v))
			}
		}
		if len(s.GetPorts()) > 0 {
			b.WriteString("    ports:\n")
			for _, p := range s.GetPorts() {
				b.WriteString(fmt.Sprintf("       - %s\n", p))
			}
		}
	}
	return b.String(), nil
}

func (t *Launcher) GenDockerComposeYaml() error {
	wd, err := os.Getwd()
	if err != nil {
		return err
	}
	defer os.Chdir(wd)
	if err := os.Chdir(t.NetworkDir); err != nil {
		return err
	}
	t.Logger.Debugf("Generate docker-compose.yml in %s", t.NetworkDir)
	f, err := os.Create("docker-compose.yml")
	if err != nil {
		return err
	}
	defer f.Close()
	content, err := t.exportDockerComposeYaml()
	if err != nil {
		return err
	}
	_, err = f.WriteString(content)
	if err != nil {
		return err
	}
	return nil
}

type ExportedConfig struct {
	Timestamp string          `json:"timestamp"`
	Network   string          `json:"network"`
	Services  []ServiceConfig `json:"services"`
}

type ServiceConfig struct {
	Name     string      `json:"name"`
	Disabled bool        `json:"disabled"`
	Rpc      interface{} `json:"rpc"`
	Mode     string      `json:"mode,omitempty"`
}

func (t *Launcher) exportConfigJson() (string, error) {
	cfg := ExportedConfig{
		Timestamp: "",
		Network:   string(t.Network),
		Services:  []ServiceConfig{},
	}

	for _, name := range t.ServicesOrder {
		if name == "proxy" {
			continue
		}
		s := t.Services[name]
		rpc, err := s.GetRpcParams()
		if err != nil {
			return "", err
		}
		cfg.Services = append(cfg.Services, ServiceConfig{
			Name:     name,
			Disabled: s.IsDisabled(),
			Mode:     s.GetMode(),
			Rpc:      rpc,
		})
	}
	j, err := json.MarshalIndent(&cfg, "", "  ")
	if err != nil {
		return "", err
	}
	return string(j), nil
}

func (t *Launcher) GenConfigJson() error {
	wd, err := os.Getwd()
	if err != nil {
		return err
	}
	defer os.Chdir(wd)
	if err := os.Chdir(t.DataDir); err != nil {
		return err
	}
	t.Logger.Debugf("Generate config.json in %s", t.DataDir)

	f, err := os.Create("config.json")
	if err != nil {
		return err
	}
	defer f.Close()
	content, err := t.exportConfigJson()
	if err != nil {
		return err
	}
	_, err = f.WriteString(content)
	if err != nil {
		return err
	}
	return nil
}

func (t *Launcher) Gen(ctx context.Context) error {
	if err := t.GenDockerComposeYaml(); err != nil {
		return err
	}
	if err := t.GenConfigJson(); err != nil {
		return err
	}
	return nil
}
