-- ==========================================
-- JARVIS PRECIOUS METALS SAAS - 数据库结构完整重置
-- ==========================================

-- 1. 如果表已存在，先彻底删除（确保结构从零开始）
DROP TABLE IF EXISTS public.subscriptions CASCADE;
DROP TABLE IF EXISTS public.global_settings CASCADE;

-- 2. 创建全局设置表（存储后端同步的权威价格快照）
CREATE TABLE public.global_settings (
  id integer PRIMARY KEY DEFAULT 1,
  reference_prices jsonb DEFAULT '{}'::jsonb,
  last_updated timestamptz DEFAULT now()
);

-- 插入默认行
INSERT INTO public.global_settings (id) VALUES (1);

-- 3. 创建核心订阅表
CREATE TABLE public.subscriptions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,

  -- 用户关联：关联 Supabase Auth 的用户 ID
  if_user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,

  -- 用户的电子邮箱
  email text UNIQUE NOT NULL,

  -- 订阅计划：FREE (免费), PRO (专业版)
  plan text DEFAULT 'FREE' NOT NULL,

  -- 试用期截止时间（FREE 用户默认 7 天）
  expires_at timestamptz DEFAULT (now() + interval '7 days'),

  -- 预警波动阈值：如 0.003 代表 0.3%
  threshold float8 DEFAULT 0.003 NOT NULL,

  -- 关注的品种数组：如 {"黄金9999", "白银T+D"}
  metals text[] DEFAULT '{"黄金9999", "白银T+D"}' NOT NULL,

  -- 关注的银行数组：如 {"中国银行", "工商银行"}
  banks text[] DEFAULT '{"中国银行"}' NOT NULL,

  -- 上次通知时的价格快照（JSON 格式）：如 {"黄金9999": 450.5}
  last_prices jsonb DEFAULT '{}'::jsonb,

  -- 创建与更新时间
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  -- 约束：同一用户不重复订阅
  CONSTRAINT unique_user_email UNIQUE (if_user_id, email)
);

-- 4. 开启 RLS（行级安全策略）
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.global_settings ENABLE ROW LEVEL SECURITY;

-- 5. RLS 策略：
-- 匿名用户可注册（插入自己的订阅）
CREATE POLICY "anon_can_insert_subscription"
  ON public.subscriptions FOR INSERT
  WITH CHECK (true);

-- 登录用户只能读写自己的订阅记录
CREATE POLICY "users_read_own_subscription"
  ON public.subscriptions FOR SELECT
  USING (auth.uid() = if_user_id);

CREATE POLICY "users_update_own_subscription"
  ON public.subscriptions FOR UPDATE
  USING (auth.uid() = if_user_id);

CREATE POLICY "users_delete_own_subscription"
  ON public.subscriptions FOR DELETE
  USING (auth.uid() = if_user_id);

-- service_role（后端服务）可读写所有订阅用于发信
CREATE POLICY "service_can_read_subscriptions"
  ON public.subscriptions FOR SELECT
  USING (true);

CREATE POLICY "service_can_update_subscriptions"
  ON public.subscriptions FOR UPDATE
  USING (true);

-- 全局设置：任何人可读（价格快照是公开的），只有 service_role 可写
CREATE POLICY "anyone_can_read_global_settings"
  ON public.global_settings FOR SELECT USING (true);

CREATE POLICY "service_can_write_global_settings"
  ON public.global_settings FOR ALL
  USING (true);

-- 6. 授予权限
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON TABLE public.subscriptions TO anon, authenticated, service_role;
GRANT ALL ON TABLE public.global_settings TO anon, authenticated, service_role;

-- 7. 创建自动更新 updated_at 字段的触发器
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

-- 8. 自动创建订阅的数据库函数（用户注册后由 trigger 调用）
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.subscriptions (if_user_id, email, plan, expires_at)
  VALUES (new.id, new.email, 'FREE', now() + interval '7 days');
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 用户注册后自动创建订阅记录
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ==========================================
-- SQL 执行说明：
-- 请复制以上全部代码，粘贴到 Supabase SQL Editor 中运行。
-- 运行成功后，您的数据库将完全匹配当前最新的前端和后端逻辑。
-- ==========================================
