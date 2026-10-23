-- Found in the Task 14 live run: users couldn't create versions through the API. PostgREST
-- inserts with RETURNING, and the returned row must also pass the SELECT policy. That policy
-- called version_visible(id), which looks the row up again and can't see it inside the same
-- statement. The read rule is now written on the row's own columns (same logic as 0004).
drop policy visible_read on public.versions;
create policy visible_read on public.versions for select to authenticated
  using (org_id = public.current_org()
    and (not private or created_by = auth.uid())
    and (public.app_role() <> 'external_creator' or created_by = auth.uid()));
