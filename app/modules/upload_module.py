# app/modules/upload_module.py
import io
import pandas as pd
from typing import Any

class FileDataSource:
    """从字节流读取数据，并按预定义 Schema 规范化列名。"""
    
    _SCHEMAS = {
        '航班':['序号','姓名','身份证号','出发地','到达地','起飞时间','到达时间','航空公司','航班号','座位号','航班日期'],
        '机动车':['序号','号牌种类','号牌号码','车辆品牌','车身颜色','所有人','身份证号','c8','c9','c10'],
        '轨迹':['序号','号牌号码','号牌种类代码名称','通过时间','行政城市','行政区域','卡口名称'],
        '租赁':['序号','租赁公司名称','号牌号码','车辆品牌','起租时间','停租时间','租车人姓名','租车人身份证号码','租车人联系方式'],
        '旅店':['序号','姓名','身份证号','入住时间','退房时间','旅馆名称','房号','旅馆地址','所属派出所代码','所属派出所名称','真入住时间','真退房时间'],
    }
    _SCHEMAS['住宿'] = _SCHEMAS['旅店']
    _SCHEMAS['旅业'] = _SCHEMAS['旅店']

    _KEEP_COLUMNS = {
        '机动车': ['序号','号牌种类','号牌号码','车辆品牌','车身颜色','所有人','身份证号'],
    }

    def load(self, content: bytes, filename: str) -> pd.DataFrame:
        stream = io.BytesIO(content)
        reader = pd.read_csv if filename.lower().endswith('.csv') else pd.read_excel
        return reader(stream, header=None, skiprows=2)

    def apply_schema(self, df: pd.DataFrame, filename: str) -> tuple[pd.DataFrame, bool]:
        for key, cols in self._SCHEMAS.items():
            if key in filename:
                result = df.copy()
                result.columns = cols
                if key in self._KEEP_COLUMNS:
                    result = result[self._KEEP_COLUMNS[key]]
                return result, True
        return df, False

    def process_files(self, files: dict[str, bytes], state: Any) -> dict:
        summary = {"succeeded": 0, "failed": 0, "frames_in_state": 0, "errors":[]}
        for filename, content in files.items():
            try:
                raw_df = self.load(content, filename)
                df, matched = self.apply_schema(raw_df, filename)
                state["uploaded_frames"][filename] = df
                summary["succeeded"] += 1
            except Exception as exc:
                summary["failed"] += 1
                summary["errors"].append(f"{filename}: {exc}")

        summary["frames_in_state"] = len(state["uploaded_frames"])
        return summary