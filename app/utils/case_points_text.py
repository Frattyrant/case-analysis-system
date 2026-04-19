"""案发记录 `case_points` 与多行文本互转（纯函数，便于测试与后续入库序列化）。"""

from __future__ import annotations


def format_case_points(lines: list[tuple[str, str]]) -> str:
    if not lines:
        return ""
    return "\n".join(f"{d.strip()}, {c.strip()}" for d, c in lines)


def parse_case_points_text(raw: str) -> tuple[list[tuple[str, str]], str | None]:
    """
    每行：`日期, 城市`（第一个逗号分隔日期与城市）。

    Returns:
        (points, error_message)；成功时 error_message 为 None。
    """
    out: list[tuple[str, str]] = []
    for i, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        if "," not in s:
            return [], f"第 {i} 行缺少逗号，格式应为：日期, 城市"
        date_part, city_part = s.split(",", 1)
        d, c = date_part.strip(), city_part.strip()
        if not d or not c:
            return [], f"第 {i} 行日期或城市不能为空"
        out.append((d, c))
    return out, None
