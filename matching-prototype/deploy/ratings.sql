-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.
create table if not exists ratings (
  run_id   text primary key,
  saved_at timestamptz not null default now(),
  data     jsonb not null
);
-- The app uses the service key, which bypasses row security; this keeps the
-- table closed to anyone using the public (anon) key.
alter table ratings enable row level security;
