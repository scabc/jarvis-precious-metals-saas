import os
import requests
from datetime import datetime
from data_engine import get_aggregated_data
from notifier import send_gmail_notification

def update_global_reference(price_map):
    """更新全局参考价到数据库，作为前端断流时的兜底"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    # 假设我们有一个专门存放公共数据的表 global_settings
    url = f"{supabase_url}/rest/v1/global_settings?id=eq.1"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}", "Content-Type": "application/json"}
    requests.patch(url, headers=headers, json={"reference_prices": price_map, "last_updated": datetime.now().isoformat()})

def fetch_tanshu_official():
    """使用探数 API 获取官方每日参考价 (限额使用)"""
    key = os.environ.get("TANSHU_KEY")
    if not key: return None
    try:
        res = requests.get(f"https://api.tanshuapi.com/api/gold_price/v1/index?key={key}", timeout=10)
        json = res.json()
        if json.get("code") == 1:
            data = json.get("data", [])
            # 提取关键价格
            ref = {}
            for i in data:
                if i['name'] in ['黄金现货', '伦敦金', '伦敦银']:
                    ref[i['name']] = i['price']
            return ref
    except: return None
    return None

def get_subscriptions():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key: return []
    url = f"{supabase_url}/rest/v1/subscriptions?select=*"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else []
    except: return []

def update_last_prices(email, price_map):
    """更新用户的上次通知价格快照"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    url = f"{supabase_url}/rest/v1/subscriptions?email=eq.{email}"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}", "Content-Type": "application/json", "Prefer": "return=minimal"}
    requests.patch(url, headers=headers, json={"last_prices": price_map})

def generate_personalized_report(sub, market_data):
    user_metals = sub.get("metals", ["黄金9999"])
    user_threshold = sub.get("threshold", 0.003)
    user_banks = sub.get("banks", ["中国银行"])
    is_pro = sub.get("plan") == "PRO"
    
    rows = ""
    should_send = False
    current_prices_snapshot = sub.get("last_prices", {})

    for item in market_data:
        name = item.get("f14", "-")
        if name not in user_metals: continue
        
        price = float(item.get("f2", 0))
        change_pct = float(item.get("f3", 0)) / 100 # 转为小数
        
        # 触发逻辑：如果涨跌幅绝对值 > 用户阈值，则视为需要提醒
        if abs(change_pct) >= user_threshold:
            should_send = True
            
        color = "#ef4444" if change_pct < 0 else "#22c55e"
        arrow = "↓" if change_pct < 0 else "↑"
        
        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{name}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; font-weight: bold;">{price}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">
                {arrow} {abs(change_pct)*100:.2f}%
            </td>
        </tr>
        """
        current_prices_snapshot[name] = price

    if not should_send: return None, None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
        <div style="background: #000; color: #fff; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 18px;">Jarvis 智能监测预警 {"[PRO]" if is_pro else ""}</h2>
            <p style="margin: 5px 0 0; font-size: 11px; opacity: 0.6;">行情来源: {', '.join(user_banks)}</p>
        </div>
        <div style="padding: 20px;">
            <p style="font-size: 13px; color: #374151;">检测到市场波动已触发您的预警阈值 (<b>{user_threshold*100:.1f}%</b>)：</p>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-top: 15px;">
                <thead>
                    <tr style="background: #f9fafb; font-size: 12px;">
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">品种</th>
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">最新成交价</th>
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">24h 涨跌</th>
                    </tr>
                </thead>
                <tbody style="font-size: 14px;">{rows}</tbody>
            </table>
            {"<div style='margin-top:20px; padding:15px; background:#fff7ed; border-radius:8px; font-size:11px; color:#9a3412;'>🌟 <b>PRO 权益：</b> 您已解锁高频监控。后台正为您锁定最优盘面。</div>" if is_pro else ""}
        </div>
        <div style="background: #f3f4f6; color: #9ca3af; padding: 15px; text-align: center; font-size: 10px;">
            报告时间: {now} | <a href="https://scabc.github.io/jarvis-precious-metals-saas/" style="color: #6b7280;">修改预警阈值</a>
        </div>
    </div>
    """
    return html, current_prices_snapshot

def fetch_jisu_official():
    """使用极速数据 API 获取官方价格 (备选源)"""
    key = os.environ.get("JISU_KEY")
    if not key: return None
    try:
        res = requests.get(f"https://api.jisuapi.com/gold/shgold?appkey={key}", timeout=10)
        json = res.json()
        if json.get("status") == 0:
            data = json.get("result", [])
            ref = {}
            for i in data:
                # 极速数据的名称匹配逻辑
                name = i.get("typename")
                if name == "黄金延期": ref["Au(T+D)"] = i["price"]
                if name == "沪金99": ref["Au99.99"] = i["price"]
                if "伦敦金" in name: ref["伦敦金"] = i["price"]
            return ref
    except: return None
    return None

def fetch_jisu_bank():
    """使用极速数据获取银行账户金属价格 (支持铂金、钯金)"""
    key = os.environ.get("JISU_KEY")
    if not key: return None
    try:
        res = requests.get(f"https://api.jisuapi.com/gold/bank?appkey={key}", timeout=10)
        json = res.json()
        if json.get("status") == 0:
            data = json.get("result", [])
            ref = {}
            for i in data:
                name = i.get("typename")
                if name == "人民币账户黄金": ref["账户黄金"] = i["midprice"]
                if name == "人民币账户白银": ref["账户白银"] = i["midprice"]
                if name == "人民币账户铂金": ref["账户铂金"] = i["midprice"]
                if name == "人民币账户钯金": ref["账户钯金"] = i["midprice"]
            return ref
    except: return None
    return None

def fetch_jisu_all():
    """全量抓取极速数据所有金价接口 (优化额度使用)"""
    key = os.environ.get("JISU_KEY")
    if not key: return None
    
    results = {}
    endpoints = [
        ("shgold", "上海金"),
        ("london", "国际金银铂钯期货"),
        ("bank", "银行账户金银铂钯"),
        ("hkgold", "香港金价")
    ]
    
    # 仅在白天 (10:00 - 22:00) 抓取金店金价，节省额度
    hour = datetime.now().hour
    if 10 <= hour <= 22:
        endpoints.append(("storegold", "实物金店"))

    for path, label in endpoints:
        try:
            res = requests.get(f"https://api.jisuapi.com/gold/{path}?appkey={key}", timeout=10)
            json = res.json()
            if json.get("status") == 0 or json.get("status") == "0":
                data = json.get("result", [])
                if isinstance(data, list):
                    for i in data:
                        name = i.get("typename") or i.get("type")
                        results[f"{label}_{name}"] = i.get("price") or i.get("midprice")
                print(f"成功同步: {label}")
            else:
                print(f"接口 {label} 返回状态非0: {json.get('msg')}")
        except Exception as e:
            print(f"抓取 {label} 失败: {e}")
            
    return results

def github_action_entry():
    sender, password = os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD")
    market_data = get_aggregated_data()
    
    # 商业 API 智能调度 (调整为每小时 1 次，确保额度 100/日 够用)
    # 每次同步耗费 4-5 个额度，24小时 * 4 = 96-120 额度
    minute = datetime.now().minute
    if minute < 10: # 每个小时的前 10 分钟运行一次
        print(f"[{datetime.now().strftime('%H:%M')}] 启动商业源全量同步 (JisuAPI 究极版)...")
        
        # 1. 尝试探数校准 (每日 9:00 / 20:00)
        hour = datetime.now().hour
        if hour in [9, 20]:
            ts_ref = fetch_tanshu_official()
            if ts_ref:
                update_global_reference(ts_ref)
                print("探数官方源已同步。")

        # 2. 极速数据全量抓取 (每小时一次)
        official_ref = fetch_jisu_all()
        
        if official_ref:
            update_global_reference(official_ref)
            print(f"官方权威全品种快照已更新: {len(official_ref)} 个品种")
            
    if not market_data or not all([sender, password]): return
    
    subscriptions = get_subscriptions()
    for sub in subscriptions:
        email = sub.get("email")
        html_body, new_snapshot = generate_personalized_report(sub, market_data)
        
        if html_body:
            print(f"正在发送预警给: {email}")
            if send_gmail_notification(email, "⚠️ Jarvis 贵金属行情波动预警", html_body):
                update_last_prices(email, new_snapshot)
        else:
            print(f"用户 {email} 未触发波动阈值，跳过发送。")

if __name__ == "__main__":
    github_action_entry()
