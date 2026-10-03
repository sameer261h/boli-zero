-- Execute once through your private Supabase SQL editor.
create table if not exists public.boli_runtime (
  id integer primary key check (id=1),
  payload jsonb not null default '{"conversations":{},"files":{}}'::jsonb
);
insert into public.boli_runtime(id) values(1) on conflict do nothing;
create table if not exists public.boli_contributions (
  id text primary key,
  token_hash text not null,
  created timestamptz not null default now(),
  audio bytea not null,
  metadata jsonb not null
);
create table if not exists public.boli_reviews (
  id text primary key,
  created timestamptz not null default now(),
  conversation_id text not null,
  turn_id text not null,
  audio bytea,
  recognized_text text,
  error_code text,
  recognition jsonb,
  reply_text text,
  understood boolean,
  reply jsonb
);
alter table public.boli_runtime enable row level security;
alter table public.boli_contributions enable row level security;
alter table public.boli_reviews enable row level security;
revoke all on public.boli_runtime, public.boli_contributions, public.boli_reviews from anon, authenticated;
-- Server uses a private database connection. No browser database access.
-- Supabase Cron removes expired contributions even without visitor traffic.
create extension if not exists pg_cron;
select cron.schedule('boli-review-retention', '5 * * * *', $$delete from public.boli_reviews where created <= now() - interval '30 days'$$);
select cron.schedule('boli-retention', '0 * * * *', $$
  delete from public.boli_contributions where created <= now() - interval '30 days';
  with alive as (
    select coalesce(jsonb_object_agg(c.key,c.value), '{}'::jsonb) as conversations
    from public.boli_runtime r, jsonb_each(r.payload->'conversations') c
    where r.id=1 and (c.value->>'created')::double precision > extract(epoch from now()) - 3600
  ), retained as (
    select coalesce(jsonb_object_agg(f.key,f.value), '{}'::jsonb) as files
    from public.boli_runtime r, alive a, jsonb_each(r.payload->'files') f
    where r.id=1 and (f.key in ('gnani.jsonl', 'claude.jsonl') or exists (
      select 1 from jsonb_each(a.conversations) c, jsonb_each(c.value->'turns') t
      where t.value->>'audio_id' = split_part(split_part(f.key, '/', 4), '.', 1)
    ))
  )
  update public.boli_runtime set payload=jsonb_set(jsonb_set(payload, '{conversations}', a.conversations), '{files}', f.files)
  from alive a, retained f where id=1;
$$);
