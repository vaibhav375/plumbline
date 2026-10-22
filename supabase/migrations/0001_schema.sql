-- Plumbline schema. Every tenant table carries org_id so RLS is a single column check.
create extension if not exists pgcrypto with schema extensions;

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table public.profiles (
  user_id uuid primary key references auth.users on delete cascade,
  org_id uuid not null references public.organizations,
  display_name text not null,
  role text not null check (role in
    ('creator','external_creator','reviewer','compliance','accessibility','brand_owner','auditor'))
);

-- Caller's org and role. security definer so policies on profiles don't recurse.
create function public.current_org() returns uuid
language sql stable security definer set search_path = '' as $$
  select org_id from public.profiles where user_id = auth.uid()
$$;

create function public.app_role() returns text
language sql stable security definer set search_path = '' as $$
  select role from public.profiles where user_id = auth.uid()
$$;

create table public.rules (
  org_id uuid not null default public.current_org() references public.organizations,
  id text not null,
  title text not null,
  category text not null check (category in
    ('claim','tone','terminology','accessibility','visual','confidential','required','style')),
  cls text not null check (cls in ('A','B','C')),
  check_type text not null check (check_type in
    ('pattern','word_list','count','required','contrast','alt_text','ai_rule')),
  params jsonb not null default '{}',
  severity text not null check (severity in ('blocking','major','minor')),
  tier text not null check (tier in ('mandatory','brand')),
  maturity text not null default 'advisory' check (maturity in ('advisory','blocking')),
  examples_good text[] not null default '{}',
  examples_bad text[] not null default '{}',
  source_ref text not null,
  owner_function text not null check (owner_function in ('brand','compliance','accessibility')),
  active boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key (org_id, id)
);

create table public.facts (
  org_id uuid not null default public.current_org() references public.organizations,
  id text not null,
  statement text not null,
  value double precision,
  unit text,
  product text,
  market text not null,
  population text,
  duration text,
  owner text not null,
  valid_from date not null,
  valid_until date,
  confidentiality text not null default 'public'
    check (confidentiality in ('public','internal','confidential','embargoed')),
  embargo_until date,
  verified boolean not null default false,
  aliases text[] not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (org_id, id)
);

create table public.approved_wordings (
  org_id uuid not null default public.current_org() references public.organizations,
  id text not null,
  fact_id text not null,
  market text not null,
  channel text not null,
  text text not null,
  disclaimer text,
  primary key (org_id, id),
  foreign key (org_id, fact_id) references public.facts (org_id, id)
);

create table public.terms (
  org_id uuid not null default public.current_org() references public.organizations,
  id text not null,
  preferred text not null,
  variants text[] not null default '{}',
  primary key (org_id, id)
);

create table public.contents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  title text not null,
  channel text not null,
  region text not null,
  origin text not null,
  created_by uuid not null default auth.uid() references auth.users,
  created_at timestamptz not null default now()
);

create table public.versions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  content_id uuid not null references public.contents on delete cascade,
  n int not null,
  text text not null,
  doc_json jsonb,
  intent_json jsonb,
  private boolean not null default false,
  status text not null default 'precheck' check (status in
    ('precheck','submitted','in_review','changes_requested','approved','published','withdrawn','recalled')),
  canonical_hash text,
  created_by uuid not null default auth.uid() references auth.users,
  created_at timestamptz not null default now(),
  unique (content_id, n)
);

create table public.check_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  version_id uuid not null references public.versions on delete cascade,
  report_json jsonb not null,
  rulebook_version text not null,
  models_used text[] not null default '{}',
  ms_code int,
  ms_total int,
  created_at timestamptz not null default now()
);

create table public.findings (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  run_id uuid not null references public.check_runs on delete cascade,
  rule_id text,
  fact_id text,
  category text not null,
  severity text not null,
  advisory boolean not null,
  quote text not null,
  span_start int,
  span_end int,
  payload_json jsonb not null default '{}'
);

create table public.decisions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  finding_id uuid not null references public.findings on delete cascade,
  actor uuid not null default auth.uid() references auth.users,
  action text not null check (action in ('accept','edit','dismiss','uphold','overrule')),
  reason text,
  edited_text text,
  at timestamptz not null default now()
);

create table public.approvals (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  version_id uuid not null references public.versions on delete cascade,
  actor uuid not null default auth.uid() references auth.users,
  stage text not null check (stage in ('first','second','compliance','accessibility')),
  outcome text not null check (outcome in ('approve','request_changes')),
  reason text,
  at timestamptz not null default now()
);

create table public.comments (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null default public.current_org() references public.organizations,
  version_id uuid not null references public.versions on delete cascade,
  author uuid not null default auth.uid() references auth.users,
  body text not null,
  span_start int,
  span_end int,
  created_at timestamptz not null default now()
);

create table public.egress_events (
  id bigserial primary key,
  org_id uuid not null default public.current_org() references public.organizations,
  run_id uuid references public.check_runs on delete set null,
  provider text not null,
  model text not null,
  purpose text not null,
  chars_sent int not null,
  redactions int not null default 0,
  masked int not null default 0,
  status text not null,
  ms int,
  at timestamptz not null default now()
);

create table public.eval_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations,
  name text not null,
  metrics_json jsonb not null,
  created_at timestamptz not null default now()
);

create table public.audit_events (
  id bigserial primary key,
  org_id uuid not null references public.organizations,
  actor uuid,
  kind text not null,
  entity text not null,
  entity_id text not null,
  payload jsonb not null,
  prev_hash text not null,
  hash text not null unique,
  at timestamptz not null
);

create index on public.versions (content_id);
create index on public.check_runs (version_id);
create index on public.findings (run_id);
create index on public.decisions (finding_id);
create index on public.approvals (version_id);
create index on public.audit_events (org_id, id);
