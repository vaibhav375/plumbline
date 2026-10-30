-- A finding counts once: its latest decision. Before this, every decision row counted, so a reviewer
-- re-clicking (or changing their mind) added agreement again. Found on 30 Oct 2026 when a script
-- re-upheld one finding about 20 times (docs/build-log.md, Task 23). The history stays in `decisions`
-- (it is audited and append-only); only the counts change. Three places count decisions: the health
-- view, the graduation counter, and the cases a clarification is drafted from.

create view public.latest_decisions with (security_invoker = true) as
select distinct on (finding_id) *
from public.decisions
order by finding_id, at desc, id desc;
grant select on public.latest_decisions to authenticated;

create or replace view public.rule_health with (security_invoker = true) as
with d as (
  select f.org_id, f.rule_id,
    count(distinct f.id) as flags,
    count(dc.id) filter (where dc.action in ('accept','edit','uphold')) as upheld,
    count(dc.id) filter (where dc.action = 'overrule') as overruled,
    count(dc.id) filter (where dc.action = 'dismiss') as dismissed
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
    and (public.sees_org_insights() or v.created_by = auth.uid())
  left join public.latest_decisions dc on dc.finding_id = f.id
  where f.rule_id is not null
  group by f.org_id, f.rule_id
)
select org_id, rule_id, flags, upheld, overruled, dismissed,
  upheld::float / nullif(upheld + overruled + dismissed, 0) as agreement,
  public.wilson_lower(upheld, upheld + overruled + dismissed) as wilson_lower
from d;

create or replace function public.rule_counts(p_org uuid, p_rule text, out upheld bigint, out n bigint, out sample bigint)
language sql stable security definer set search_path = '' as $$
  select count(*) filter (where dc.action in ('accept','edit','uphold')),
         count(*),
         count(*) filter (where ct.title like '[synthetic]%')
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
  join public.contents ct on ct.id = v.content_id
  join public.latest_decisions dc on dc.finding_id = f.id
  where f.org_id = p_org and f.rule_id = p_rule
$$;

create or replace function public.rule_cases(p_rule text) returns table (quote text, action text, reason text)
language sql stable security definer set search_path = '' as $$
  select f.quote, dc.action, dc.reason
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
  join public.latest_decisions dc on dc.finding_id = f.id
  where f.org_id = public.current_org() and f.rule_id = p_rule and public.sees_org_insights()
    and f.fact_id is null
  order by dc.at
$$;
