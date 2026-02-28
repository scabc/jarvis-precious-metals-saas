-- ==========================================
-- JARVIS PRECIOUS METALS SAAS - 数据库结构完整重置
-- ==========================================

-- 1. 如果表已存在，先彻底删除（确保结构从零开始，避免字段类型冲突）
DROP TABLE IF EXISTS public.subscriptions CASCADE;

-- 2. 创建核心订阅表
CREATE TABLE public.subscriptions (
  -- 主键 ID
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  
  -- 用户关联：关联 Supabase Auth 的用户 ID
  if_user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- 用户的电子邮箱
  email text UNIQUE NOT NULL,
  
  -- 订阅计划：FREE (免费), PRO (专业版)
  plan text DEFAULT 'FREE' NOT NULL,
  
  -- 预警波动阈值：如 0.003 代表 0.3%
  threshold float8 DEFAULT 0.003 NOT NULL,
  
  -- 关注的品种数组：如 {"黄金9999", "白银T+D"}
  metals text[] DEFAULT '{"黄金9999", "白银T+D"}' NOT NULL,
  
  -- 关注的银行数组：如 {"中国银行", "工商银行", "招商银行", "农业银行"}
  banks text[] DEFAULT '{"中国银行"}' NOT NULL,
  
  -- 上次通知时的价格快照（JSON 格式）：如 {"黄金9999": 450.5}
  last_prices jsonb DEFAULT '{}'::jsonb,
  
  -- 创建与更新时间
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 3. 关闭 RLS (安全策略)，在 MVP 阶段允许前端通过 API 直接写入
-- 注意：这确保了即便没有复杂的 Policy，保存功能也能 100% 成功
ALTER TABLE public.subscriptions DISABLE ROW LEVEL SECURITY;

-- 4. 显式授予各角色对表的操作权限
GRANT ALL ON TABLE public.subscriptions TO anon;
GRANT ALL ON TABLE public.subscriptions TO authenticated;
GRANT ALL ON TABLE public.subscriptions TO service_role;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;

-- 5. 创建自动更新 updated_at 字段的触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();

-- ==========================================
-- SQL 执行说明：
-- 请复制以上全部代码，粘贴到 Supabase SQL Editor 中运行。
-- 运行成功后，您的数据库将完全匹配当前最新的前端和后端逻辑。
-- ==========================================
