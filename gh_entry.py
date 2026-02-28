import os
import sys
import json
from data_engine import get_aggregated_data
from notifier import send_gmail_notification

def github_action_entry():
    # 从 GitHub Secrets 读取
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("APP_PASSWORD")
    target = os.environ.get("TARGET_EMAIL")
    
    if not all([sender, password, target]):
        print(f"错误: 环境变量缺失! SENDER: {bool(sender)}, PWD: {bool(password)}, TARGET: {bool(target)}")
        return

    print("正在获取实时贵金属行情...")
    data = get_aggregated_data()
    
    if data:
        body = "【Jarvis SaaS - 自动巡检报告】\n\n"
        for item in data:
            name = item.get("f14", "未知品种")
            price = item.get("f2", "-")
            change = item.get("f3", "0.00")
            body += f"- {name}: {price} (涨跌: {change}%)\n"
        
        body += "\n--- 监控结束 ---"
        
        print(f"正在发送至: {target}")
        if send_gmail_notification(target, "Jarvis 贵金属行情快报", body):
            print("邮件发送成功!")
        else:
            print("邮件发送失败!")
    else:
        print("数据抓取失败，跳过此次运行。")

if __name__ == "__main__":
    github_action_entry()
