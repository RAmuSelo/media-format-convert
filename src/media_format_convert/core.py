"""Core logic for media-format-convert.

This module knows how to:

* locate the ``ffmpeg`` binary on the system ``PATH``;
* discover input files in a folder by extension;
* build the ``ffmpeg`` command line for a given conversion;
* run those commands (or merely plan them, for ``--dry-run``).

``ffmpeg`` is invoked through :mod:`subprocess` and never at import time, so
importing this module has no external side effects.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

FFMPEG_BINARY = "ffmpeg"


class FfmpegNotFoundError(RuntimeError):
    """Raised when the ``ffmpeg`` executable cannot be located on ``PATH``."""


@dataclass(frozen=True)
class ConversionProfile:
    """Extra ``ffmpeg`` arguments to apply for a given source/target pair.

    The arguments are inserted between the input (``-i <file>``) and the
    output path, exactly where ffmpeg expects output-stream options.
    """

    name: str
    extra_args: Sequence[str] = field(default_factory=tuple)


# Sensible defaults distilled from the original conversion scripts.
#
# * mov -> mp4: H.264 video + AAC audio, ``preset fast`` and ``-crf 22`` for a
#   light file that keeps good quality.
# * oga/ogg -> mp3: stereo, 44.1 kHz, 192 kbit/s.
# * ogg/oga -> wav: straight PCM export (ffmpeg defaults are fine).
_DEFAULT_PROFILES = {
    ("mov", "mp4"): ConversionProfile(
        "mov->mp4 (H.264/AAC, light)",
        (
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
        ),
    ),
    ("oga", "mp3"): ConversionProfile(
        "oga->mp3 (stereo 44.1kHz 192k)",
        ("-c:a", "libmp3lame", "-b:a", "192k", "-ac", "2", "-ar", "44100"),
    ),
    ("ogg", "mp3"): ConversionProfile(
        "ogg->mp3 (stereo 44.1kHz 192k)",
        ("-c:a", "libmp3lame", "-b:a", "192k", "-ac", "2", "-ar", "44100"),
    ),
    ("ogg", "wav"): ConversionProfile("ogg->wav (PCM)", ()),
    ("oga", "wav"): ConversionProfile("oga->wav (PCM)", ()),
}


def normalize_ext(ext: str) -> str:
    """Return a lowercase extension with no leading dot.

    ``".MP4"`` and ``"mp4"`` both normalise to ``"mp4"``.
    """

    return ext.lower().lstrip(".")


def find_ffmpeg(binary: str = FFMPEG_BINARY) -> str:
    """Return the absolute path to the ``ffmpeg`` executable.

    Raises :class:`FfmpegNotFoundError` with an actionable message if the
    binary is not present on ``PATH``.
    """

    resolved = shutil.which(binary)
    if resolved is None:
        raise FfmpegNotFoundError(
            f"'{binary}' was not found on your PATH. "
            "media-format-convert relies on a system ffmpeg install.\n"
            "  macOS:         brew install ffmpeg\n"
            "  Debian/Ubuntu: sudo apt install ffmpeg\n"
            "  Windows:       https://ffmpeg.org/download.html"
        )
    return resolved


def get_profile(src_ext: str, dst_ext: str) -> ConversionProfile:
    """Return the :class:`ConversionProfile` for a source/target extension pair.

    Falls back to an empty profile (ffmpeg defaults) for pairs that have no
    explicit preset, so arbitrary conversions still work.
    """

    key = (normalize_ext(src_ext), normalize_ext(dst_ext))
    if key in _DEFAULT_PROFILES:
        return _DEFAULT_PROFILES[key]
    return ConversionProfile(f"{key[0]}->{key[1]} (ffmpeg defaults)", ())


def discover_files(folder: Path, src_ext: str) -> List[Path]:
    """Return the sorted list of files in ``folder`` matching ``src_ext``.

    Matching is case-insensitive and the search is non-recursive, mirroring
    the original scripts which only looked at the top level of a folder.
    """

    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Input folder does not exist: {folder}")

    target = normalize_ext(src_ext)
    matches = [
        entry
        for entry in folder.iterdir()
        if entry.is_file() and normalize_ext(entry.suffix) == target
    ]
    return sorted(matches)


def output_path_for(src: Path, dst_ext: str, out_dir: Path) -> Path:
    """Compute the output path for ``src`` in ``out_dir`` with ``dst_ext``."""

    return Path(out_dir) / f"{Path(src).stem}.{normalize_ext(dst_ext)}"


def build_ffmpeg_command(
    src: Path,
    dst: Path,
    profile: ConversionProfile,
    *,
    overwrite: bool = True,
    ffmpeg_path: str = FFMPEG_BINARY,
) -> List[str]:
    """Build the full ``ffmpeg`` argument vector for one conversion.

    The resulting command is structured as::

        ffmpeg [-y|-n] -i <src> <profile args...> <dst>
    """

    command: List[str] = [ffmpeg_path, "-y" if overwrite else "-n", "-i", str(src)]
    command.extend(profile.extra_args)
    command.append(str(dst))
    return command


@dataclass
class PlannedConversion:
    """A single conversion that has been planned but not necessarily run."""

    src: Path
    dst: Path
    command: List[str]


def plan_conversions(
    folder: Path,
    src_ext: str,
    dst_ext: str,
    out_dir: Path,
    *,
    overwrite: bool = True,
    ffmpeg_path: str = FFMPEG_BINARY,
) -> List[PlannedConversion]:
    """Discover inputs and build a plan of conversions without running them."""

    files = discover_files(folder, src_ext)
    profile = get_profile(src_ext, dst_ext)
    plan: List[PlannedConversion] = []
    for src in files:
        dst = output_path_for(src, dst_ext, out_dir)
        command = build_ffmpeg_command(
            src, dst, profile, overwrite=overwrite, ffmpeg_path=ffmpeg_path
        )
        plan.append(PlannedConversion(src=src, dst=dst, command=command))
    return plan


def run_conversions(
    plan: Iterable[PlannedConversion],
    out_dir: Path,
    *,
    runner=subprocess.run,
) -> List[PlannedConversion]:
    """Execute each planned conversion via ``runner`` (defaults to subprocess.run).

    ``out_dir`` is created if needed. The ``runner`` indirection keeps the
    function easy to test without a real ffmpeg.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    done: List[PlannedConversion] = []
    for item in plan:
        runner(item.command, check=True)
        done.append(item)
    return done


def ensure_distinct(src_ext: str, dst_ext: str) -> None:
    """Reject conversions where source and target extension are identical."""

    if normalize_ext(src_ext) == normalize_ext(dst_ext):
        raise ValueError(
            f"--from and --to are both '{normalize_ext(src_ext)}'; "
            "nothing to convert."
        )


def resolve_out_dir(folder: Path, dst_ext: str, out: Optional[str]) -> Path:
    """Return the output directory.

    If ``out`` is given it is used verbatim. Otherwise a sibling folder of the
    input is derived from its name and the target extension, e.g.
    ``recordings`` + ``mp3`` -> ``recordings_mp3``.
    """

    if out:
        return Path(out)
    folder = Path(folder)
    return folder.parent / f"{folder.name}_{normalize_ext(dst_ext)}"
