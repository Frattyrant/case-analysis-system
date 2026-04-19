from __future__ import annotations

from typing import Optional

import pandas as pd


class IdentityUtils:
    """嫌疑人身份推断工具：通过身份证号判性别和户籍区域。"""

    _NORTH = {'11', '12', '13', '14', '15', '21', '22', '23', '37', '41', '61', '62', '63', '64', '65'}
    _SOUTH = {'31', '32', '33', '34', '35', '36', '42', '43', '44', '45', '46', '50', '51', '52', '53', '54'}

    @classmethod
    def gender(cls, id_str: str) -> Optional[str]:
        """核心逻辑：看身份证倒数第二位，奇数是男，偶数是女。

        Args:
            id_str: 身份证号码

        Returns:
            '男性' 或 '女性'，如果无法判断则返回 None
        """
        s = str(id_str).strip()
        if len(s) < 17 or not s[:17].isdigit():
            return None
        return '男性' if int(s[16]) % 2 == 1 else '女性'

    @classmethod
    def region(cls, id_str: str) -> Optional[str]:
        """核心逻辑：根据身份证前两位代码判断属于南方还是北方。

        Args:
            id_str: 身份证号码

        Returns:
            '北方' 或 '南方'，如果无法判断则返回 None
        """
        s = str(id_str).strip()
        if len(s) < 2:
            return None
        prefix = s[:2]
        return '北方' if prefix in cls._NORTH else ('南方' if prefix in cls._SOUTH else None)

    @classmethod
    def apply_filters(cls, df: pd.DataFrame, gender: Optional[str] = None, region: Optional[str] = None) -> pd.DataFrame:
        """一键画像筛选：给一个大表，按照设定的性别、地域条件自动过滤出嫌疑人。

        Args:
            df: 包含身份证号列的数据框
            gender: 性别筛选条件 ('男性' 或 '女性')
            region: 地域筛选条件 ('北方' 或 '南方')

        Returns:
            筛选后的数据框
        """
        if df.empty or '身份证号' not in df.columns:
            return df
        result = df.copy()
        result['_id'] = result['身份证号'].astype(str).str.strip()
        if gender:
            result = result[result['_id'].apply(cls.gender) == gender]
        if region:
            result = result[result['_id'].apply(cls.region) == region]
        return result.drop(columns=['_id']).reset_index(drop=True)