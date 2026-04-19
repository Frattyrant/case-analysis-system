from __future__ import annotations

from typing import Optional


class GeoUtils:
    """地理工具：查找地名对应的省份，或者机场代码对应的城市。"""

    def __init__(self):
        """初始化地理工具，加载机场数据。"""
        try:
            import airportsdata
            self._airports = airportsdata.load('IATA')
        except ImportError:
            self._airports = {}

    def province_of(self, location: str) -> Optional[str]:
        """省份提取逻辑：调用 cpca 库自动解析地名中的省份。

        Args:
            location: 地名或地址字符串

        Returns:
            省份名称，如果无法解析则返回 None
        """
        if not location:
            return None
        try:
            import cpca
            df_res = cpca.transform([str(location)])
            if not df_res.empty:
                return df_res.iloc[0]['省']
        except:
            pass
        return None

    def city_of_airport(self, iata_code: str) -> str:
        """机场翻译逻辑：输入 PEK 这种代码，返回其所在的城市名。

        Args:
            iata_code: IATA 机场代码（如 PEK, SHA 等）

        Returns:
            城市名称，如果找不到则返回原始代码
        """
        val = str(iata_code).strip().upper()
        info = self._airports.get(val)
        return str(info['city']) if info and info.get('city') else val