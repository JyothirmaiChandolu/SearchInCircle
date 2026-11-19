-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.
create table if not exists ratings (
  run_id   text primary key,
  saved_at timestamptz not null default now(),
  data     jsonb not null
);
-- The app uses the service key, which bypasses row security; this keeps the
-- table closed to anyone using the public (anon) key.
alter table ratings enable row level security;

-- Run log for the spend limits (runs per hour, daily spend cap). Also run this.
create table if not exists run_log (
  id     bigint generated always as identity primary key,
  at     timestamptz not null default now(),
  tester text,
  ip     text,
  cost   numeric not null default 0,
  design text
);
create index if not exists run_log_at on run_log (at desc);
alter table run_log enable row level security;
