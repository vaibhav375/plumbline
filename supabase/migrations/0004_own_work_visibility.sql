-- Spec §4.5 permissions table, found in the Task 3 evaluation:
--   "View insights, guideline health and the audit log": creator ◐ own, external creator ◐ own work.
--   External creators (agencies) see their own work only, never the brand's other content.

-- Audit events remember whose work they're about, so creators can be shown only their own.
alter table public.audit_events add column subject_user uuid;

create function public.audit_subject(entity text, payload jsonb) returns uuid
language sql stable security definer set search_path = '' as $$
  select case entity
    when 'versions' then (payload->>'created_by')::uuid
    when 'approvals' then (select v.created_by from public.versions v where v.id = (payload->>'version_id')::uuid)
    when 'decisions' then (
      select v.created_by from public.findings f
      join public.check_runs r on r.id = f.run_id
      join public.versions v on v.id = r.version_id
      where f.id = (payload->>'finding_id')::uuid)
  end
$$;

-- Backfill existing rows: the one sanctioned change to the append-only table.
-- subject_user is not part of the hash, so the chain stays valid.
alter table public.audit_events disable trigger audit_no_change;
update public.audit_events set subject_user = public.audit_subject(entity, payload);
alter table public.audit_events enable trigger audit_no_change;

create or replace function public.audit_append() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  payload jsonb := to_jsonb(new);
  org uuid := (payload->>'org_id')::uuid;
  prev text;
  ts timestamptz := clock_timestamp();
begin
  if tg_table_name = 'versions' then
    payload := payload - 'text' - 'doc_json' - 'intent_json';
    if tg_op = 'UPDATE' then
      payload := payload || jsonb_build_object('from_status', old.status);
    end if;
  end if;
  perform pg_advisory_xact_lock(hashtext('audit:' || org::text));
  select a.hash into prev from public.audit_events a where a.org_id = org order by a.id desc limit 1;
  prev := coalesce(prev, repeat('0', 64));
  insert into public.audit_events
    (org_id, actor, kind, entity, entity_id, payload, prev_hash, hash, at, subject_user)
  values (
    org,
    coalesce(auth.uid(), (payload->>'actor')::uuid, (payload->>'created_by')::uuid),
    tg_table_name || '.' || lower(tg_op),
    tg_table_name,
    payload->>'id',
    payload,
    prev,
    encode(extensions.digest(prev || payload::text || public.audit_ts(ts), 'sha256'), 'hex'),
    ts,
    public.audit_subject(tg_table_name, payload));
  return null;
end $$;

drop policy org_read on public.audit_events;
create policy role_read on public.audit_events for select to authenticated
  using (org_id = public.current_org() and (
    public.app_role() in ('reviewer','compliance','accessibility','brand_owner','auditor')
    or subject_user = auth.uid() or actor = auth.uid()));

-- Agencies see only their own versions and contents.
create or replace function public.version_visible(vid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.versions v
    where v.id = vid and v.org_id = public.current_org()
      and (not v.private or v.created_by = auth.uid())
      and (public.app_role() <> 'external_creator' or v.created_by = auth.uid()))
$$;

drop policy org_read on public.contents;
create policy org_read on public.contents for select to authenticated
  using (org_id = public.current_org()
    and (public.app_role() <> 'external_creator' or created_by = auth.uid()));
