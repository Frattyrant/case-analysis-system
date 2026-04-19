"""upload_module：编码与解析。"""
from __future__ import annotations

from app.modules.upload_module import FileDataSource


def test_load_csv_utf8_sig() -> None:
    ds = FileDataSource()
    raw = "\ufeffa,b\n1,2\n".encode("utf-8")
    df = ds.load(raw, "t.csv")
    assert list(df.columns) == ["a", "b"]
    assert int(df.iloc[0]["a"]) == 1


def test_load_csv_gbk() -> None:
    ds = FileDataSource()
    raw = "姓名,值\n张三,1\n".encode("gbk")
    df = ds.load(raw, "t.csv")
    assert len(df) == 1
    assert "姓名" in df.columns
