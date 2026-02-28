import os
import sys
import json
import requests
from data_engine import get_aggregated_data
from notifier import send_gmail_notification

def get_subscriptions():
    """从 Supabase 获取所有订阅者列表"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("警告: 缺失 Supabase 配置，回退到单用户模式。")
        return [{"email": os.environ.get("TARGET_EMAIL"), "threshold": 0.003}]

    url = f"{supabase_url}/rest/v1/subscriptions?select=email,threshold,banks"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"读取订阅列表失败: {e}")
    return []

def github_action_entry():
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("APP_PASSWORD")
    
    if not all([sender, password]):
        print("错误: 核心发件配置缺失!")
        return

    print("正在获取实时贵金属行情...")
    data = get_aggregated_data()
    
    if not data:
        print("数据抓取失败。")
        return

    # 生成行情简报
    report_lines = []
    for item in data:
        name = item.get("f14", "未知品种")
        price = item.get("f2", "-")
        change = item.get("f3", "0.00")
        report_lines.append(f"- {name}: {price} (涨跌: {change}%)")
    
    report_content = "\n".join(report_lines)
    
    # 获取订阅者并分发
    subscriptions = get_subscriptions()
    print(f"共发现 {len(subscriptions)} 位订阅者。")
    
    for sub in subscriptions:
        target = sub.get("email")
        # 这里可以根据 sub.get("threshold") 做更精细的波动判断
        # MVP 阶段先给所有订阅者发送当前快报
        body = f"【Jarvis SaaS - 您订阅的实时行情】\n\n{report_content}\n\n--- 祝您交易顺利 ---"
        
        print(f"正在发送至: {target}")
        if send_gmail_notification(target, "Jarvis 贵金属行情快报", body):
            print(f"-> {target} 发送成功!")
        else:
            print(f"-> {target} 发送失败!")

if __name__ == "__main__":
    github_action_entry()
