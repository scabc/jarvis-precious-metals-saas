import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import socket

def send_gmail_notification(to_email, subject, body):
    # 优先从环境变量读取，如果没有则使用硬编码（本地测试用）
    sender_email = os.environ.get("SENDER_EMAIL", "troiamaribelcl57@gmail.com")
    app_password = os.environ.get("APP_PASSWORD", "plqwxidwkwvqlfob")
    
    # 只有在本地环境（检测是否存在代理端口）时才启用 SOCKS5
    # GitHub Actions 不需要代理即可访问 Gmail
    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    
    if not is_github:
        try:
            import socks
            # 测试本地 7897 端口是否开启（判断是否在本地运行）
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(("127.0.0.1", 7897)) == 0:
                    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 7897)
                    socket.socket = socks.socksocket
                    print("已启用本地 SOCKS5 代理")
        except Exception:
            print("未检测到本地代理，尝试直连...")

    # 创建邮件对象
    message = MIMEMultipart()
    message["From"] = f"Jarvis Monitor <{sender_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, message.as_string())
        server.close()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

if __name__ == "__main__":
    # 本地测试
    send_gmail_notification("troiamaribelcl57@gmail.com", "本地测试", "测试自适应通知系统")
