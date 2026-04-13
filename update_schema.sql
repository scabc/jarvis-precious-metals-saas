-- ==========================================
-- JARVIS 贵金属 SaaS - 数据库增量迁移
-- （已有旧表结构的用户运行此文件）
-- ==========================================

-- 1. 如果 global_settings 表不存在则创建
CREATE TABLE IF NOT EXISTS public.global_settings (
  id integer PRIMARY KEY DEFAULT 1,
  reference_prices jsonb DEFAULT '{}'::jsonb,
  last_updated timestamptz DEFAULT now()
);

INSERT INTO public.global_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- 2. 给 subscriptions 补缺失字段
ALTER TABLE public.subscriptions
  ADD COLUMN IF NOT EXISTS expires_at timestamptz DEFAULT (now() + interval '7 days'),
  ADD COLUMN IF NOT EXISTS banks text[] DEFAULT '{"中国银行"}' NOT NULL;

-- 3. 恢复 RLS（如需重新开启）
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.global_settings ENABLE ROW LEVEL SECURITY;

-- 4. 重建 RLS 策略（先删后建避免冲突）
DROP POLICY IF EXISTS "anon_can_insert_subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "users_read_own_subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "users_update_own_subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "users_delete_own_subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "service_can_read_subscriptions" ON public.subscriptions;
DROP POLICY IF EXISTS "service_can_update_subscriptions" ON public.subscriptions;
DROP POLICY IF EXISTS "anyone_can_read_global_settings" ON public.global_settings;
DROP POLICY IF EXISTS "service_can_write_global_settings" ON public.global_settings;

CREATE POLICY "anon_can_insert_subscription" ON public.subscriptions FOR INSERT WITH CHECK (true);
CREATE POLICY "users_read_own_subscription" ON public.subscriptions FOR SELECT USING (auth.uid() = if_user_id);
CREATE POLICY "users_update_own_subscription" ON public.subscriptions FOR UPDATE USING (auth.uid() = if_user_id);
CREATE POLICY "users_delete_own_subscription" ON public.subscriptions FOR DELETE USING (auth.uid() = if_user_id);
CREATE POLICY "service_can_read_subscriptions" ON public.subscriptions FOR SELECT USING (true);
CREATE POLICY "service_can_update_subscriptions" ON public.subscriptions FOR UPDATE USING (true);
CREATE POLICY "anyone_can_read_global_settings" ON public.global_settings FOR SELECT USING (true);
CREATE POLICY "service_can_write_global_settings" ON public.global_settings FOR ALL USING (true);

-- 5. 自动创建订阅（用户注册后自动在 subscriptions 插入记录）
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.subscriptions (if_user_id, email, plan, expires_at)
  VALUES (new.id, new.email, 'FREE', now() + interval '7 days')
  ON CONFLICT (if_user_id) DO NOTHING;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
