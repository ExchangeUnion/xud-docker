package logging

import (
	"bytes"
	"fmt"
	"github.com/sirupsen/logrus"
	"strings"
)

type Formatter struct {
}

func (f *Formatter) Format(entry *logrus.Entry) ([]byte, error) {
	data := make(logrus.Fields)
	for k, v := range entry.Data {
		data[k] = v
	}

	var b *bytes.Buffer
	if entry.Buffer != nil {
		b = entry.Buffer
	} else {
		b = &bytes.Buffer{}
	}

	name := data["name"]
	if name == nil {
		name = ""
	}

	b.WriteString(fmt.Sprintf("%s [%-5s] %-24s: %s\n",
		entry.Time.Format("2006-01-02 15:04:05.000"),
		strings.ToUpper(entry.Level.String()),
		name,
		entry.Message,
	))

	return b.Bytes(), nil
}
