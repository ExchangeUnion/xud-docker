package service

import "errors"

var (
	ErrForbiddenService = errors.New("forbidden service")
	ErrInvalidService = errors.New("invalid service")
)

type ErrExec struct {
	Output   string
	ExitCode int
	Message  string
}

func (t ErrExec) Error() string {
	return t.Message
}
