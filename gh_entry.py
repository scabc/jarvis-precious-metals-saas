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
        return [{"email": os.environ.get("TARGET_EMAIL"), "threshold": 0.003}]
    url = f"{supabase_url}/rest/v1/subscriptions?select=email,threshold,banks"
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else []
    except: return []

def generate_html_report(data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = ""
    for item in data:
        name = item.get("f14", "-")
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
    
    return f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
        <div style="background: #000; color: #fff; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">Jarvis 贵金属智能巡检</h2>
            <p style="margin: 5px 0 0; font-size: 12px; opacity: 0.7;">报告生成时间: {now}</p>
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
            <div style="margin-top: 25px; padding: 15px; background: #fffbeb; border-radius: 8px; border: 1px solid #fef3c7;">
                <p style="margin: 0; font-size: 13px; color: #92400e;">
                    💡 <b>智能提示：</b> 当前市场波动率保持在正常范围内。请关注晚间美盘开盘后的行情异动。
                </p>
            </div>
        </div>
        <div style="background: #f3f4f6; color: #9ca3af; padding: 15px; text-align: center; font-size: 11px;">
            您收到此邮件是因为您在 Jarvis Precious Metal SaaS 进行了订阅。<br>
            想要退订？请联系系统管理员 Lore。
        </div>
    </div>
    """

def github_action_entry():
    sender, password = os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD")
    if not all([sender, password]): return
    
    data = get_aggregated_data()
    if not data: return
    
    html_body = generate_html_report(data)
    subscriptions = get_subscriptions()
    
    for sub in subscriptions:
        target = sub.get("email")
        send_gmail_notification(target, "📈 Jarvis 贵金属实时行情快报", html_body)

if __name__ == "__main__":
    github_action_entry()
