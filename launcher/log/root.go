package log

import (
	"github.com/sirupsen/logrus"
	"io"
)

var (
	rootLogger = &logrus.Logger{
		Level:     logrus.DebugLevel,
		Formatter: &Formatter{},
	}
)

func SetOutput(output io.Writer) {
	rootLogger.SetOutput(output)
}

func NewLogger(name string) *logrus.Entry {
	return logrus.NewEntry(rootLogger).WithField("name", name)
}
