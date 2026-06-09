"""Unit tests for media_format_convert.cli.

No network, no real ffmpeg: subprocess.run is monkeypatched and ffmpeg
discovery is patched to a fake path (or to "missing").
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from media_format_convert import cli, core  # noqa: E402


class _Tmp:
    """Helper context creating a folder with given files."""

    def __init__(self, files):
        self._files = files
        self._tmp = tempfile.TemporaryDirectory()

    def __enter__(self):
        root = Path(self._tmp.name)
        for name in self._files:
            (root / name).write_bytes(b"data")
        return root

    def __exit__(self, *exc):
        self._tmp.cleanup()


class DryRunTests(unittest.TestCase):
    def test_dry_run_prints_planned_commands_and_runs_nothing(self):
        run_mock = mock.Mock()
        with _Tmp(["clip.mov", "other.mov"]) as folder:
            out = io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value="/usr/bin/ffmpeg"
            ), mock.patch.object(cli.subprocess, "run", run_mock), redirect_stdout(out):
                rc = cli.main(
                    [str(folder), "--from", "mov", "--to", "mp4", "--dry-run"]
                )

        self.assertEqual(rc, 0)
        run_mock.assert_not_called()
        text = out.getvalue()
        self.assertIn("[dry-run]", text)
        self.assertIn("ffmpeg", text)
        self.assertIn("libx264", text)
        # One command line per file.
        self.assertEqual(text.count("-crf"), 2)

    def test_dry_run_without_ffmpeg_warns_but_succeeds(self):
        with _Tmp(["a.ogg"]) as folder:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value=None
            ), mock.patch.object(cli.subprocess, "run") as run_mock, redirect_stdout(
                out
            ), redirect_stderr(
                err
            ):
                rc = cli.main(
                    [str(folder), "--from", "ogg", "--to", "wav", "--dry-run"]
                )

        self.assertEqual(rc, 0)
        run_mock.assert_not_called()
        self.assertIn("warning", err.getvalue().lower())
        self.assertIn("[dry-run]", out.getvalue())


class MissingFfmpegTests(unittest.TestCase):
    def test_real_run_without_ffmpeg_errors_with_code_2(self):
        with _Tmp(["a.ogg"]) as folder:
            err = io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value=None
            ), mock.patch.object(cli.subprocess, "run") as run_mock, redirect_stdout(
                io.StringIO()
            ), redirect_stderr(
                err
            ):
                rc = cli.main([str(folder), "--from", "ogg", "--to", "wav"])

        self.assertEqual(rc, 2)
        run_mock.assert_not_called()
        self.assertIn("error", err.getvalue().lower())
        self.assertIn("ffmpeg", err.getvalue())


class RealRunTests(unittest.TestCase):
    def test_each_file_triggers_one_subprocess_call(self):
        captured = []

        def fake_run(command, check):
            captured.append(command)

            class _R:
                returncode = 0

            return _R()

        with _Tmp(["v1.oga", "v2.oga", "skip.txt"]) as folder:
            out = io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value="/usr/bin/ffmpeg"
            ), mock.patch.object(
                cli.subprocess, "run", side_effect=fake_run
            ), redirect_stdout(
                out
            ):
                rc = cli.main([str(folder), "--from", "oga", "--to", "mp3"])

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 2)  # only the two .oga files
        for command in captured:
            self.assertEqual(command[0], "/usr/bin/ffmpeg")
            self.assertIn("libmp3lame", command)
        self.assertIn("Done: 2 succeeded, 0 failed", out.getvalue())

    def test_ffmpeg_failure_reports_and_returns_1(self):
        import subprocess as _sp

        def fake_run(command, check):
            raise _sp.CalledProcessError(returncode=1, cmd=command)

        with _Tmp(["bad.mov"]) as folder:
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value="/usr/bin/ffmpeg"
            ), mock.patch.object(
                cli.subprocess, "run", side_effect=fake_run
            ), redirect_stdout(
                out
            ), redirect_stderr(
                err
            ):
                rc = cli.main([str(folder), "--from", "mov", "--to", "mp4"])

        self.assertEqual(rc, 1)
        self.assertIn("failed", err.getvalue().lower())


class DiscoveryAndValidationTests(unittest.TestCase):
    def test_no_matching_files_returns_0_with_message(self):
        with _Tmp(["readme.txt"]) as folder:
            out = io.StringIO()
            with mock.patch.object(
                core.shutil, "which", return_value="/usr/bin/ffmpeg"
            ), mock.patch.object(cli.subprocess, "run") as run_mock, redirect_stdout(
                out
            ):
                rc = cli.main([str(folder), "--from", "mov", "--to", "mp4"])

        self.assertEqual(rc, 0)
        run_mock.assert_not_called()
        self.assertIn("No '.mov' files found", out.getvalue())

    def test_custom_out_dir_is_used(self):
        captured = []

        def fake_run(command, check):
            captured.append(command)

            class _R:
                returncode = 0

            return _R()

        with _Tmp(["a.ogg"]) as folder:
            with tempfile.TemporaryDirectory() as out_root:
                out_dir = Path(out_root) / "encoded"
                with mock.patch.object(
                    core.shutil, "which", return_value="/usr/bin/ffmpeg"
                ), mock.patch.object(
                    cli.subprocess, "run", side_effect=fake_run
                ), redirect_stdout(
                    io.StringIO()
                ):
                    rc = cli.main(
                        [
                            str(folder),
                            "--from",
                            "ogg",
                            "--to",
                            "wav",
                            "--out",
                            str(out_dir),
                        ]
                    )

                self.assertEqual(rc, 0)
                self.assertTrue(out_dir.exists())
                self.assertTrue(captured[0][-1].startswith(str(out_dir)))

    def test_same_from_and_to_is_rejected(self):
        with _Tmp(["a.mp3"]) as folder:
            err = io.StringIO()
            # argparse calls SystemExit(2) via parser.error.
            with mock.patch.object(
                core.shutil, "which", return_value="/usr/bin/ffmpeg"
            ), redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main([str(folder), "--from", "mp3", "--to", "mp3"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("nothing to convert", err.getvalue())

    def test_missing_input_folder_returns_2(self):
        err = io.StringIO()
        with mock.patch.object(
            core.shutil, "which", return_value="/usr/bin/ffmpeg"
        ), mock.patch.object(cli.subprocess, "run") as run_mock, redirect_stdout(
            io.StringIO()
        ), redirect_stderr(
            err
        ):
            rc = cli.main(["/definitely/not/here/zzz", "--from", "mov", "--to", "mp4"])
        self.assertEqual(rc, 2)
        run_mock.assert_not_called()
        self.assertIn("error", err.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
