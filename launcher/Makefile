PKG := github.com/ExchangeUnion/xud-docker/launcher

GO_BIN = ${GOPATH}/bin

GOBUILD := go build -v

VERSION := latest
COMMIT := $(shell git rev-parse HEAD)
ifeq ($(OS), Windows_NT)
	TIMESTAMP := $(shell powershell.exe scripts\get_timestamp.ps1)
else
	TIMESTAMP := $(shell date +%s)
endif

ifeq ($(GOOS), windows)
	OUTPUT := launcher.exe
else
	OUTPUT := launcher
endif


LDFLAGS := -ldflags "-w -s \
-X $(PKG)/build.Version=$(VERSION) \
-X $(PKG)/build.GitCommit=$(COMMIT) \
-X $(PKG)/build.Timestamp=$(TIMESTAMP)"

default: build

build:
	$(GOBUILD) $(LDFLAGS)

zip:
	zip --junk-paths launcher.zip $(OUTPUT)

clean:
	rm -f launcher
	rm -f launcher.zip

.PHONY: build
