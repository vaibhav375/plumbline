-- Spec §4.5: "Edit rules (each function edits only its own)". 0002 let any rule owner write any
-- rule; now the brand owner writes brand rules, compliance writes compliance rules, and
-- accessibility writes accessibility rules.
create function public.owns_rule(owner_function text) returns boolean
language sql stable security definer set search_path = '' as $$
  select case public.app_role()
    when 'brand_owner' then owner_function = 'brand'
    when 'compliance' then owner_function = 'compliance'
    when 'accessibility' then owner_function = 'accessibility'
    else false end
$$;

drop policy owners_write on public.rules;
create policy owners_write on public.rules for all to authenticated
  using (org_id = public.current_org() and public.owns_rule(owner_function))
  with check (org_id = public.current_org() and public.owns_rule(owner_function));
