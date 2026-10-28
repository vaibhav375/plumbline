-- Round 3, improvement 1: the claim watch. Same pattern as 0006 and 0013: tables closed to the API
-- (row-level security on, no policies, no grants), reached only through functions that the narrow
-- plumbline_checker role may call.

create table public.watch_tasks (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations on delete cascade,
  version_id uuid not null references public.versions on delete cascade,
  content_id uuid not null references public.contents on delete cascade,
  fact_id text,                                  -- null for page drift
  reason text not null check (reason in ('removed', 'expired', 'unverified', 'changed', 'drift')),
  detail text not null,                          -- never holds a restricted fact's text
  replacement text,                              -- approved wording to use instead, if one exists
  owner uuid references auth.users on delete set null,
  status text not null default 'open' check (status in ('open', 'done', 'dismissed')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  resolved_by uuid references auth.users on delete set null,
  resolution_note text
);
-- One open task per post, fact and reason: a re-scan never opens it twice.
create unique index watch_tasks_one_open on public.watch_tasks (version_id, coalesce(fact_id, ''), reason)
  where status = 'open';

-- The live address of an approved version, and what the last re-read found.
create table public.published_urls (
  version_id uuid primary key references public.versions on delete cascade,
  org_id uuid not null references public.organizations on delete cascade,
  url text not null,
  added_by uuid references auth.users on delete set null,
  added_at timestamptz not null default now(),
  last_checked_at timestamptz,
  last_result jsonb
);

do $$
declare t text;
begin
  foreach t in array array['watch_tasks', 'published_urls'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;

-- Approved or published versions, each with the facts its latest check says it relied on.
create function public.watch_live(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'version_id', v.id, 'content_id', v.content_id, 'n', v.n, 'text', v.text, 'status', v.status,
    'title', c.title, 'channel', c.channel, 'region', c.region, 'owner', c.created_by,
    'owner_name', p.display_name,
    'claims_used', coalesce(r.report_json -> 'claims_used', '[]'::jsonb))), '[]'::jsonb)
  from public.versions v
  join public.contents c on c.id = v.content_id
  left join public.profiles p on p.user_id = c.created_by
  left join lateral (
    select report_json from public.check_runs
    where version_id = v.id and report_json ? 'findings'
    order by created_at desc limit 1) r on true
  where v.org_id = p_org and not v.private and v.status in ('approved', 'published')
$$;

-- Every fact of the org, restricted ones too (the scan runs in code and never shows their text),
-- with approved wordings.
create function public.watch_facts(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'facts', coalesce((select jsonb_agg(to_jsonb(f)) from public.facts f where f.org_id = p_org), '[]'::jsonb),
    'wordings', coalesce((select jsonb_agg(to_jsonb(w)) from public.approved_wordings w where w.org_id = p_org), '[]'::jsonb))
$$;

create function public.watch_task_add(
  p_org uuid, p_version uuid, p_content uuid, p_fact text, p_reason text,
  p_detail text, p_replacement text, p_owner uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
begin
  insert into public.watch_tasks (org_id, version_id, content_id, fact_id, reason, detail, replacement, owner)
  values (p_org, p_version, p_content, p_fact, p_reason, p_detail, p_replacement, p_owner);
  return true;
exception when unique_violation then
  return false;
end $$;

create function public.watch_tasks_list(p_org uuid, p_status text default 'open', p_owner uuid default null)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'id', t.id, 'version_id', t.version_id, 'content_id', t.content_id, 'title', c.title,
    'fact_id', t.fact_id, 'reason', t.reason, 'detail', t.detail, 'replacement', t.replacement,
    'owner', t.owner, 'owner_name', p.display_name, 'status', t.status,
    'created_at', t.created_at, 'resolved_at', t.resolved_at, 'note', t.resolution_note)
    order by t.created_at desc), '[]'::jsonb)
  from public.watch_tasks t
  join public.contents c on c.id = t.content_id
  left join public.profiles p on p.user_id = t.owner
  where t.org_id = p_org and (p_status = 'all' or t.status = p_status)
    and (p_owner is null or t.owner = p_owner)
$$;

create function public.watch_task_resolve(p_org uuid, p_id uuid, p_by uuid, p_status text, p_note text)
returns int language sql security definer set search_path = '' as $$
  with u as (
    update public.watch_tasks set status = p_status, resolved_at = now(), resolved_by = p_by,
      resolution_note = p_note
    where id = p_id and org_id = p_org and status = 'open' and p_status in ('done', 'dismissed')
    returning 1)
  select count(*)::int from u
$$;

create function public.watch_url_set(p_org uuid, p_version uuid, p_url text, p_by uuid)
returns int language sql security definer set search_path = '' as $$
  with ok as (
    select id from public.versions
    where id = p_version and org_id = p_org and not private and status in ('approved', 'published')),
  ins as (
    insert into public.published_urls (version_id, org_id, url, added_by)
    select id, p_org, p_url, p_by from ok
    on conflict (version_id) do update
      set url = excluded.url, added_by = excluded.added_by, added_at = now(),
          last_checked_at = null, last_result = null
    returning 1)
  select count(*)::int from ins
$$;

create function public.watch_urls_list(p_org uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'version_id', u.version_id, 'url', u.url, 'title', c.title, 'owner', c.created_by,
    'added_at', u.added_at, 'last_checked_at', u.last_checked_at, 'last_result', u.last_result)
    order by u.added_at desc), '[]'::jsonb)
  from public.published_urls u
  join public.versions v on v.id = u.version_id
  join public.contents c on c.id = v.content_id
  where u.org_id = p_org
$$;

create function public.watch_url_target(p_org uuid, p_version uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object('url', u.url, 'text', v.text, 'content_id', v.content_id,
                            'owner', c.created_by)
  from public.published_urls u
  join public.versions v on v.id = u.version_id
  join public.contents c on c.id = v.content_id
  where u.org_id = p_org and u.version_id = p_version
$$;

create function public.watch_url_result(p_org uuid, p_version uuid, p_result jsonb)
returns void language sql security definer set search_path = '' as $$
  update public.published_urls set last_checked_at = now(), last_result = p_result
  where org_id = p_org and version_id = p_version
$$;

do $$
declare f record;
begin
  for f in select oid::regprocedure as sig from pg_proc
           where pronamespace = 'public'::regnamespace and proname like 'watch\_%' loop
    execute format('revoke all on function %s from public, anon, authenticated, service_role', f.sig);
    execute format('grant execute on function %s to plumbline_checker', f.sig);
  end loop;
end $$;
