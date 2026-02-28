import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_gmail_notification(to_email, subject, body):
    import socks
    import socket
    # 配置信息
    sender_email = "troiamaribelcl57@gmail.com" 
    app_password = "plqwxidwkwvqlfob"
    
    # 设置 SOCKS5 代理 (Clash/Cloudupup 默认通常支持 7897 的 socks)
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 7897)
    socket.socket = socks.socksocket

    # 创建邮件对象
    message = MIMEMultipart()
    message["From"] = f"Jarvis Monitor <{sender_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    
    message.attach(MIMEText(body, "plain"))
    
    try:
        # 使用代理
        import os
        proxy = "http://127.0.0.1:7897"
        os.environ["http_proxy"] = proxy
        os.environ["https_proxy"] = proxy
        
        # Gmail SMTP 配置
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, message.as_string())
        server.close()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    # 测试发送给 Lore 自己
    test_subject = "Jarvis SaaS - 监控系统启动通知"
    test_body = "报告 Lore，邮件通知系统已成功打通。当前正在为您监测各大行贵金属实时牌价。"
    if send_gmail_notification("chenlong248@gmail.com", test_subject, test_body):
        print("测试邮件已发出，请检查收件箱。")
