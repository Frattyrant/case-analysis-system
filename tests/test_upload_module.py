"""upload_module：按 demo 读取规则（skiprows=2 + header=None）。"""
from __future__ import annotations

import pandas as pd

from app.modules.upload_module import FileDataSource


def test_load_csv_skiprows_and_no_header() -> None:
    ds = FileDataSource()
    raw = "备注1\n备注2\n1,2\n3,4\n".encode("utf-8")
    df = ds.load(raw, "t.csv")
    assert list(df.columns) == [0, 1]
    assert int(df.iloc[0][0]) == 1
    assert int(df.iloc[1][1]) == 4


def test_apply_schema_rental_columns() -> None:
    ds = FileDataSource()
    raw = pd.DataFrame({i: [f"v{i}"] for i in range(9)})
    out, matched = ds.apply_schema(raw, "辽宁汽车租赁信息.xls")
    assert matched
    assert list(out.columns) == FileDataSource._SCHEMAS["租赁"]


def test_apply_schema_motor_keep_columns() -> None:
    ds = FileDataSource()
    raw = pd.DataFrame({i: [f"v{i}"] for i in range(10)})
    out, matched = ds.apply_schema(raw, "辽宁机动车信息库.xls")
    assert matched
    assert list(out.columns) == FileDataSource._KEEP_COLUMNS["机动车"]
