# Jarvis Precious Metal Smart Monitoring SaaS

智能贵金属监控 SaaS 系统，为专业投资者提供实时价格监测、智能预警及市场分析。

## 核心功能 (MVP)

1. **实时行情推送**：监控金、银、铂、钯的全球市场价格
2. **智能预警系统**：支持价格阈值告警、波动率告警，多渠道实时推送
3. **多端触达**：通过 Gmail 等渠道实时推送通知
4. **可视化面板**：历史趋势分析及权威价格参考

## 技术架构

```
前端:  index.html / account.html  (静态站，托管于 GitHub Pages)
后端:  gh_entry.py  (GitHub Actions 定时爬虫 + 邮件推送)
数据:  Supabase (PostgreSQL + Auth)
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `index.html` | 主监控大屏（实时价格 + 图表 + 订阅表单）|
| `account.html` | 用户中心（订阅状态 + 预警阈值配置）|
| `data_engine_v3.py` | **核心数据引擎**：聚合 11 家银行积存金实时牌价 |
| `gh_entry.py` | **GitHub Actions 定时入口**：同步权威价格 + 触发邮件预警 |
| `notifier.py` | Gmail SMTP 通知，支持 SOCKS5 代理 |
| `full_schema_reset.sql` | Supabase 数据库完整建表脚本 |
| `update_schema.sql` | 增量迁移脚本（已有旧表用户使用）|
| `.env.example` | 环境变量模板 |

## 快速部署

### 1. 配置 Supabase

1. 在 [Supabase](https://supabase.com) 创建项目
2. 在 **SQL Editor** 中运行 `full_schema_reset.sql`
3. 获取 `SUPABASE_URL` 和 `SUPABASE_SERVICE_KEY`

### 2. 配置 GitHub Secrets

在 GitHub 仓库 → **Settings → Secrets and variables → Actions** 中添加：

| Secret | 说明 |
|--------|------|
| `SENDER_EMAIL` | Gmail 发件地址 |
| `APP_PASSWORD` | Gmail 16位应用密码 |
| `SUPABASE_URL` | Supabase 项目地址 |
| `SUPABASE_SERVICE_KEY` | Supabase service_role 密钥 |
| `JISU_KEY` | [极速数据](https://www.jisuapi.com) API Key（可选） |
| `ALAPI_TOKEN` | [ALAPI](https://v3.alapi.cn) Token（可选，用于品牌金饰价）|

### 3. 配置 GitHub Actions

GitHub Actions 已配置在 `.github/workflows/jarvis_global_sync.yml`，定时每 2 小时运行一次商业数据同步 + 邮件预警。

### 4. 部署前端

推送到 GitHub Pages：
```bash
git push origin main
# 等待 GitHub Pages 自动部署（约 2 分钟）
```

## ⚠️ 安全说明

- **Supabase Anon Key** 暴露在前端是**设计如此**（Supabase 的 Row Level Security 控制数据访问），但前端匿名 key 权限已被 RLS 严格限制，用户只能操作自己的订阅记录
- **所有业务密钥**（Gmail App Password、Supabase Service Key、JISU_KEY 等）**绝不暴露在前端**，仅存储于 GitHub Secrets
- **ALAPI_TOKEN** 等可选密钥通过环境变量注入，不在前端流通

## 数据库 Schema

详见 `full_schema_reset.sql`，核心表：

- `subscriptions` — 用户订阅（含 RLS 策略）
- `global_settings` — 后端权威价格快照，前端断流兜底

## 开发

```bash
# 本地测试数据引擎
python data_engine_v3.py

# 本地测试邮件发送（需先配置 .env）
python gh_entry.py
```
