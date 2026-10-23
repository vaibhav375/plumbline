-- Reports are cached by a key over everything that can change them (text, org context, models,
-- code, viewer scope, intent, date). RLS on check_runs still decides who may reuse a cached run.
alter table public.check_runs add column cache_key text;
create index on public.check_runs (cache_key);
