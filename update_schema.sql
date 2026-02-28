-- 1. 为订阅表增加用户关联字段
alter table public.subscriptions 
add column if_user_id uuid references auth.users(id);

-- 2. 开启更严谨的安全策略：用户只能看到和修改自己的订阅
alter table public.subscriptions enable row level security;

-- 允许登录用户插入自己的数据
create policy "Users can insert their own subscription"
on public.subscriptions for insert
with check (auth.uid() = if_user_id);

-- 允许用户查看自己的订阅
create policy "Users can view their own subscription"
on public.subscriptions for select
using (auth.uid() = if_user_id);

-- 允许用户更新自己的订阅
create policy "Users can update their own subscription"
on public.subscriptions for update
using (auth.uid() = if_user_id);

-- 允许后台服务 (service_role) 继续读取所有数据用于发信
create policy "Service role can do everything"
on public.subscriptions for all
using (true)
with check (true);
