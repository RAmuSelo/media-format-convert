# Contributing to media-format-convert

Thanks for your interest in improving `media-format-convert`. It is a small, dependency-free wrapper around ffmpeg, and contributions that keep it lean are very welcome.

## Ground rules

- **No secrets in the repo.** Never commit API keys, tokens, credentials, or absolute paths from your machine.
- **ffmpeg is a system dependency.** The user installs ffmpeg themselves (e.g. `brew install ffmpeg`, `apt install ffmpeg`). The tool must **not** bundle, download, or auto-install ffmpeg or anything else — it only calls the binary already on `PATH`.
- **Stay dependency-free.** There are no runtime pip dependencies; please keep it that way. If a change seems to need one, open an issue to discuss first.

## Development setup

```bash
pip install -e .
python -m unittest discover -s tests
```

## Making a change

- Keep pull requests small and focused on a single change.
- Add or update unittest tests to cover your change.
- Keep CI green (the test suite runs on Python 3.9, 3.11, and 3.12).
- No new runtime dependencies without discussion first.

## Reporting bugs

Open an issue and include:

- What you ran (the exact command and flags).
- What you expected to happen, and what actually happened.
- Your OS, Python version, and `ffmpeg -version` output.
- The source/target extensions involved, if relevant.

Never paste secrets or absolute machine paths into an issue.

## Scope

- **In scope:** batch-converting media files in a folder via ffmpeg, with sensible named presets for common conversions.
- **Out of scope:** shipping or installing ffmpeg itself, and editing/filtering media beyond a straightforward container/codec conversion.
