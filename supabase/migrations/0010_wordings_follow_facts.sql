-- An approved wording restates its fact, so it must be no more visible than the fact itself.
-- The subquery runs under the caller's own facts policy, so confidential and embargoed wordings
-- reach only the roles that can read those facts.
drop policy org_read on public.approved_wordings;
create policy org_read on public.approved_wordings for select to authenticated
  using (org_id = public.current_org() and exists (
    select 1 from public.facts f
    where f.org_id = approved_wordings.org_id and f.id = approved_wordings.fact_id));

-- A FOR ALL policy also grants reads, so writers are limited to the roles that own facts
-- (accessibility doesn't, and would otherwise read every wording through this policy).
drop policy owners_write on public.approved_wordings;
create policy owners_write on public.approved_wordings for all to authenticated
  using (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance'))
  with check (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance'));
