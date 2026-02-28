import requests
import json

def get_aggregated_data():
    """
    通过东方财富聚合接口获取贵金属数据
    这个接口比银行官网稳健得多，且包含了主流银行参考品种
    """
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1", "pz": "50", "po": "1", "np": "1",
        "ut": "bd1d9ddb040897f3cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f3",
        "fs": "m:118,m:119,m:120,m:121", # 包含黄金、白银、外汇等
        "fields": "f12,f14,f2,f3,f4" # 代码, 名称, 价格, 涨跌幅, 涨跌额
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data["rc"] == 0:
            diff = data["data"]["diff"]
            # 过滤出我们需要的品种
            targets = ["黄金9999", "白银T+D", "AU9999", "AGTD"]
            results = [item for item in diff if item["f14"] in targets or item["f12"] in targets]
            return results
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print(json.dumps(get_aggregated_data(), indent=2, ensure_ascii=False))
