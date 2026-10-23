-- Spec §4.5: insights and guideline health are org-wide for reviewers (incl. accessibility
-- approvers), compliance, brand owners and auditors; creators and agencies see their own work only.
-- Enforced here, not just in the page, so a direct API read gets the same answer.
create function public.sees_org_insights() returns boolean
language sql stable security definer set search_path = '' as $$
  select public.app_role() in ('reviewer','compliance','brand_owner','accessibility','auditor')
$$;

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
  left join public.decisions dc on dc.finding_id = f.id
  where f.rule_id is not null
  group by f.org_id, f.rule_id
)
select org_id, rule_id, flags, upheld, overruled, dismissed,
  upheld::float / nullif(upheld + overruled + dismissed, 0) as agreement,
  public.wilson_lower(upheld, upheld + overruled + dismissed) as wilson_lower
from d;

-- Group comparisons are org-level only; still no breakdown for groups of fewer than 3 people.
create or replace view public.insights_by_origin with (security_invoker = true) as
select c.org_id, c.origin,
  count(distinct c.created_by) as authors,
  count(distinct v.id) as versions,
  count(f.id) as findings,
  count(f.id) filter (where f.severity = 'blocking') as blocking
from public.contents c
join public.versions v on v.content_id = c.id and not v.private
left join public.check_runs r on r.version_id = v.id
left join public.findings f on f.run_id = r.id
where public.sees_org_insights()
group by c.org_id, c.origin
having count(distinct c.created_by) >= 3;
