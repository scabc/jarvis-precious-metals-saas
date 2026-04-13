
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logger = logging.getLogger(__name__)
import socket
from datetime import datetime

def generate_html_report(market_data):
    """生成 SaaS 风格的 HTML 行情报表"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = ""
    # 兼容处理 list 或 dict
    items = market_data.get('data', []) if isinstance(market_data, dict) else market_data
    
    for item in items:
        # 字段兼容性处理
        bank = item.get('bank') or item.get('f14') or "银行"
        product = item.get('product') or "积存金"
        buy = item.get('buy') or item.get('f2') or "0.00"
        sell = item.get('sell') or "0.00"
        time_str = item.get('time') or datetime.now().strftime('%H:%M')
        
        rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; font-weight: bold;">{bank}</td>
            <td style="padding: 12px; color: #666;">{product}</td>
            <td style="padding: 12px; text-align: right; color: #d32f2f;">{sell}</td>
            <td style="padding: 12px; text-align: right; color: #388e3c;">{buy}</td>
            <td style="padding: 12px; text-align: right; font-size: 11px; color: #999;">{time_str}</td>
        </tr>
        """

    html = f"""
    <html>
    <body style="font-family: sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; border: 1px solid #eee; overflow: hidden;">
            <div style="background: #f59e0b; color: #000; padding: 24px; text-align: center;">
                <h2 style="margin: 0;">Jarvis Market Alert</h2>
                <p style="margin: 5px 0 0; font-size: 12px;">{timestamp} 实时行情报表</p>
            </div>
            <div style="padding: 24px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="text-align: left; border-bottom: 2px solid #eee; color: #999; font-size: 10px;">
                            <th style="padding: 12px;">银行/品种</th>
                            <th style="padding: 12px;">产品</th>
                            <th style="padding: 12px; text-align: right;">卖出</th>
                            <th style="padding: 12px; text-align: right;">买入</th>
                            <th style="padding: 12px; text-align: right;">更新</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <div style="margin-top: 30px; text-align: center;">
                    <a href="https://scabc.github.io/jarvis-precious-metals-saas/" style="background: #000; color: #fff; padding: 12px 32px; border-radius: 12px; text-decoration: none; font-weight: bold;">查看实时大屏</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_gmail_notification(to_email, subject, body_content):
    """通用 Gmail 通知发送函数"""
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    if not sender_email or not app_password:
        print("Gmail credentials not configured. Set SENDER_EMAIL and APP_PASSWORD environment variables.")
        return False
    
    # 检测是否在 GitHub Actions 环境
    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    
    # 仅在非 GitHub 环境尝试代理
    if not is_github:
        try:
            import socks
            for port in [7897, 7890]:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", port)
                        socket.socket = socks.socksocket
                        break
        except Exception as e:
            logger.warning(f"[proxy_setup] failed: {e}")

    message = MIMEMultipart()
    message["From"] = f"Jarvis Monitor <{sender_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    
    # 智能判断 body 是 HTML 还是纯文本
    if "<div" in str(body_content) or "<html" in str(body_content):
        message.attach(MIMEText(body_content, "html"))
    else:
        # 如果是字符串，则尝试生成报表
        if isinstance(body_content, (list, dict)):
            html = generate_html_report(body_content)
            message.attach(MIMEText(html, "html"))
        else:
            message.attach(MIMEText(str(body_content), "plain"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"通知邮件已发送至: {to_email}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

# 别名兼容
send_market_report = send_gmail_notification

if __name__ == "__main__":
    import os
    test_email = os.environ.get("TEST_EMAIL")
    if test_email:
        send_gmail_notification(test_email, "Jarvis Test", "这是一封测试邮件")
    else:
        print("请设置 TEST_EMAIL 环境变量再运行测试")
