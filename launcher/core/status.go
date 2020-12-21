package core

import "context"

func (t *Launcher) Status(ctx context.Context, name string) (string, error) {
	s, err := t.GetService(name)
	if err != nil {
		return "", err
	}
	return s.GetStatus(ctx)
}
