
import requests
import time
import json
import re
from datetime import datetime

def fetch_bank_gold_prices():
    """
    从金投网 (api.jijinhao.com) 抓取主流银行积存金实时价格
    """
    # 银行代码映射表
    CODE_MAP = {
        "JO_9753": "工商银行-积存金",
        "JO_71":   "建设银行-个人积存金",
        "JO_70":   "中国银行-积存金",
        "JO_73":   "农业银行-存金通",
        "JO_9754": "招商银行-积存金",
        "JO_72":   "交通银行-积存金",
        "JO_75":   "兴业银行-积存金",
        "JO_9751": "平安银行-黄金积存",
        "JO_9752": "中信银行-黄金积存",
        "JO_76":   "民生银行-积存金",
        "JO_74":   "光大银行-积存金",
    }

    url = "https://api.jijinhao.com/quoteCenter/realTime.htm"
    params = {
        "codes": ",".join(CODE_MAP.keys()),
        "_": int(time.time() * 1000)
    }
    headers = {
        "Referer": "https://quote.cngold.org/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    session = requests.Session()
    session.trust_env = False 

    try:
        response = session.get(url, params=params, headers=headers, timeout=10)
        text = response.text
        
        # 提取 JSON 内容
        match = re.search(r'\{.*\}', text)
        if not match:
            return None
            
        data_obj = json.loads(match.group(0))
        
        results = []
        for code, info in data_obj.items():
            if code in CODE_MAP:
                # 价格字段映射 (金投网私有代码)
                # q1: 卖出价, q2: 买入价, q3: 最新价, q4: 开盘, q5: 最高, q6: 最低, q70: 涨跌, q80: 涨跌幅, q59: 更新时间戳
                sell = info.get("q1")
                buy = info.get("q2")
                last = info.get("q3")
                ts = info.get("time")
                
                dt_str = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else "-"
                
                results.append({
                    "bank_name": CODE_MAP[code],
                    "buy_price": buy,
                    "sell_price": sell,
                    "last_price": last,
                    "update_time": dt_str,
                    "change": info.get("q70"),
                    "change_pct": info.get("q80"),
                })
        
        # 按银行名称排序
        results.sort(key=lambda x: x['bank_name'])
        return results

    except Exception as e:
        print(f"抓取异常: {e}")
        return None

if __name__ == "__main__":
    prices = fetch_bank_gold_prices()
    if prices:
        print(f"{'银行产品':<20} | {'银行买入':<8} | {'银行卖出':<8} | {'更新时间'}")
        print("-" * 75)
        for p in prices:
            # 这里的买入/卖出逻辑：
            # 对银行来说：q1是卖出价（你买入的价格），q2是买入价（你卖出的价格）
            print(f"{p['bank_name']:<20} | {str(p['buy_price']):<8} | {str(p['sell_price']):<8} | {p['update_time']}")
    else:
        print("未获取到数据")
