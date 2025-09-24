# Building and Packaging Kumanui Resources

This guide is for developers and contributors who want to build generated resources and create distributable packages.

## Prerequisites

- Python 3.10+ available as `python3` (or a local `venv` in `venv/`).
- Install dependencies with `python3 -m pip install -r requirements.txt`.
  - Includes PyYAML for token parsing.
  - Includes PyObjC for macOS Terminal profile generation (macOS only).

## Make Targets

- `make help`: Lists available targets.
- `make all`: Builds CSS, macOS Terminal profile, and README color sections.
- `make css`: Generates `dist/css/kumanui.css` from `tokens/colors.yaml`.
- `make macos-terminal`: Generates `dist/macos-terminal/Kumanui.terminal`.
- `make readme`: Regenerates README color sections from tokens.
- `make readme-check`: Verifies README is in sync with tokens.
- `make contrast`: Prints WCAG contrast report for key colors.
- `make demo`: Runs a small terminal color demo.
- `make clean`: Removes generated files in `dist/` (safe targets only).
- `make package`: Creates a ZIP with tokens and any built assets.
- `make release`: Runs full build, then creates the ZIP.
- `make version`: Prints the current version.

## Versioning

- Source of truth is the file `VERSION` (first line only).
- The package filename includes the version, e.g., `dist/kumanui-<version>.zip`.
- Running `make readme` (or `make all`) refreshes the README download link with the version from `VERSION`.

## Packaging Details

- Output ZIP: `dist/kumanui-<version>.zip`.
- Contents: essential docs (`README.md`, `build.md`, `LICENSE`), resources referenced by those docs, `tokens/`, and generated platform assets when present (`css/`, `macos-terminal/`).
- Customize filename: `make PACKAGE_NAME=kumanui-YYYY-MM-DD.zip package`.

## Configuration

- macOS Terminal font: set `FONT_NAME` and `FONT_SIZE` via env or make args.
  - Example: `make macos-terminal FONT_NAME="SF Mono" FONT_SIZE=12`

