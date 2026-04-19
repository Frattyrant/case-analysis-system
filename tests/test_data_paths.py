from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config_manager import ConfigManager
from app.data_paths import (
    DataPaths,
    default_paths,
    ensure_data_dirs,
    paths_from_config,
    persist_upload_bytes,
    safe_case_dir_name,
)


class TestDataPaths(unittest.TestCase):
    def test_safe_case_dir_name(self) -> None:
        self.assertEqual(safe_case_dir_name("case-01"), "case-01")
        self.assertNotIn("/", safe_case_dir_name("../x"))
        self.assertEqual(safe_case_dir_name(".."), "unknown_case")

    def test_ensure_and_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            paths = DataPaths(root=root, raw=root / "raw", cache=root / "cache", sample=root / "sample")
            ensure_data_dirs(paths)
            out = persist_upload_bytes(paths, "c1", "a.csv", b"x,y\n1,2\n")
            self.assertTrue(out.exists())
            self.assertEqual(out.read_bytes(), b"x,y\n1,2\n")

    def test_paths_from_config_defaults(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            p = Path(f.name)
        try:
            cm = ConfigManager(p)
            paths = paths_from_config(cm)
            self.assertTrue(paths.raw.name == "raw")
            self.assertTrue(paths.cache.name == "cache")
            self.assertTrue(paths.sample.name == "sample")
        finally:
            p.unlink(missing_ok=True)

    def test_default_paths_under_project(self) -> None:
        dp = default_paths()
        self.assertEqual(dp.raw.parent, dp.root)


if __name__ == "__main__":
    unittest.main()
