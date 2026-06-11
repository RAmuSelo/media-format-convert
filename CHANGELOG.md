# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CONTRIBUTING.md
- CHANGELOG.md
- A more specific README (Why + Roadmap)

### Planned

- **Recursive** folder scanning (currently top-level only).
- Parallel conversion with a `--workers` flag for large folders.
- Per-pair quality flags (e.g. configurable CRF / bitrate).

## [0.1.0] - 2026-06-08

### Added

- Batch-convert media files in a folder by source and target extension, wrapping the system `ffmpeg` binary via `subprocess`.
- Built-in presets for common conversions: `mov` → `mp4` (H.264 + AAC), `oga`/`ogg` → `mp3` (192 kbit/s), and `ogg`/`oga` → `wav` (PCM); any other extension pair falls back to ffmpeg defaults.
- `--out` to choose the output directory (defaults to a sibling `<folder>_<to>` folder).
- `--dry-run` to print the planned ffmpeg commands without converting.
- `--no-overwrite` to keep existing outputs (passes `-n` to ffmpeg).
- Clear error when ffmpeg is missing from `PATH` (a warning in `--dry-run`).
- No runtime pip dependencies (ffmpeg is a system binary).
- Stdlib unittest test suite.
- GitHub Actions CI.
- MIT license.

[Unreleased]: https://github.com/RAmuSelo/media-format-convert/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/RAmuSelo/media-format-convert/releases/tag/v0.1.0
