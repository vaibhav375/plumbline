-- Row-level security. Everything is org-scoped; extra rules for private versions,
-- confidential facts and the insert-only audit log.

do $$
declare t text;
begin
  foreach t in array array['organizations','profiles','rules','facts','approved_wordings','terms',
    'contents','versions','check_runs','findings','decisions','approvals','comments',
    'egress_events','eval_runs','audit_events']
  loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Nothing is readable without signing in.
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
alter default privileges in schema public revoke all on tables from anon;

-- A version is visible if it's in my org and either not private or mine.
create function public.version_visible(vid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.versions v
    where v.id = vid and v.org_id = public.current_org()
      and (not v.private or v.created_by = auth.uid()))
$$;

create function public.run_visible(rid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.check_runs r where r.id = rid and public.version_visible(r.version_id))
$$;

create function public.finding_visible(fid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.findings f where f.id = fid and public.run_visible(f.run_id))
$$;

create policy org_read on public.organizations for select to authenticated
  using (id = public.current_org());
create policy org_read on public.profiles for select to authenticated
  using (org_id = public.current_org());

-- Rulebook tables: whole org reads; rule owners write.
do $$
declare t text;
begin
  foreach t in array array['rules','approved_wordings','terms'] loop
    execute format($p$create policy org_read on public.%I for select to authenticated
      using (org_id = public.current_org())$p$, t);
    execute format($p$create policy owners_write on public.%I for all to authenticated
      using (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance','accessibility'))
      with check (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance','accessibility'))$p$, t);
  end loop;
end $$;

-- Confidential and embargoed facts only for reviewers and above (§4.5).
create policy org_read on public.facts for select to authenticated
  using (org_id = public.current_org() and (
    confidentiality in ('public','internal')
    or public.app_role() in ('reviewer','compliance','brand_owner','auditor')));
create policy owners_write on public.facts for all to authenticated
  using (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance'))
  with check (org_id = public.current_org() and public.app_role() in ('brand_owner','compliance'));

create policy org_read on public.contents for select to authenticated
  using (org_id = public.current_org());
create policy own_insert on public.contents for insert to authenticated
  with check (org_id = public.current_org() and created_by = auth.uid());
create policy own_update on public.contents for update to authenticated
  using (org_id = public.current_org() and created_by = auth.uid());

create policy visible_read on public.versions for select to authenticated
  using (public.version_visible(id));
create policy own_insert on public.versions for insert to authenticated
  with check (org_id = public.current_org() and created_by = auth.uid());
-- Creators move their own versions (submit, withdraw); reviewers move submitted ones.
create policy status_update on public.versions for update to authenticated
  using (public.version_visible(id) and (created_by = auth.uid()
    or public.app_role() in ('reviewer','compliance','accessibility','brand_owner')))
  with check (org_id = public.current_org());

create policy visible_read on public.check_runs for select to authenticated
  using (public.version_visible(version_id));
create policy visible_insert on public.check_runs for insert to authenticated
  with check (org_id = public.current_org() and public.version_visible(version_id));

create policy visible_read on public.findings for select to authenticated
  using (public.run_visible(run_id));
create policy visible_insert on public.findings for insert to authenticated
  with check (org_id = public.current_org() and public.run_visible(run_id));

create policy visible_read on public.decisions for select to authenticated
  using (org_id = public.current_org() and public.finding_visible(finding_id));
create policy own_insert on public.decisions for insert to authenticated
  with check (org_id = public.current_org() and actor = auth.uid()
    and public.finding_visible(finding_id));

create policy org_read on public.approvals for select to authenticated
  using (org_id = public.current_org() and public.version_visible(version_id));
create policy reviewer_insert on public.approvals for insert to authenticated
  with check (org_id = public.current_org() and actor = auth.uid()
    and public.app_role() in ('reviewer','compliance','accessibility','brand_owner')
    and public.version_visible(version_id));

create policy visible_read on public.comments for select to authenticated
  using (org_id = public.current_org() and public.version_visible(version_id));
create policy own_insert on public.comments for insert to authenticated
  with check (org_id = public.current_org() and author = auth.uid()
    and public.version_visible(version_id));

create policy org_read on public.egress_events for select to authenticated
  using (org_id = public.current_org());
create policy org_insert on public.egress_events for insert to authenticated
  with check (org_id = public.current_org());

create policy org_read on public.eval_runs for select to authenticated
  using (org_id = public.current_org());

-- Audit log: read-only for every client role; rows come only from audit_append().
create policy org_read on public.audit_events for select to authenticated
  using (org_id = public.current_org());
revoke insert, update, delete, truncate on public.audit_events from authenticated, service_role;
