# Simple build helpers for CLI, updater, and installer.

CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra
LDFLAGS ?=

# Windows cross-compile (MinGW-w64) settings
MINGW_PREFIX ?= x86_64-w64-mingw32
WIN_CC := $(MINGW_PREFIX)-gcc
WIN_CFLAGS ?= -O2 -Wall -Wextra -static
WIN_LDFLAGS ?=
WIN_DIST_DIR := dist/windows

LINUX_BINARIES := cli_calculator auto_updater installer_gui
WINDOWS_BINARIES := $(WIN_DIST_DIR)/cli_calculator.exe $(WIN_DIST_DIR)/auto_updater.exe $(WIN_DIST_DIR)/installer_gui.exe

.PHONY: all windows clean dist

all: $(LINUX_BINARIES)

cli_calculator: cli_calculator.c version.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ cli_calculator.c

auto_updater: auto_updater.c gui_dialogs.c gui_dialogs.h version.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ auto_updater.c gui_dialogs.c

installer_gui: installer_gui.c gui_dialogs.c gui_dialogs.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ installer_gui.c gui_dialogs.c

$(WIN_DIST_DIR):
	mkdir -p $(WIN_DIST_DIR)/rangeTables

$(WIN_DIST_DIR)/cli_calculator.exe: cli_calculator.c version.h | $(WIN_DIST_DIR)
	$(WIN_CC) $(WIN_CFLAGS) $(WIN_LDFLAGS) -o $@ cli_calculator.c

$(WIN_DIST_DIR)/auto_updater.exe: auto_updater.c gui_dialogs.c gui_dialogs.h version.h | $(WIN_DIST_DIR)
	$(WIN_CC) $(WIN_CFLAGS) $(WIN_LDFLAGS) -o $@ auto_updater.c gui_dialogs.c

$(WIN_DIST_DIR)/installer_gui.exe: installer_gui.c gui_dialogs.c gui_dialogs.h | $(WIN_DIST_DIR)
	$(WIN_CC) $(WIN_CFLAGS) $(WIN_LDFLAGS) -o $@ installer_gui.c gui_dialogs.c

windows: $(WINDOWS_BINARIES)
	cp -a rangeTables/* $(WIN_DIST_DIR)/rangeTables 2>/dev/null || true

# Archive Windows deliverables into a zip ready for GitHub Releases.
zip-windows: windows
	cd $(WIN_DIST_DIR) && zip -r artillery_calculator-windows.zip cli_calculator.exe auto_updater.exe installer_gui.exe rangeTables

clean:
	rm -f $(LINUX_BINARIES) $(WINDOWS_BINARIES)
	rm -rf dist
