import time
import json
import os
from data_engine import get_aggregated_data
from notifier import send_gmail_notification

# 模拟数据库存储历史价格，用于计算最高/最低
HISTORY_FILE = "projects/jarvis-pm-saas/price_history.json"

def update_history(current_data):
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    
    now = time.time()
    for item in current_data:
        code = item["f12"]
        name = item["f14"]
        price = item["f2"]
        
        if code not in history:
            history[code] = {"name": name, "prices": []}
        
        # 记录价格和时间戳
        history[code]["prices"].append({"p": price, "t": now})
        
        # 只保留最近 24 小时的数据 (24 * 3600 秒)
        history[code]["prices"] = [x for x in history[code]["prices"] if now - x["t"] <= 86400]
        
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)
    return history

def analyze_and_notify(history):
    target_email = "troiamaribelcl57@gmail.com"
    VOLATILITY_THRESHOLD = 0.003  # 0.3% 的波动阈值
    
    # 记录上次发送告警的价格，避免重复轰炸
    if not hasattr(analyze_and_notify, "last_alert_prices"):
        analyze_and_notify.last_alert_prices = {}

    for code, info in history.items():
        if len(info["prices"]) < 2: continue
        
        current_price = info["prices"][-1]["p"]
        all_prices = [x["p"] for x in info["prices"]]
        high_24h = max(all_prices)
        low_24h = min(all_prices)
        
        # 获取上次告警时的价格，如果没有，则取 24 小时内的第一个价格
        last_price = analyze_and_notify.last_alert_prices.get(code, info["prices"][0]["p"])
        
        # 计算当前相对于上次告警价格的波动率
        change_ratio = abs(current_price - last_price) / last_price
        
        if change_ratio >= VOLATILITY_THRESHOLD:
            direction = "上涨" if current_price > last_price else "下跌"
            diff_from_low = current_price - low_24h
            diff_from_high = current_price - high_24h
            
            subject = f"📢 波动预警：{info['name']} 快速{direction} {change_ratio:.2%}"
            body = (
                f"【Jarvis 智能监控 - 实时波动汇报】\n\n"
                f"品种：{info['name']}\n"
                f"当前价格：{current_price}\n"
                f"较上次提醒：{direction} {change_ratio:.2%}\n"
                f"--------------------------\n"
                f"24h 最高价：{high_24h} (距最高：{diff_from_high:.2f})\n"
                f"24h 最低价：{low_24h} (距最低：+{diff_from_low:.2f})\n\n"
                f"监控建议：市场波动加剧，请注意仓位控制。"
            )
            
            print(f"检测到 {info['name']} 剧烈波动 ({change_ratio:.2%})，正在推送...")
            if send_gmail_notification(target_email, subject, body):
                # 发送成功后更新上次告警价格
                analyze_and_notify.last_alert_prices[code] = current_price

def main():
    print("Jarvis 贵金属监控服务已启动...")
    while True:
        try:
            data = get_aggregated_data()
            if data and not isinstance(data, dict):
                history = update_history(data)
                analyze_and_notify(history)
            else:
                print("获取数据失败，重试中...")
        except Exception as e:
            print(f"运行异常: {e}")
        
        # 演示环境每 5 分钟检查一次，实际可调
        time.sleep(300)

if __name__ == "__main__":
    main()
