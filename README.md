# media-format-convert

[![Tests](https://github.com/RAmuSelo/media-format-convert/actions/workflows/tests.yml/badge.svg)](https://github.com/RAmuSelo/media-format-convert/actions/workflows/tests.yml)

A small, dependency-free command-line tool that wraps [ffmpeg](https://ffmpeg.org/)
to **batch-convert media files in a folder**. Point it at a directory, tell it
the source and target extension, and it converts every matching file.

Common conversions ship with sensible presets:

| From  | To    | Preset                                                |
|-------|-------|-------------------------------------------------------|
| `mov` | `mp4` | H.264 (`libx264`) video + AAC audio, `preset fast`, `-crf 22` (light file, good quality) |
| `oga` | `mp3` | stereo, 44.1 kHz, 192 kbit/s (`libmp3lame`)           |
| `ogg` | `mp3` | stereo, 44.1 kHz, 192 kbit/s (`libmp3lame`)           |
| `ogg` | `wav` | PCM (ffmpeg defaults)                                  |
| `oga` | `wav` | PCM (ffmpeg defaults)                                  |

Any other extension pair also works — it falls back to ffmpeg's defaults for
that container/codec.

## Requirements

* **Python 3.9+**
* **ffmpeg** available on your `PATH`. This tool does **not** bundle or install
  ffmpeg; it calls the system binary via `subprocess`.

Install ffmpeg with your platform's package manager:

```sh
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Windows: download from https://ffmpeg.org/download.html and add to PATH
```

## Install

From the project root:

```sh
pip install .
```

Or for development (editable install):

```sh
pip install -e .
```

This exposes the `media-format-convert` command.

## Usage

```text
media-format-convert FOLDER --from EXT --to EXT [--out DIR] [--dry-run] [--no-overwrite]
```

Convert every `.oga` file in a folder to stereo MP3:

```sh
media-format-convert ./recordings --from oga --to mp3
```

Convert `.mov` clips to light `.mp4`, writing into a chosen folder:

```sh
media-format-convert ./clips --from mov --to mp4 --out ./encoded
```

Preview the exact ffmpeg commands without running anything:

```sh
media-format-convert ./clips --from mov --to mp4 --dry-run
```

Don't overwrite files that already exist in the output directory:

```sh
media-format-convert ./recordings --from ogg --to wav --no-overwrite
```

### Options

| Option           | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `FOLDER`         | Folder to scan for input files (non-recursive).                             |
| `--from EXT`     | Source extension to match (case-insensitive, e.g. `mov`).                   |
| `--to EXT`       | Target extension (e.g. `mp4`).                                              |
| `--out DIR`      | Output directory. Defaults to a sibling folder `<folder>_<to>`.            |
| `--dry-run`      | Print the planned ffmpeg commands and exit without converting.             |
| `--no-overwrite` | Pass `-n` to ffmpeg so existing outputs are kept.                          |

### Output location

If you don't pass `--out`, results are written to a sibling folder named after
the input folder plus the target extension. For example, converting the folder
`recordings` to `mp3` produces a `recordings_mp3` folder next to it. Output file
names keep the original stem with the new extension (`note.oga` -> `note.mp3`).

## How it works

The tool discovers matching files, builds an ffmpeg argument vector per file
(`ffmpeg -y -i <src> <preset args...> <dst>`), then runs each one through
`subprocess`. ffmpeg is located with `shutil.which`; if it's missing you get a
clear error (or a warning in `--dry-run`, since the planned commands are still
worth inspecting).

## License

MIT. See [LICENSE](LICENSE).
