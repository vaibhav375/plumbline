-- Round 3, improvement 2: per-brand chat checks and the publish gate.
-- Same pattern as 0006: tables nobody can read through the API (row-level security on, no policies,
-- no grants), reached only by security-definer functions that only plumbline_checker may call.
-- Codes and keys are stored as SHA-256 hashes; the plain value is shown once, in the app.

-- A brand owner creates a one-time code; a chat address redeems it to link itself to the org.
create table public.agent_link_codes (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations on delete cascade,
  code_hash text not null unique,
  created_by uuid not null references auth.users on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);

create table public.agent_links (
  agent_address text primary key,
  org_id uuid not null references public.organizations on delete cascade,
  linked_by uuid references auth.users on delete set null,
  linked_at timestamptz not null default now()
);

-- A key a scheduling or CMS tool uses to ask the publish gate. Belongs to the organisation.
create table public.gate_keys (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations on delete cascade,
  key_hash text not null unique,
  label text not null,
  created_by uuid not null references auth.users on delete cascade,
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Every gate answer, so the brand owner can see what tools asked and what they were told.
create table public.gate_calls (
  id bigserial primary key,
  org_id uuid not null references public.organizations on delete cascade,
  version_id uuid references public.versions on delete set null,
  decision text not null check (decision in ('go', 'not_yet')),
  reasons text[] not null default '{}',
  at timestamptz not null default now()
);

do $$
declare t text;
begin
  foreach t in array array['agent_link_codes', 'agent_links', 'gate_keys', 'gate_calls'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;

-- ---- linking ----------------------------------------------------------------------------------

create function public.agent_make_code(p_org uuid, p_by uuid, p_hash text, p_minutes int)
returns timestamptz language sql security definer set search_path = '' as $$
  insert into public.agent_link_codes (org_id, created_by, code_hash, expires_at)
  values (p_org, p_by, p_hash, now() + make_interval(mins => p_minutes))
  returning expires_at
$$;

-- Single use and atomic: two redemptions of one code can't both succeed.
create function public.agent_redeem_code(p_hash text, p_address text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_org uuid; v_by uuid; v_name text;
begin
  update public.agent_link_codes set used_at = now()
  where code_hash = p_hash and used_at is null and expires_at > now()
  returning org_id, created_by into v_org, v_by;
  if v_org is null then return null; end if;
  insert into public.agent_links (agent_address, org_id, linked_by)
  values (p_address, v_org, v_by)
  on conflict (agent_address) do update
    set org_id = excluded.org_id, linked_by = excluded.linked_by, linked_at = now();
  select name into v_name from public.organizations where id = v_org;
  return jsonb_build_object('org_id', v_org, 'org_name', v_name);
end $$;

create function public.agent_link_for(p_address text)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('org_id', l.org_id, 'org_name', o.name)
  from public.agent_links l join public.organizations o on o.id = l.org_id
  where l.agent_address = p_address
$$;

create function public.agent_unlink(p_address text, p_org uuid default null)
returns int language sql security definer set search_path = '' as $$
  with d as (
    delete from public.agent_links
    where agent_address = p_address and (p_org is null or org_id = p_org) returning 1)
  select count(*)::int from d
$$;

create function public.agent_links_list(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object('address', agent_address, 'linked_at', linked_at)
                            order by linked_at desc), '[]'::jsonb)
  from public.agent_links where org_id = p_org
$$;

create function public.agent_codes_open(p_org uuid)
returns int language sql stable security definer set search_path = '' as $$
  select count(*)::int from public.agent_link_codes
  where org_id = p_org and used_at is null and expires_at > now()
$$;

-- What an agency writer of this org may see (the same as their row-level-security view): active
-- rules, terms, facts that are not confidential or embargoed, and the wordings of those facts.
-- Confidential facts are matched separately through confidential_facts() and never listed here.
create function public.agent_org_context(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'rules', coalesce((select jsonb_agg(to_jsonb(r) order by r.id)
                       from public.rules r where r.org_id = p_org and r.active), '[]'::jsonb),
    'terms', coalesce((select jsonb_agg(to_jsonb(t) order by t.id)
                       from public.terms t where t.org_id = p_org), '[]'::jsonb),
    'facts', coalesce((select jsonb_agg(to_jsonb(f) order by f.id)
                       from public.facts f
                       where f.org_id = p_org and f.confidentiality in ('public', 'internal')),
                      '[]'::jsonb),
    'wordings', coalesce((select jsonb_agg(to_jsonb(w) order by w.id)
                          from public.approved_wordings w
                          where w.org_id = p_org and exists (
                            select 1 from public.facts f
                            where f.org_id = w.org_id and f.id = w.fact_id
                              and f.confidentiality in ('public', 'internal'))), '[]'::jsonb))
$$;

-- ---- the publish gate -------------------------------------------------------------------------

create function public.gate_key_create(p_org uuid, p_by uuid, p_hash text, p_label text)
returns uuid language sql security definer set search_path = '' as $$
  insert into public.gate_keys (org_id, created_by, key_hash, label)
  values (p_org, p_by, p_hash, p_label) returning id
$$;

create function public.gate_key_org(p_hash text)
returns uuid language sql security definer set search_path = '' as $$
  update public.gate_keys set last_used_at = now()
  where key_hash = p_hash and revoked_at is null returning org_id
$$;

create function public.gate_keys_list(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object('id', id, 'label', label, 'created_at', created_at,
           'last_used_at', last_used_at, 'revoked_at', revoked_at) order by created_at desc), '[]'::jsonb)
  from public.gate_keys where org_id = p_org
$$;

create function public.gate_key_revoke(p_org uuid, p_id uuid)
returns int language sql security definer set search_path = '' as $$
  with u as (update public.gate_keys set revoked_at = now()
             where id = p_id and org_id = p_org and revoked_at is null returning 1)
  select count(*)::int from u
$$;

create function public.gate_latest_version(p_org uuid, p_content uuid)
returns uuid language sql stable security definer set search_path = '' as $$
  select id from public.versions
  where content_id = p_content and org_id = p_org and not private
  order by n desc limit 1
$$;

-- One version of one org: the version, its latest real check, that check's findings (for their record
-- ids), the decisions on them and the approvals. Null if the version isn't this org's or is private.
create function public.gate_snapshot(p_org uuid, p_version uuid)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare v jsonb; r record;
begin
  select to_jsonb(x) into v from (
    select id, content_id, n, text, status from public.versions
    where id = p_version and org_id = p_org and not private) x;
  if v is null then return null; end if;
  select id, report_json into r from public.check_runs
  where version_id = p_version and report_json ? 'findings'
  order by created_at desc limit 1;
  return jsonb_build_object(
    'version', v,
    'report', r.report_json,
    'findings', coalesce((select jsonb_agg(jsonb_build_object('id', f.id, 'payload', f.payload_json))
                          from public.findings f where f.run_id = r.id), '[]'::jsonb),
    'decisions', coalesce((select jsonb_agg(jsonb_build_object(
                             'finding_id', d.finding_id, 'action', d.action, 'at', d.at))
                           from public.decisions d join public.findings f on f.id = d.finding_id
                           where f.run_id = r.id), '[]'::jsonb),
    'approvals', coalesce((select jsonb_agg(jsonb_build_object(
                             'stage', a.stage, 'outcome', a.outcome, 'at', a.at))
                           from public.approvals a where a.version_id = p_version), '[]'::jsonb));
end $$;

create function public.gate_log(p_org uuid, p_version uuid, p_decision text, p_reasons text[])
returns void language sql security definer set search_path = '' as $$
  insert into public.gate_calls (org_id, version_id, decision, reasons)
  values (p_org, p_version, p_decision, p_reasons)
$$;

create function public.gate_calls_recent(p_org uuid, p_limit int default 20)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object('version_id', version_id, 'decision', decision,
           'reasons', reasons, 'at', at) order by at desc), '[]'::jsonb)
  from (select * from public.gate_calls where org_id = p_org order by at desc limit p_limit) c
$$;

-- Only the narrow checker role may call any of these.
do $$
declare f record;
begin
  for f in select oid::regprocedure as sig from pg_proc
           where pronamespace = 'public'::regnamespace
             and (proname like 'agent\_%' or proname like 'gate\_%') loop
    execute format('revoke all on function %s from public, anon, authenticated, service_role', f.sig);
    execute format('grant execute on function %s to plumbline_checker', f.sig);
  end loop;
end $$;
