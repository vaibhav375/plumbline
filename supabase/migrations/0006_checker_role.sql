-- Confidential matching for every check, including an agency's (open item from Tasks 6 and 9).
-- The API reads as the signed-in user, so an agency's check can't see embargoed facts and so
-- couldn't mask or flag them. A function users could call would let an agency probe which phrases
-- are secret (§4.5). Instead: a role with no table access that can only call this one function.
-- Login and its password are set outside migrations (the repo is public): see
-- services/checker/scripts/checker_role.py.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'plumbline_checker') then
    create role plumbline_checker nologin noinherit;
  end if;
end $$;
grant plumbline_checker to postgres;  -- lets the owner (and the DB tests) act as it

create function public.confidential_facts(p_org uuid) returns setof public.facts
language sql stable security definer set search_path = '' as $$
  select * from public.facts
  where org_id = p_org and confidentiality in ('confidential', 'embargoed')
$$;

revoke all on function public.confidential_facts(uuid) from public, anon, authenticated, service_role;
grant usage on schema public to plumbline_checker;
grant execute on function public.confidential_facts(uuid) to plumbline_checker;
