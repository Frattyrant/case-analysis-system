from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """配置管理器，负责读取和保存配置到 JSON 文件。"""

    def __init__(self, config_path: Path):
        """
        初始化配置管理器。

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载配置。"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}
        else:
            self._config = self._get_default_config()
        self._migrate_legacy_paths()

    def _get_default_config(self) -> dict[str, Any]:
        """获取默认配置。"""
        data_root = Path(__file__).parent.parent / 'data'
        return {
            'database': {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '123456',
                'name': 'case_analysis'
            },
            'paths': {
                'data_root': str(data_root),
                'raw_dir': str(data_root / 'raw'),
                'cache_dir': str(data_root / 'cache'),
                'sample_dir': str(data_root / 'sample'),
            }
        }

    def _migrate_legacy_paths(self) -> None:
        """旧版 upload_dir / export_dir 映射到 raw_dir / cache_dir。"""
        paths = self._config.setdefault('paths', {})
        if 'raw_dir' not in paths and paths.get('upload_dir'):
            paths['raw_dir'] = paths['upload_dir']
        if 'cache_dir' not in paths and paths.get('export_dir'):
            paths['cache_dir'] = paths['export_dir']
        if 'data_root' not in paths:
            paths['data_root'] = str(Path(__file__).parent.parent / 'data')
        if 'sample_dir' not in paths:
            paths['sample_dir'] = str(Path(paths['data_root']) / 'sample')

    def save(self) -> None:
        """保存配置到文件。"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        Args:
            key: 配置键（支持点号分隔的嵌套键，如 'database.host'）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值。

        Args:
            key: 配置键（支持点号分隔的嵌套键，如 'database.host'）
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def database_config(self) -> dict[str, Any]:
        """获取数据库配置。"""
        return self._config.get('database', {})

    @property
    def paths_config(self) -> dict[str, Any]:
        """获取路径配置。"""
        return self._config.get('paths', {})
