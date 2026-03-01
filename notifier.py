
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import socket
from datetime import datetime

def generate_html_report(market_data):
    """
    生成 SaaS 风格的 HTML 行情报表
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 动态生成银行价格表格
    rows = ""
    for item in market_data.get('data', []):
        stale_style = "color: #ff9800;" if item.get('is_stale') else "color: #4caf50;"
        rows += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; font-weight: bold;">{item['bank']}</td>
            <td style="padding: 12px; color: #666;">{item['product']}</td>
            <td style="padding: 12px; text-align: right; color: #d32f2f;">{item['sell']}</td>
            <td style="padding: 12px; text-align: right; color: #388e3c;">{item['buy']}</td>
            <td style="padding: 12px; text-align: right; font-size: 11px; {stale_style}">{item['time']}</td>
        </tr>
        """

    brand_info = ""
    if market_data.get('brand_avg'):
        brand_info = f"<div style='margin-top: 20px; padding: 15px; background: #fff8e1; border-radius: 8px; font-size: 13px;'>当前品牌金饰均价参考: <strong>{market_data['brand_avg']} 元/克</strong></div>"

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #eee;">
            <div style="background: #f59e0b; color: #000; padding: 24px; text-align: center;">
                <h2 style="margin: 0; font-weight: 900; letter-spacing: -1px;">Jarvis <span style="font-style: italic;">Market Alert</span></h2>
                <p style="margin: 8px 0 0; font-size: 12px; font-weight: bold; opacity: 0.8;">{timestamp} 实时行情报表</p>
            </div>
            
            <div style="padding: 24px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="text-align: left; border-bottom: 2px solid #eee;">
                            <th style="padding: 12px; color: #999; font-weight: bold; text-transform: uppercase; font-size: 10px;">银行</th>
                            <th style="padding: 12px; color: #999; font-weight: bold; text-transform: uppercase; font-size: 10px;">品种</th>
                            <th style="padding: 12px; text-align: right; color: #999; font-weight: bold; text-transform: uppercase; font-size: 10px;">卖出(你买)</th>
                            <th style="padding: 12px; text-align: right; color: #999; font-weight: bold; text-transform: uppercase; font-size: 10px;">买入(你卖)</th>
                            <th style="padding: 12px; text-align: right; color: #999; font-weight: bold; text-transform: uppercase; font-size: 10px;">更新</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                
                {brand_info}

                <div style="margin-top: 30px; text-align: center;">
                    <a href="https://github.com/scabc/jarvis-precious-metals-saas" style="background: #000; color: #fff; padding: 12px 32px; border-radius: 12px; text-decoration: none; font-weight: bold; font-size: 14px;">进入监控大屏</a>
                </div>
            </div>
            
            <div style="padding: 20px; text-align: center; background: #fdfdfd; border-top: 1px solid #eee; font-size: 10px; color: #aaa;">
                本报告由 Jarvis 贵金属 SaaS 自动生成。数据源自多源聚合，仅供参考，不作为投资建议。
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_market_report(to_email, market_data):
    subject = f"🔔 Jarvis 贵金属行情快报 | {datetime.now().strftime('%H:%M')}"
    body = generate_html_report(market_data)
    
    sender_email = os.environ.get("SENDER_EMAIL", "troiamaribelcl57@gmail.com")
    app_password = os.environ.get("APP_PASSWORD", "plqwxidwkwvqlfob")
    
    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    if not is_github:
        try:
            import socks
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(("127.0.0.1", 7897)) == 0:
                    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 7897)
                    socket.socket = socks.socksocket
                    print("已启用本地 SOCKS5 代理")
        except Exception: pass

    message = MIMEMultipart()
    message["From"] = f"Jarvis Monitor <{sender_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, message.as_string())
        server.close()
        print(f"行情报告已成功发送至: {to_email}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    # 测试数据模拟
    test_data = {
        "data": [
            {"bank": "工商银行", "product": "积存金", "buy": 1142.48, "sell": 1145.5, "time": "2026-03-02 01:20", "is_stale": False},
            {"bank": "农业银行", "product": "存金通", "buy": 1145.0, "sell": 1147.8, "time": "2026-02-28 00:42", "is_stale": True}
        ],
        "brand_avg": 732.5
    }
    send_market_report("troiamaribelcl57@gmail.com", test_data)
