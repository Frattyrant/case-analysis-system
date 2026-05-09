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
        self._cn_subd_map = {
            "beijing": "北京", "tianjin": "天津", "hebei": "河北", "shanxi": "山西",
            "inner mongolia": "内蒙古", "liaoning": "辽宁", "jilin": "吉林", "heilongjiang": "黑龙江",
            "shanghai": "上海", "jiangsu": "江苏", "zhejiang": "浙江", "anhui": "安徽",
            "fujian": "福建", "jiangxi": "江西", "shandong": "山东", "henan": "河南",
            "hubei": "湖北", "hunan": "湖南", "guangdong": "广东", "guangxi": "广西",
            "hainan": "海南", "chongqing": "重庆", "sichuan": "四川", "guizhou": "贵州",
            "yunnan": "云南", "xizang": "西藏", "tibet": "西藏", "shaanxi": "陕西",
            "gansu": "甘肃", "qinghai": "青海", "ningxia": "宁夏", "xinjiang": "新疆",
            "hong kong": "香港", "macau": "澳门", "taiwan": "台湾",
        }
        self._city_to_province = {
            "沈阳": "辽宁", "大连": "辽宁", "鞍山": "辽宁", "抚顺": "辽宁", "本溪": "辽宁",
            "北京": "北京", "上海": "上海", "天津": "天津", "重庆": "重庆",
            "广州": "广东", "深圳": "广东", "珠海": "广东", "佛山": "广东",
            "成都": "四川", "武汉": "湖北", "西安": "陕西", "杭州": "浙江", "南京": "江苏",
            "长沙": "湖南", "郑州": "河南", "济南": "山东", "青岛": "山东", "哈尔滨": "黑龙江",
            "长春": "吉林", "石家庄": "河北", "太原": "山西", "合肥": "安徽", "福州": "福建",
            "南昌": "江西", "南宁": "广西", "海口": "海南", "贵阳": "贵州", "昆明": "云南",
            "兰州": "甘肃", "西宁": "青海", "银川": "宁夏", "乌鲁木齐": "新疆", "拉萨": "西藏",
            "呼和浩特": "内蒙古", "香港": "香港", "澳门": "澳门", "台北": "台湾",
        }
        self._en_city_to_cn = {
            "beijing": "北京", "shanghai": "上海", "tianjin": "天津", "chongqing": "重庆",
            "shenyang": "沈阳", "dalian": "大连", "guangzhou": "广州", "shenzhen": "深圳",
            "chengdu": "成都", "wuhan": "武汉", "xian": "西安", "xiamen": "厦门",
            "hangzhou": "杭州", "nanjing": "南京", "changsha": "长沙", "zhengzhou": "郑州",
            "kunming": "昆明", "haikou": "海口", "harbin": "哈尔滨", "changchun": "长春",
            "qingdao": "青岛", "jinan": "济南", "fuzhou": "福州", "nanchang": "南昌",
            "guiyang": "贵阳", "urumqi": "乌鲁木齐", "lhasa": "拉萨",
        }

        # ── 省份解析缓存 (惰性初始化) ──
        self._province_cache: dict[str, Optional[str]] = {}
        self._cpca_available: bool | None = None

    # ── 核心优化: 批量机场代码 → 省份映射 ─────────

    def build_airport_province_map(self, airport_codes: list[str], target_provinces: set[str]) -> dict[str, bool]:
        """批量构建机场代码 → 是否属于目标省份的映射。
        对每个唯一代码仅计算一次，避免 cpca 逐行调用。
        返回 {IATA_code: True/False}，可直接用于 df.map()。
        """
        unique_codes = list(set(str(c).strip().upper() for c in airport_codes))
        result: dict[str, bool] = {}

        for code in unique_codes:
            # 优先用 airportsdata 直接查省份（O(1) 字典查找）
            info = self._airports.get(code)
            if info and str(info.get("country", "")).upper() == "CN":
                subd = str(info.get("subd", "")).strip()
                if subd:
                    key = subd.lower()
                    prov = self._cn_subd_map.get(key, subd)
                    prov_clean = prov.replace('省', '') if prov else ''
                    result[code] = prov_clean in target_provinces
                    continue

            # 回退: 机场代码 → 城市名 → 省份
            city = str(info['city']) if info and info.get('city') else code
            prov = self.province_of(city)
            prov_clean = (prov or '').replace('省', '')
            result[code] = prov_clean in target_provinces

        return result

    # ── 省份解析 ─────────────────────────────────

    def province_of(self, location: str) -> Optional[str]:
        """省份提取逻辑（带缓存，避免重复cpca调用）。"""
        if not location:
            return None
        text = str(location).strip()
        if not text:
            return None

        # 命中缓存直接返回
        if text in self._province_cache:
            return self._province_cache[text]

        result: Optional[str] = None

        # 尝试 cpca (首次调用)
        if self._cpca_available is None:
            try:
                import cpca
                cpca.transform(["北京"])  # 预热测试
                self._cpca_available = True
            except Exception:
                self._cpca_available = False

        if self._cpca_available:
            try:
                import cpca
                df_res = cpca.transform([text])
                if not df_res.empty:
                    val = df_res.iloc[0]['省']
                    if val and str(val) != 'nan':
                        result = val
            except Exception:
                pass

        # 兜底1: 直接包含省份关键字
        if result is None:
            for key in [
                "辽宁", "吉林", "黑龙江", "河北", "山西", "陕西", "甘肃", "青海", "山东", "江苏", "浙江",
                "安徽", "福建", "江西", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南",
                "北京", "上海", "天津", "重庆", "内蒙古", "广西", "宁夏", "新疆", "西藏", "香港", "澳门", "台湾",
            ]:
                if key in text:
                    result = key
                    break

        # 兜底2: 城市→省份映射
        if result is None:
            for city, prov in self._city_to_province.items():
                if city in text:
                    result = prov
                    break

        self._province_cache[text] = result
        return result

    # ── 机场工具 ─────────────────────────────────

    def city_of_airport(self, iata_code: str) -> str:
        val = str(iata_code).strip().upper()
        info = self._airports.get(val)
        return str(info['city']) if info and info.get('city') else val

    def city_of_airport_cn(self, iata_code: str) -> str:
        """机场代码转中文城市名（可转时），否则返回原值。"""
        city = self.city_of_airport(iata_code)
        key = str(city).strip().lower()
        return self._en_city_to_cn.get(key, str(city))

    def normalize_city(self, location: str) -> Optional[str]:
        """将输入地名标准化为中文城市名（如能识别）。"""
        if not location:
            return None
        text = str(location).strip()
        try:
            import cpca
            df_res = cpca.transform([text])
            if not df_res.empty:
                city = str(df_res.iloc[0].get("市", "")).strip()
                if city and city != "nan":
                    return city.replace("市", "")
        except Exception:
            pass
        for city in self._city_to_province:
            if city in text:
                return city
        key = text.lower()
        if key in self._en_city_to_cn:
            return self._en_city_to_cn[key]
        return text.replace("市", "")

    def province_of_airport(self, iata_code: str) -> Optional[str]:
        """直接根据机场代码解析省份。"""
        val = str(iata_code).strip().upper()
        info = self._airports.get(val)
        if not info:
            return None
        if str(info.get("country", "")).upper() != "CN":
            return None
        subd = str(info.get("subd", "")).strip()
        if not subd:
            return None
        key = subd.lower()
        if key in self._cn_subd_map:
            return self._cn_subd_map[key]
        return subd
