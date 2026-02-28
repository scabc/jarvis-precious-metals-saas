# Jarvis Precious Metal Smart Monitoring SaaS

智能贵金属监控 SaaS 系统，旨在为用户提供实时价格监测、智能预警及市场分析。

## 核心功能 (MVP)
1. **实时行情推送**：监控金、银、铂、钯的全球市场价格。
2. **智能预警系统**：支持价格阈值告警、波动率告警。
3. **多端触达**：通过 Telegram、飞书等渠道实时推送通知。
4. **可视化面板**：历史趋势分析及资产价值估算。

## 技术栈建议
- **Frontend**: Next.js 15 (App Router) + Tailwind CSS v4 + Shadcn/UI
- **Backend**: Node.js (Edge Functions) / Python (Data Crawler)
- **Database**: Supabase (PostgreSQL + Auth)
- **Monitoring**: OpenClaw Cron + Sub-agents

## 阶段规划
- [ ] Phase 1: 监控核心引擎开发 (实现基础行情抓取与存储)
- [ ] Phase 2: 预警逻辑与多渠道通知集成
- [ ] Phase 3: SaaS 仪表盘界面设计与实现
- [ ] Phase 4: 用户认证与多租户支持
