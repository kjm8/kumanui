# Makefile for Kumanui

# Use local venv Python if present; else fallback to system python3
PYTHON ?= python3
VENV_BIN := venv/bin/python
ifeq ($(wildcard $(VENV_BIN)), $(VENV_BIN))
  PYTHON := $(VENV_BIN)
endif

# Paths
TOKENS := tokens/colors.yaml
CSS_OUT := dist/css/kumanui.css
TERMINAL_OUT := dist/macos-terminal/Kumanui.terminal
DOCS := README.md build.md LICENSE

# Version
VERSION_FILE ?= VERSION
VERSION := $(shell test -f $(VERSION_FILE) && sed -n '1p' $(VERSION_FILE) | tr -d ' \n' || echo 0.0.0)

# Font configuration for macOS Terminal profile generation
FONT_NAME ?= SF Mono Terminal
FONT_SIZE ?= 12

# Scripts
GEN_CSS := _assets/scripts/generate_css.py
GEN_README := _assets/scripts/generate_readme.py
GEN_TERMINAL := _assets/scripts/generate_macos_terminal.py
CHECK_CONTRAST := _assets/scripts/check_contrast.py

.PHONY: help all css macos-terminal readme readme-check contrast demo clean package release version

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "\033[33m%-15s\033[0m %s\n", $$1, $$2}'

all: css macos-terminal readme ## Build CSS, Terminal profile, and README sections

css: $(CSS_OUT) ## Generate CSS variables from tokens

$(CSS_OUT): $(TOKENS) $(GEN_CSS)
	@echo "[build] Generating CSS -> $(CSS_OUT)"
	$(PYTHON) $(GEN_CSS)

macos-terminal: $(TERMINAL_OUT) ## Generate macOS Terminal profile

$(TERMINAL_OUT): $(TOKENS) $(GEN_TERMINAL)
	@echo "[build] Generating macOS Terminal profile -> $(TERMINAL_OUT)"
	$(PYTHON) $(GEN_TERMINAL) $(TERMINAL_OUT) --font-name "$(FONT_NAME)" --font-size $(FONT_SIZE)

readme: $(GEN_README) $(TOKENS) ## Update README color sections from tokens
	@echo "[docs] Regenerating README color sections"
	$(PYTHON) $(GEN_README)

readme-check: $(GEN_README) $(TOKENS) ## Check README is in sync with tokens (CI use)
	$(PYTHON) $(GEN_README) --check

contrast: $(CHECK_CONTRAST) $(TOKENS) ## Print WCAG contrast report for key colors
	$(PYTHON) $(CHECK_CONTRAST)

demo: ## Run terminal color demo
	$(PYTHON) _assets/scripts/terminal_demo.py

clean: ## Remove generated artifacts in dist (safe targets only)
	@echo "[clean] Removing generated files"
	rm -f $(CSS_OUT) $(TERMINAL_OUT)

# Packaging
# Package filename includes version from $(VERSION_FILE)
PACKAGE_NAME ?= kumanui-$(VERSION).zip
PACKAGE_OUT := dist/$(PACKAGE_NAME)
PKG_STAGING := dist/_package

package: ## Create distributable ZIP with tokens and built resources
	@echo "[package] Preparing package contents"
	@rm -rf $(PKG_STAGING) $(PACKAGE_OUT)
	@mkdir -p $(PKG_STAGING)
	@# Include docs
	@cp $(DOCS) $(PKG_STAGING)/
	@# Include assets referenced by docs
	@echo "[package] Collecting doc assets"
	@{ grep -E -h -o '_assets/[^"\) ]+' $(DOCS) || true; } | sort -u | while read asset; do \
	        if [ -f "$$asset" ]; then \
	                mkdir -p "$(PKG_STAGING)/$$(dirname $$asset)"; \
	                cp "$$asset" "$(PKG_STAGING)/$$asset"; \
	        fi; \
	done
	@# Include tokens
	@cp -R tokens $(PKG_STAGING)/tokens
	@# Include generated resources if present
	@if [ -d dist/css ]; then cp -R dist/css $(PKG_STAGING)/css; fi
	@if [ -d dist/macos-terminal ]; then cp -R dist/macos-terminal $(PKG_STAGING)/macos-terminal; fi
	@echo "[package] Zipping -> $(PACKAGE_OUT)"
	@(cd $(PKG_STAGING) && zip -rq ../$(PACKAGE_NAME) .)
	@rm -rf $(PKG_STAGING)
	@echo "[package] Done: $(PACKAGE_OUT)"

release: all package ## Build all resources and create ZIP

version: ## Print the current version (from VERSION file)
	@echo $(VERSION)
