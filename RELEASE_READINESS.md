# Release Readiness — media-format-convert

Status snapshot for the `0.1.0` candidate.

## Summary

`media-format-convert` is a small CLI that wraps the system `ffmpeg` binary to
batch-convert media files in a folder (mov->mp4, oga->mp3, ogg->wav, and
arbitrary pairs via ffmpeg defaults). It has **no runtime pip dependencies**;
ffmpeg is a system requirement invoked through `subprocess`.

## Checklist

| Item | Status | Notes |
|------|--------|-------|
| Package layout (`src/`) | Done | `src/media_format_convert/{__init__,cli,core}.py` |
| Console entry point | Done | `media-format-convert = media_format_convert.cli:main` |
| Argparse CLI (no `input()`) | Done | folder, `--from`, `--to`, `--out`, `--dry-run`, `--no-overwrite` |
| ffmpeg via subprocess, not at import | Done | located with `shutil.which`; commands run in `core.run_conversions` |
| Missing-ffmpeg handling | Done | hard error on real run (exit 2), warning in `--dry-run` |
| Dry-run mode | Done | prints planned, shell-quoted ffmpeg commands; runs nothing |
| File discovery by extension | Done | case-insensitive, non-recursive |
| README (pitch/install/usage) | Done | documents ffmpeg-on-PATH requirement |
| LICENSE (MIT) | Done | "The media-format-convert authors", 2026 |
| `pyproject.toml` | Done | MIT, `requires-python >=3.9`, no deps, src layout |
| `.gitignore` | Done | Python + build + media artifacts |
| Tests (stdlib unittest) | Done | `tests/test_core.py`, `tests/test_cli.py` |
| No network in tests | Done | subprocess monkeypatched; no sockets |
| No real ffmpeg in tests | Done | `shutil.which` patched; runner faked |
| No personal paths / secrets | Done | verified via grep (see below) |

## Test strategy

Tests use only the standard library (`unittest`, `unittest.mock`, `tempfile`):

* **Command construction** — exact ffmpeg argument vectors per conversion
  (mov->mp4 H.264/CRF/AAC; oga->mp3 stereo/44.1k/192k; ogg->wav PCM).
* **Dry-run** — planned commands are printed and `subprocess.run` is never
  called.
* **Missing ffmpeg** — real run exits with code 2; dry-run only warns.
* **File discovery** — case-insensitive, non-recursive, extension filtering.
* **End-to-end CLI** — one subprocess call per matching file, failure handling,
  custom output dir, identical `--from`/`--to` rejection, missing folder.

Run them with:

```sh
python3 -m unittest discover -s tests
```

## Known limitations / future work

* Discovery is non-recursive by design (mirrors the original scripts). A
  `--recursive` flag could be added later.
* Conversion presets are opinionated defaults; a `--ffmpeg-arg` passthrough
  could expose finer control.
* No progress bar / parallelism; conversions run sequentially.

## Verdict

Ready for an initial open-source `0.1.0` release pending a real-world smoke test
on a machine with ffmpeg installed (the automated suite intentionally does not
invoke the real binary).
