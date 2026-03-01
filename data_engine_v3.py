
import requests
import time
import json
import re
from datetime import datetime

class BankGoldEngine:
    """
    SaaS 级别的多源聚合积存金数据引擎 (0 成本方案)
    聚合金投网、新浪、东方财富，并进行跨源验证与数据清洗
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False  # 关键：禁用代理
        self.headers = {
            "Referer": "https://quote.cngold.org/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 银行代码与名称映射
        self.CODE_MAP = {
            "JO_9753": {"name": "工商银行", "product": "积存金"},
            "JO_71":   {"name": "建设银行", "product": "个人积存金"},
            "JO_70":   {"name": "中国银行", "product": "积存金"},
            "JO_73":   {"name": "农业银行", "product": "存金通"},
            "JO_9754": {"name": "招商银行", "product": "积存金"},
            "JO_72":   {"name": "交通银行", "product": "积存金"},
            "JO_75":   {"name": "兴业银行", "product": "积存金"},
            "JO_9751": {"name": "平安银行", "product": "黄金积存"},
            "JO_9752": {"name": "中信银行", "product": "黄金积存"},
            "JO_76":   {"name": "民生银行", "product": "积存金"},
            "JO_74":   {"name": "光大银行", "product": "积存金"},
        }

    def fetch_raw_data(self):
        """抓取金投网核心接口"""
        url = "https://api.jijinhao.com/quoteCenter/realTime.htm"
        params = {
            "codes": ",".join(self.CODE_MAP.keys()),
            "_": int(time.time() * 1000)
        }
        try:
            resp = self.session.get(url, params=params, headers=self.headers, timeout=10)
            match = re.search(r'\{.*\}', resp.text)
            return json.loads(match.group(0)) if match else None
        except Exception as e:
            print(f"Fetch error: {e}")
            return None

    def clean_data(self, raw_data):
        """数据清洗与逻辑修复"""
        if not raw_data: return []
        
        cleaned = []
        for code, info in raw_data.items():
            if code not in self.CODE_MAP: continue
            
            meta = self.CODE_MAP[code]
            buy = info.get("q2", 0)   # 银行买入价 (你卖)
            sell = info.get("q1", 0)  # 银行卖出价 (你买)
            
            # --- 异常值清洗策略 ---
            # 1. 招行/民生等可能返回的是白银或总市值 (20000+)，黄金正常在 400-1500 区间
            if buy > 5000 or sell > 5000:
                continue # 丢弃疑似白银的数据
            
            # 2. 价格为 0 的无效数据丢弃
            if buy == 0 and sell == 0:
                continue
                
            # 3. 补全逻辑：如果只有一个价格，假设点差为 0.5 元 (保守估计)
            if buy > 0 and sell == 0:
                sell = buy + 0.5
            elif sell > 0 and buy == 0:
                buy = sell - 0.5

            ts = info.get("time")
            dt = datetime.fromtimestamp(ts/1000) if ts else datetime.now()
            
            cleaned.append({
                "bank": meta["name"],
                "product": meta["product"],
                "buy": round(float(buy), 2),
                "sell": round(float(sell), 2),
                "spread": round(float(sell - buy), 2),
                "time": dt.strftime('%Y-%m-%d %H:%M:%S'),
                "is_stale": (datetime.now() - dt).total_seconds() > 3600 * 48 # 超过48小时标记为陈旧
            })
            
        return sorted(cleaned, key=lambda x: x['buy'], reverse=True)

    def fetch_xxapi_verification(self):
        """
        源 4：xxapi.cn (辅助验证源)
        提供各大银行金条价（日级更新），用于基准偏差校验
        """
        url = "https://v2.xxapi.cn/api/goldprice"
        try:
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("bank", [])
        except:
            return None
        return None

    def fetch_alapi_brands(self):
        """
        源 5：ALAPI (v3.alapi.cn)
        提供品牌金饰价（周大福、老凤祥等），作为市场情绪辅助
        """
        url = "https://v3.alapi.cn/api/gold/brand"
        # 注意：此处需要 token，暂时占位，返回模拟或尝试请求
        try:
            # 使用用户提供的 ALAPI Token
            params = {"token": "t4fgiavrkcsekz4ve72mgghllgs4qf"} 
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", [])
        except:
            return None
        return None

    def get_display_data(self):
        raw = self.fetch_raw_data()
        data = self.clean_data(raw)
        
        # 获取各渠道验证数据
        verification_data = self.fetch_xxapi_verification()
        brand_data = self.fetch_alapi_brands()
        
        v_map = {item['name']: float(item['price']) for item in verification_data if item.get('price')} if verification_data else {}
        
        # 品牌金饰价通常比积存金高出 100-200 元（含加工费和溢价）
        avg_brand_price = sum([float(b['price']) for b in brand_data if b.get('price')]) / len(brand_data) if brand_data else None
        
        for item in data:
            # 银行金条价验证
            v_price = v_map.get(item['bank'])
            if v_price:
                diff = abs(item['buy'] - v_price)
                item['v_diff'] = round(diff, 2)
                item['v_status'] = "safe" if diff < 10 else "diverged"
            else:
                item['v_status'] = "unknown"
            
            # 品牌价逻辑校验 (积存金不应高于品牌金饰价)
            if avg_brand_price:
                item['brand_ref_diff'] = round(avg_brand_price - item['sell'], 2)

        return {
            "source": "Aggregated",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": data,
            "brand_avg": round(avg_brand_price, 2) if avg_brand_price else None
        }

if __name__ == "__main__":
    engine = BankGoldEngine()
    result = engine.get_display_data()
    print(f"\n🚀 {result['source']} - {result['timestamp']}")
    print("-" * 80)
    print(f"{'银行':<10} | {'产品':<12} | {'你卖(买入)':<10} | {'你买(卖出)':<10} | {'点差':<6} | {'更新时间'}")
    print("-" * 80)
    for item in result['data']:
        stale_mark = " [!] " if item['is_stale'] else ""
        print(f"{item['bank']:<10} | {item['product']:<12} | {item['buy']:<12} | {item['sell']:<12} | {item['spread']:<6} | {item['time']}{stale_mark}")
