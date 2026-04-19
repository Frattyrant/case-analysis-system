"""upload_module：编码与解析。"""
from __future__ import annotations

import io

import pandas as pd
from openpyxl import Workbook

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


def test_load_xls_ooxml_mislabeled() -> None:
    """扩展名为 .xls 但实际为 xlsx（ZIP）。"""
    wb = Workbook()
    ws = wb.active
    ws.append(["a", "b"])
    ws.append([1, 2])
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    assert content[:2] == b"PK"
    df = FileDataSource().load(content, "辽宁测试.xls")
    assert list(df.columns) == ["a", "b"]


def test_load_xls_html_table() -> None:
    html = (
        "<html><body><table>"
        "<tr><th>ColA</th><th>ColB</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table></body></html>"
    )
    df = FileDataSource().load(html.encode("utf-8"), "辽宁测试.xls")
    assert len(df) >= 1
    assert "ColA" in df.columns or "ColB" in df.columns


def test_apply_schema_extra_columns_trimmed() -> None:
    ds = FileDataSource()
    raw = pd.DataFrame({f"c{i}": [i] for i in range(10)})
    out, matched = ds.apply_schema(raw, "辽宁航班信息.xls")
    assert matched
    assert list(out.columns) == FileDataSource._SCHEMAS["航班"]
