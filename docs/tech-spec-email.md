# 邮件发送模块方案

## 1. 方案选择
- **方案 A**: 使用 NodeMailer + SMTP (如 163, Gmail, 或阿里云邮件推送)。
- **方案 B**: 使用专业邮件 API (如 Resend 或 SendGrid)。
*建议首期使用 NodeMailer + SMTP，成本最低且易于控制。*

## 2. 关键代码片段逻辑 (Pseudo)
```javascript
async function sendAlert(to, subject, content) {
  // 1. 配置 Transporter
  // 2. 构造邮件 HTML (包含实时价格波动表)
  // 3. 执行发送并记录日志
}
```
