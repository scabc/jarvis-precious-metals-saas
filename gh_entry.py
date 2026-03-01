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

def github_action_entry():
    sender, password = os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD")
    market_data = get_aggregated_data()
    
    # 每日两次自动同步 (通过判断当前小时来节约 API 额度)
    # 假设 Action 每 5-10 分钟跑一次，我们只在 9:00 和 20:00 的第一次运行请求探数
    hour = datetime.now().hour
    minute = datetime.now().minute
    if hour in [9, 20] and minute < 10:
        print(f"[{hour}:00] 触发探数 API 官方校准...")
        ref_prices = fetch_tanshu_official()
        if ref_prices:
            update_global_reference(ref_prices)
            print(f"官方参考价已同步: {ref_prices}")

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
