"""Command-line interface for media-format-convert.

Usage example::

    media-format-convert ./recordings --from oga --to mp3
    media-format-convert ./clips --from mov --to mp4 --out ./encoded --dry-run

The CLI never prompts interactively: every input comes from arguments.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import core


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="media-format-convert",
        description=(
            "Batch-convert media files in a folder using ffmpeg "
            "(e.g. mov->mp4, oga->mp3, ogg->wav)."
        ),
    )
    parser.add_argument(
        "folder",
        help="Folder containing the files to convert (searched non-recursively).",
    )
    parser.add_argument(
        "--from",
        dest="from_ext",
        required=True,
        metavar="EXT",
        help="Source file extension to match, e.g. 'mov', 'oga', 'ogg'.",
    )
    parser.add_argument(
        "--to",
        dest="to_ext",
        required=True,
        metavar="EXT",
        help="Target file extension, e.g. 'mp4', 'mp3', 'wav'.",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default=None,
        metavar="DIR",
        help=(
            "Output directory. Defaults to a sibling folder named "
            "'<folder>_<to>' next to the input folder."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the ffmpeg commands that would run, without executing them.",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Pass -n to ffmpeg so existing output files are not overwritten.",
    )
    return parser


def _format_command(command: Sequence[str]) -> str:
    """Render an argument vector as a copy-pasteable shell command."""

    return " ".join(shlex.quote(part) for part in command)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    folder = Path(args.folder)

    try:
        core.ensure_distinct(args.from_ext, args.to_ext)
    except ValueError as exc:
        parser.error(str(exc))

    # Locate ffmpeg up front so we fail fast with a clear message. In dry-run
    # mode a missing ffmpeg is only a warning: the planned commands are still
    # useful to inspect.
    try:
        ffmpeg_path = core.find_ffmpeg()
    except core.FfmpegNotFoundError as exc:
        if not args.dry_run:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"warning: {exc}", file=sys.stderr)
        ffmpeg_path = core.FFMPEG_BINARY

    out_dir = core.resolve_out_dir(folder, args.to_ext, args.out)

    try:
        plan = core.plan_conversions(
            folder,
            args.from_ext,
            args.to_ext,
            out_dir,
            overwrite=not args.no_overwrite,
            ffmpeg_path=ffmpeg_path,
        )
    except (NotADirectoryError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not plan:
        print(
            f"No '.{core.normalize_ext(args.from_ext)}' files found in {folder}."
        )
        return 0

    print(
        f"Found {len(plan)} file(s) to convert "
        f"({core.normalize_ext(args.from_ext)} -> {core.normalize_ext(args.to_ext)})."
    )
    print(f"Output directory: {out_dir}")

    if args.dry_run:
        print("\n[dry-run] Planned ffmpeg commands:")
        for item in plan:
            print(f"  {_format_command(item.command)}")
        return 0

    failures: List[str] = []
    for index, item in enumerate(plan, start=1):
        print(f"[{index}/{len(plan)}] {item.src.name} -> {item.dst.name}")
        try:
            core.run_conversions([item], out_dir, runner=subprocess.run)
        except subprocess.CalledProcessError as exc:
            print(f"  failed (ffmpeg exit code {exc.returncode})", file=sys.stderr)
            failures.append(item.src.name)

    converted = len(plan) - len(failures)
    print(f"\nDone: {converted} succeeded, {len(failures)} failed.")
    if failures:
        print("Failed files: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
