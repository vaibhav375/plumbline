-- Hash-chained audit log, one chain per org (so an org's auditor can verify it under RLS).
-- hash = sha256(prev_hash || payload::text || at as UTC ISO text). The timestamp is
-- rendered in UTC explicitly so verification doesn't depend on the session time zone.

create function public.audit_ts(t timestamptz) returns text
language sql immutable as $$
  select to_char(t at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$$;

create function public.audit_append() returns trigger
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
  -- Serialise appends per org so two concurrent inserts can't share a prev_hash.
  perform pg_advisory_xact_lock(hashtext('audit:' || org::text));
  select a.hash into prev from public.audit_events a where a.org_id = org order by a.id desc limit 1;
  prev := coalesce(prev, repeat('0', 64));
  insert into public.audit_events (org_id, actor, kind, entity, entity_id, payload, prev_hash, hash, at)
  values (
    org,
    coalesce(auth.uid(), (payload->>'actor')::uuid, (payload->>'created_by')::uuid),
    tg_table_name || '.' || lower(tg_op),
    tg_table_name,
    payload->>'id',
    payload,
    prev,
    encode(extensions.digest(prev || payload::text || public.audit_ts(ts), 'sha256'), 'hex'),
    ts);
  return null;
end $$;

create trigger audit_decisions after insert on public.decisions
  for each row execute function public.audit_append();
create trigger audit_approvals after insert on public.approvals
  for each row execute function public.audit_append();
create trigger audit_versions_insert after insert on public.versions
  for each row execute function public.audit_append();
create trigger audit_versions_status after update of status on public.versions
  for each row when (old.status is distinct from new.status)
  execute function public.audit_append();

-- Insert-only, even for the table owner: any update or delete raises.
create function public.audit_immutable() returns trigger
language plpgsql as $$
begin
  raise exception 'audit_events is append-only' using errcode = '42501';
end $$;

create trigger audit_no_change before update or delete on public.audit_events
  for each row execute function public.audit_immutable();

-- Separation of duties: the second approval must come from someone else.
create function public.check_second_approver() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if new.stage = 'second' and exists (
    select 1 from public.approvals a
    where a.version_id = new.version_id and a.stage = 'first' and a.actor = new.actor) then
    raise exception 'A second approval must come from a different person than the first.';
  end if;
  return null;
end $$;

create constraint trigger second_approver_differs after insert on public.approvals
  for each row execute function public.check_second_approver();

-- Guideline health. Private pre-checks never count. security_invoker keeps RLS in force.
create function public.wilson_lower(k bigint, n bigint) returns double precision
language sql immutable as $$
  select case when n = 0 then null else
    (p + z * z / (2 * nf) - z * sqrt(p * (1 - p) / nf + z * z / (4 * nf * nf))) / (1 + z * z / nf) end
  from (select k::float8 / nullif(n, 0) as p, n::float8 as nf, 1.96::float8 as z) s
$$;

create view public.rule_health with (security_invoker = true) as
with d as (
  select f.org_id, f.rule_id,
    count(distinct f.id) as flags,
    count(dc.id) filter (where dc.action in ('accept','edit','uphold')) as upheld,
    count(dc.id) filter (where dc.action = 'overrule') as overruled,
    count(dc.id) filter (where dc.action = 'dismiss') as dismissed
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
  left join public.decisions dc on dc.finding_id = f.id
  where f.rule_id is not null
  group by f.org_id, f.rule_id
)
select org_id, rule_id, flags, upheld, overruled, dismissed,
  upheld::float / nullif(upheld + overruled + dismissed, 0) as agreement,
  public.wilson_lower(upheld, upheld + overruled + dismissed) as wilson_lower
from d;

-- No breakdown for groups of fewer than 3 people.
create view public.insights_by_origin with (security_invoker = true) as
select c.org_id, c.origin,
  count(distinct c.created_by) as authors,
  count(distinct v.id) as versions,
  count(f.id) as findings,
  count(f.id) filter (where f.severity = 'blocking') as blocking
from public.contents c
join public.versions v on v.content_id = c.id and not v.private
left join public.check_runs r on r.version_id = v.id
left join public.findings f on f.run_id = r.id
group by c.org_id, c.origin
having count(distinct c.created_by) >= 3;
