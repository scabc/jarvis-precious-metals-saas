import os
import logging
import requests
from datetime import datetime
from data_engine_v3 import BankGoldEngine

def get_aggregated_data():
    engine = BankGoldEngine()
    result = engine.get_display_data()
    return result.get("data", [])
from notifier import send_gmail_notification

logger = logging.getLogger(__name__)

def update_global_reference(price_map):
    """更新全局参考价到数据库，作为前端断流时的兜底"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not all([supabase_url, supabase_key]): return

    url = f"{supabase_url}/rest/v1/global_settings?id=eq.1"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}", "Content-Type": "application/json"}
    payload = {
        "reference_prices": price_map,
        "last_updated": datetime.now().isoformat()
    }
    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=15)
        if resp.status_code not in (200, 204):
            print(f"数据库参考价更新失败: HTTP {resp.status_code} - {resp.text}")
        else:
            print(f"权威快照已更新: {len(price_map)} 个品种")
    except Exception as e:
        print(f"数据库参考价更新失败: {e}")

def fetch_tanshu_official():
    """使用探数 API 获取官方每日参考价 (限额使用)"""
    key = os.environ.get("TANSHU_KEY")
    if not key: return None
    try:
        res = requests.get(f"https://api.tanshuapi.com/api/gold_price/v1/index?key={key}", timeout=10)
        json = res.json()
        if json.get("code") == 1:
            data = json.get("data", [])
            ref = {}
            for i in data:
                name = i.get('name')
                if name in ['黄金现货', '伦敦金', '伦敦银', '铂金现货', '钯金现货']:
                    ref[name] = i.get('price')
            return ref
    except Exception as e:
        logger.warning(f"[fetch_ref_price] failed: {e}")
        return None
    return None

def fetch_jisu_all():
    """全量抓取极速数据所有金价接口"""
    key = os.environ.get("JISU_KEY")
    if not key: return None

    results = {}
    endpoints = [
        ("shgold", "上海金"),
        ("london", "国际期货"),
        ("bank", "银行账户"),
        ("hkgold", "香港金价"),
        ("exchangerate", "汇率"),
    ]

    hour = datetime.now().hour
    if 10 <= hour <= 22:
        endpoints.append(("storegold", "实物金店"))

    for path, label in endpoints:
        try:
            res = requests.get(f"https://api.jisuapi.com/gold/{path}?appkey={key}", timeout=10)
            json = res.json()
            if str(json.get("status")) == "0":
                data = json.get("result", [])
                if isinstance(data, list):
                    for i in data:
                        name = i.get("typename") or i.get("type") or i.get("from") or "主货币对"
                        results[f"{label}_{name}"] = i.get("price") or i.get("midprice")
                    print(f"成功同步: {label} ({len(data)} 条)")
                elif isinstance(data, dict):
                    # 汇率接口返回的是字典结构
                    for k, v in data.items():
                        if isinstance(v, (int, float)):
                            results[f"汇率_{k}"] = v
                    print(f"成功同步: {label}")
        except Exception as e:
            logger.warning(f"[fetch_jisu_all] {label} sync failed: {e}")
            continue

    return results

def get_subscriptions():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not all([supabase_url, supabase_key]): return []
    url = f"{supabase_url}/rest/v1/subscriptions?select=*"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"获取订阅列表失败: {e}")
        return []

def update_last_prices(email, price_map):
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    url = f"{supabase_url}/rest/v1/subscriptions?email=eq.{email}"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}", "Content-Type": "application/json"}
    try:
        requests.patch(url, headers=headers, json={"last_prices": price_map}, timeout=10)
    except Exception as e:
        logger.warning(f"[update_user_price] patch failed: {e}")

def generate_personalized_report(sub, market_data):
    user_metals = sub.get("metals", ["黄金9999", "AU9999"])
    user_threshold = float(sub.get("threshold", 0.003))
    is_pro = sub.get("plan") == "PRO"
    
    rows = ""
    should_send = False
    current_prices_snapshot = sub.get("last_prices", {})
    if not isinstance(current_prices_snapshot, dict): current_prices_snapshot = {}

    for item in market_data:
        name = item.get("f14") or item.get("name", "-")
        if name not in user_metals: continue
        
        try:
            price = float(item.get("f2") or 0)
            change_pct_raw = float(item.get("f3") or 0)
            change_pct = change_pct_raw / 100 
            
            if abs(change_pct) >= user_threshold:
                should_send = True
                
            color = "#ef4444" if change_pct < 0 else "#22c55e"
            arrow = "↓" if change_pct < 0 else "↑"
            
            rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">{name}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; font-weight: bold;">{price}</td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">
                    {arrow} {abs(change_pct_raw):.2f}%
                </td>
            </tr>
            """
            current_prices_snapshot[name] = price
        except (ValueError, TypeError): continue

    if not should_send or not rows: return None, None

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
        <div style="background: #000; color: #fff; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 18px;">Jarvis 智能监测预警 {"[PRO]" if is_pro else ""}</h2>
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
        </div>
        <div style="background: #f3f4f6; color: #9ca3af; padding: 15px; text-align: center; font-size: 10px;">
            报告时间: {now} | <a href="https://scabc.github.io/jarvis-precious-metals-saas/" style="color: #6b7280;">修改预警设置</a>
        </div>
    </div>
    """
    return html, current_prices_snapshot

def github_action_entry():
    print(f"开始执行 Jarvis 全局同步任务: {datetime.now()}")
    
    # 1. 尝试同步商业参考价（每 4 小时一次，即 00:00, 04:00, 08:00, 12:00, 16:00, 20:00）
    try:
        hour = datetime.now().hour
        if hour % 4 == 0:  # 每 4 小时运行一次商业同步
            print("启动商业源全量同步...")
            official_ref = fetch_jisu_all()
            if official_ref:
                update_global_reference(official_ref)
                print(f"官方权威快照已更新: {len(official_ref)} 个品种")
        else:
            print(f"跳过商业同步（当前小时: {hour}，下次同步: {(hour // 4 + 1) * 4}:00）")
    except Exception as e:
        print(f"参考价同步环节出错: {e}")

    # 2. 获取实时行情并发送邮件
    try:
        market_data = get_aggregated_data()
        if not market_data:
            print("未能获取实时行情数据，跳过邮件发送。")
            return

        subscriptions = get_subscriptions()
        print(f"读取到 {len(subscriptions)} 条有效订阅")

        for sub in subscriptions:
            email = sub.get("email")
            if not email: continue
            
            html_body, new_snapshot = generate_personalized_report(sub, market_data)
            if html_body:
                print(f"正在发送预警给: {email}")
                if send_gmail_notification(email, "⚠️ Jarvis 贵金属行情波动预警", html_body):
                    update_last_prices(email, new_snapshot)
    except Exception as e:
        print(f"邮件发送环节出错: {e}")

if __name__ == "__main__":
    github_action_entry()
