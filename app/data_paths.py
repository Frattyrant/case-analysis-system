from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config_manager import ConfigManager


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DataPaths:
    """项目 data 层目录约定：raw / cache / sample。"""

    root: Path
    raw: Path
    cache: Path
    sample: Path

    def case_raw_dir(self, case_id: str) -> Path:
        return self.raw / safe_case_dir_name(case_id)

    def case_cache_dir(self, case_id: str) -> Path:
        return self.cache / safe_case_dir_name(case_id)


def safe_case_dir_name(case_id: str) -> str:
    """将案件 ID 转为单层目录名，避免路径穿越。"""
    s = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(case_id).strip())
    if not s or s in {".", ".."}:
        return "unknown_case"
    return s


def default_paths() -> DataPaths:
    root = project_root() / "data"
    return DataPaths(root=root, raw=root / "raw", cache=root / "cache", sample=root / "sample")


def paths_from_config(config_manager: ConfigManager) -> DataPaths:
    """从 ConfigManager 解析路径，缺项时回落到默认 data/ 结构。"""
    d = default_paths()
    root = Path(config_manager.get("paths.data_root", str(d.root)))
    raw = Path(config_manager.get("paths.raw_dir", str(root / "raw")))
    cache = Path(config_manager.get("paths.cache_dir", str(root / "cache")))
    sample = Path(config_manager.get("paths.sample_dir", str(root / "sample")))
    return DataPaths(root=root, raw=raw, cache=cache, sample=sample)


def ensure_data_dirs(paths: DataPaths) -> None:
    for p in (paths.raw, paths.cache, paths.sample):
        p.mkdir(parents=True, exist_ok=True)


def persist_upload_bytes(paths: DataPaths, case_id: str, filename: str, content: bytes) -> Path:
    """用户上传原始字节落盘到 raw/{case}/filename。"""
    dest_dir = paths.case_raw_dir(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(filename).name
    dest.write_bytes(content)
    return dest
