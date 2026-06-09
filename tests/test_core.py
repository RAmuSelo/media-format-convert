"""Unit tests for media_format_convert.core.

These tests never touch the network and never invoke a real ffmpeg: every
subprocess call is captured by a fake runner, and ffmpeg discovery is patched.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

# Make the src/ layout importable when running ``python -m unittest`` from the
# repo root without an editable install.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from media_format_convert import core  # noqa: E402


class NormalizeExtTests(unittest.TestCase):
    def test_strips_dot_and_lowercases(self):
        self.assertEqual(core.normalize_ext(".MP4"), "mp4")
        self.assertEqual(core.normalize_ext("OGG"), "ogg")
        self.assertEqual(core.normalize_ext("mp3"), "mp3")


class FindFfmpegTests(unittest.TestCase):
    def test_returns_path_when_present(self):
        with mock.patch.object(core.shutil, "which", return_value="/usr/bin/ffmpeg"):
            self.assertEqual(core.find_ffmpeg(), "/usr/bin/ffmpeg")

    def test_raises_clear_error_when_missing(self):
        with mock.patch.object(core.shutil, "which", return_value=None):
            with self.assertRaises(core.FfmpegNotFoundError) as ctx:
                core.find_ffmpeg()
        message = str(ctx.exception)
        self.assertIn("ffmpeg", message)
        self.assertIn("PATH", message)


class ProfileTests(unittest.TestCase):
    def test_mov_to_mp4_uses_h264_and_crf(self):
        profile = core.get_profile("mov", "mp4")
        self.assertIn("libx264", profile.extra_args)
        self.assertIn("-crf", profile.extra_args)
        self.assertIn("22", profile.extra_args)
        self.assertIn("aac", profile.extra_args)

    def test_oga_to_mp3_uses_stereo_44k_192k(self):
        profile = core.get_profile("oga", "mp3")
        self.assertIn("-b:a", profile.extra_args)
        self.assertIn("192k", profile.extra_args)
        self.assertIn("-ac", profile.extra_args)
        self.assertIn("2", profile.extra_args)
        self.assertIn("-ar", profile.extra_args)
        self.assertIn("44100", profile.extra_args)

    def test_ogg_to_wav_has_no_extra_codec_args(self):
        profile = core.get_profile("ogg", "wav")
        self.assertEqual(tuple(profile.extra_args), ())

    def test_unknown_pair_falls_back_to_defaults(self):
        profile = core.get_profile("flac", "aac")
        self.assertEqual(tuple(profile.extra_args), ())


class BuildCommandTests(unittest.TestCase):
    def test_mov_to_mp4_command_structure(self):
        profile = core.get_profile("mov", "mp4")
        cmd = core.build_ffmpeg_command(
            Path("/in/clip.mov"),
            Path("/out/clip.mp4"),
            profile,
            ffmpeg_path="ffmpeg",
        )
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertEqual(cmd[1], "-y")
        self.assertEqual(cmd[2], "-i")
        self.assertEqual(cmd[3], str(Path("/in/clip.mov")))
        # Output path is last.
        self.assertEqual(cmd[-1], str(Path("/out/clip.mp4")))
        # Codec args sit between input and output.
        self.assertIn("libx264", cmd)
        self.assertLess(cmd.index("libx264"), cmd.index(str(Path("/out/clip.mp4"))))

    def test_no_overwrite_uses_dash_n(self):
        profile = core.get_profile("ogg", "wav")
        cmd = core.build_ffmpeg_command(
            Path("a.ogg"), Path("a.wav"), profile, overwrite=False
        )
        self.assertIn("-n", cmd)
        self.assertNotIn("-y", cmd)

    def test_oga_to_mp3_full_command(self):
        profile = core.get_profile("oga", "mp3")
        cmd = core.build_ffmpeg_command(
            Path("/src/voice.oga"), Path("/dst/voice.mp3"), profile
        )
        self.assertEqual(
            cmd,
            [
                "ffmpeg",
                "-y",
                "-i",
                str(Path("/src/voice.oga")),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-ac",
                "2",
                "-ar",
                "44100",
                str(Path("/dst/voice.mp3")),
            ],
        )


class DiscoverFilesTests(unittest.TestCase):
    def _make_tree(self, tmp):
        root = Path(tmp)
        (root / "a.oga").write_bytes(b"x")
        (root / "b.OGA").write_bytes(b"x")  # case-insensitive match
        (root / "c.ogg").write_bytes(b"x")  # different extension
        (root / "d.txt").write_bytes(b"x")
        (root / "sub").mkdir()
        (root / "sub" / "deep.oga").write_bytes(b"x")  # not recursive
        return root

    def test_finds_matching_extension_case_insensitive_non_recursive(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_tree(tmp)
            found = core.discover_files(root, "oga")
            names = sorted(p.name for p in found)
            self.assertEqual(names, ["a.oga", "b.OGA"])

    def test_finds_with_dotted_extension_argument(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = self._make_tree(tmp)
            found = core.discover_files(root, ".ogg")
            self.assertEqual([p.name for p in found], ["c.ogg"])

    def test_missing_folder_raises(self):
        with self.assertRaises(NotADirectoryError):
            core.discover_files(Path("/no/such/folder/xyz"), "mp4")


class OutputPathTests(unittest.TestCase):
    def test_keeps_stem_changes_extension(self):
        out = core.output_path_for(Path("/in/note.oga"), "mp3", Path("/out"))
        self.assertEqual(out, Path("/out/note.mp3"))


class EnsureDistinctTests(unittest.TestCase):
    def test_same_extension_rejected(self):
        with self.assertRaises(ValueError):
            core.ensure_distinct("mp3", ".MP3")

    def test_different_extension_ok(self):
        core.ensure_distinct("oga", "mp3")  # should not raise


class ResolveOutDirTests(unittest.TestCase):
    def test_explicit_out_used_verbatim(self):
        self.assertEqual(
            core.resolve_out_dir(Path("/in/clips"), "mp4", "/somewhere/else"),
            Path("/somewhere/else"),
        )

    def test_default_is_sibling_with_target_ext(self):
        self.assertEqual(
            core.resolve_out_dir(Path("/in/recordings"), "mp3", None),
            Path("/in/recordings_mp3"),
        )


class RunConversionsTests(unittest.TestCase):
    def test_uses_runner_and_creates_out_dir(self):
        import tempfile

        calls = []

        def fake_runner(command, check):
            calls.append((command, check))

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            plan = [
                core.PlannedConversion(
                    src=Path("a.oga"),
                    dst=out_dir / "a.mp3",
                    command=["ffmpeg", "-y", "-i", "a.oga", str(out_dir / "a.mp3")],
                )
            ]
            done = core.run_conversions(plan, out_dir, runner=fake_runner)

            self.assertTrue(out_dir.exists())
            self.assertEqual(len(done), 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], True)  # check=True
            self.assertEqual(calls[0][0][0], "ffmpeg")


class PlanConversionsTests(unittest.TestCase):
    def test_builds_one_plan_entry_per_matching_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one.mov").write_bytes(b"x")
            (root / "two.mov").write_bytes(b"x")
            (root / "ignore.txt").write_bytes(b"x")

            out_dir = root / "out"
            plan = core.plan_conversions(root, "mov", "mp4", out_dir)

            self.assertEqual(len(plan), 2)
            for item in plan:
                self.assertEqual(item.dst.parent, out_dir)
                self.assertEqual(item.dst.suffix, ".mp4")
                self.assertIn("libx264", item.command)


if __name__ == "__main__":
    unittest.main()
