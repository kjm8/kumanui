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

# Font configuration for macOS Terminal profile generation
FONT_NAME ?= SF Mono Terminal
FONT_SIZE ?= 12

# Scripts
GEN_CSS := _assets/scripts/generate_css.py
GEN_README := _assets/scripts/generate_readme.py
GEN_TERMINAL := _assets/scripts/generate_macos_terminal.py
CHECK_CONTRAST := _assets/scripts/check_contrast.py

.PHONY: help all css macos-terminal readme readme-check contrast demo clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

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
