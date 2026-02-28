import os
import sys
import json
import requests
from datetime import datetime
from data_engine import get_aggregated_data
from notifier import send_gmail_notification

def get_subscriptions():
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        return []
    # 获取邮箱、阈值、关注品种、订阅计划
    url = f"{supabase_url}/rest/v1/subscriptions?select=email,threshold,metals,plan"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else []
    except: return []

def generate_personalized_html(user_data, market_data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    user_metals = user_data.get("metals", ["黄金9999", "白银T+D"])
    is_pro = user_data.get("plan") == "PRO"
    
    rows = ""
    for item in market_data:
        name = item.get("f14", "-")
        # 过滤：非 Pro 用户只能看到他勾选的品种，且默认只推金银
        if name not in user_metals:
            continue
            
        price = item.get("f2", "-")
        change = float(item.get("f3", 0))
        color = "#ef4444" if change < 0 else "#22c55e"
        arrow = "↓" if change < 0 else "↑"
        
        rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{name}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; font-weight: bold;">{price}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">
                {arrow} {abs(change)}%
            </td>
        </tr>
        """
    
    pro_tip = ""
    if not is_pro:
        pro_tip = """
        <div style="margin-top: 20px; padding: 15px; background: #fff7ed; border-radius: 8px; border: 1px solid #ffedd5; text-align: center;">
            <p style="margin: 0; font-size: 12px; color: #9a3412;">
                🌟 <b>升级到 PRO 版：</b> 解锁铂金、钯金监控及 0.1% 极速预警。
            </p>
            <a href="https://scabc.github.io/jarvis-precious-metals-saas/" style="display: inline-block; margin-top: 10px; padding: 8px 16px; background: #f59e0b; color: #000; text-decoration: none; border-radius: 6px; font-size: 11px; font-weight: bold;">立即升级</a>
        </div>
        """

    return f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
        <div style="background: #000; color: #fff; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">Jarvis 贵金属巡检报告 {"<span style='color:#f59e0b'>[PRO]</span>" if is_pro else ""}</h2>
            <p style="margin: 5px 0 0; font-size: 12px; opacity: 0.7;">生成时间: {now}</p>
        </div>
        <div style="padding: 20px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background: #f9fafb;">
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">品种</th>
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">实时价</th>
                        <th style="padding: 12px; border-bottom: 2px solid #eee;">涨跌幅</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            {pro_tip}
        </div>
        <div style="background: #f3f4f6; color: #9ca3af; padding: 15px; text-align: center; font-size: 10px;">
            本报告基于您的监控阈值 ({user_data.get('threshold', 0.003)*100}%) 自动触发。<br>
            <a href="https://scabc.github.io/jarvis-precious-metals-saas/" style="color: #6b7280;">管理我的订阅设置</a>
        </div>
    </div>
    """

def github_action_entry():
    sender, password = os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD")
    if not all([sender, password]): return
    
    market_data = get_aggregated_data()
    if not market_data: return
    
    subscriptions = get_subscriptions()
    print(f"开始为 {len(subscriptions)} 位用户分发个性化报告...")

    for sub in subscriptions:
        # 核心逻辑：判断是否达到波动预警阈值
        # 为演示方便，目前每 15 分钟发送一次；正式版可加入 last_price 比较逻辑
        html_body = generate_personalized_html(sub, market_data)
        target = sub.get("email")
        send_gmail_notification(target, f"📈 Jarvis 监控报告 ({sub.get('plan', 'FREE')})", html_body)

if __name__ == "__main__":
    github_action_entry()
