-- Improvement 3: rules graduate on evidence, with an audit event and undo; reworded rules are drafted,
-- replayed and accepted by the owner.
--   * A trigger on decisions moves a brand rule to blocking at Wilson lower bound >= 0.80 on >= 10
--     decisions, and back to advisory (only if it graduated by itself) below 0.70.
--   * An owner's undo pins the rule: the mechanism leaves it alone until the owner unpins it.
--   * Every move is a rule_changes row, which the audit chain records (audit_append).

alter table public.rules
  add column pinned boolean not null default false,
  add column graduated_auto boolean not null default false;

create table public.rule_changes (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations,
  rule_id text not null,
  kind text not null check (kind in ('graduate','demote','undo','unpin','clarify','revert')),
  from_value text,
  to_value text,
  why text not null,
  n int,
  upheld int,
  lower double precision,
  actor uuid,
  detail jsonb not null default '{}',
  at timestamptz not null default clock_timestamp()
);
create index on public.rule_changes (org_id, at desc);
alter table public.rule_changes enable row level security;
create policy org_read on public.rule_changes for select to authenticated
  using (org_id = public.current_org() and public.sees_org_insights());
revoke all on public.rule_changes from anon, authenticated;
grant select on public.rule_changes to authenticated;
create trigger audit_rule_changes after insert on public.rule_changes
  for each row execute function public.audit_append();

create table public.rule_clarifications (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations,
  rule_id text not null,
  status text not null default 'draft' check (status in ('draft','accepted','rejected','reverted')),
  old_wording jsonb not null,
  new_wording jsonb not null,
  evidence jsonb not null default '{}',
  replay jsonb not null default '{}',
  created_by uuid default auth.uid(),
  decided_by uuid,
  created_at timestamptz not null default now(),
  decided_at timestamptz
);
create index on public.rule_clarifications (org_id, rule_id);
alter table public.rule_clarifications enable row level security;
create policy org_read on public.rule_clarifications for select to authenticated
  using (org_id = public.current_org() and public.sees_org_insights());
revoke all on public.rule_clarifications from anon, authenticated;
grant select on public.rule_clarifications to authenticated;

-- The wording of a rule: what a reviewer reads and what the AI judge is given.
create function public.rule_wording(r public.rules) returns jsonb
language sql immutable set search_path = '' as $$
  select jsonb_build_object('title', r.title, 'instruction', r.params->>'instruction',
    'examples_good', to_jsonb(r.examples_good), 'examples_bad', to_jsonb(r.examples_bad))
$$;

-- Counts as the health page does: decisions on findings of non-private versions.
create function public.rule_counts(p_org uuid, p_rule text, out upheld bigint, out n bigint)
language sql stable security definer set search_path = '' as $$
  select count(*) filter (where dc.action in ('accept','edit','uphold')),
         count(*)
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
  join public.decisions dc on dc.finding_id = f.id
  where f.org_id = p_org and f.rule_id = p_rule
$$;

create function public.graduate_on_decision() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  fnd record;
  rl public.rules;
  c record;
  lb double precision;
begin
  select org_id, rule_id into fnd from public.findings where id = new.finding_id;
  if fnd.rule_id is null then return null; end if;
  select * into rl from public.rules where org_id = fnd.org_id and id = fnd.rule_id for update;
  if not found or not rl.active or rl.tier <> 'brand' or rl.pinned then return null; end if;
  select * into c from public.rule_counts(fnd.org_id, fnd.rule_id);
  if c.n < 10 then return null; end if;
  lb := public.wilson_lower(c.upheld, c.n);
  if rl.maturity = 'advisory' and lb >= 0.80 then
    update public.rules set maturity = 'blocking', graduated_auto = true, updated_at = now()
      where org_id = rl.org_id and id = rl.id;
    insert into public.rule_changes (org_id, rule_id, kind, from_value, to_value, why, n, upheld, lower)
      values (rl.org_id, rl.id, 'graduate', 'advisory', 'blocking',
        format('Reviewers upheld %s of %s decisions; we are 95%% sure they agree at least %s%% of the time.',
          c.upheld, c.n, floor(lb * 100)), c.n, c.upheld, lb);
  elsif rl.maturity = 'blocking' and rl.graduated_auto and lb < 0.70 then
    update public.rules set maturity = 'advisory', graduated_auto = false, updated_at = now()
      where org_id = rl.org_id and id = rl.id;
    insert into public.rule_changes (org_id, rule_id, kind, from_value, to_value, why, n, upheld, lower)
      values (rl.org_id, rl.id, 'demote', 'blocking', 'advisory',
        format('Agreement fell: %s of %s decisions upheld, lower bound %s%%.', c.upheld, c.n, floor(lb * 100)),
        c.n, c.upheld, lb);
  end if;
  return null;
end $$;
create trigger graduate_after_decision after insert on public.decisions
  for each row execute function public.graduate_on_decision();

-- Owner actions. They act as the signed-in owner of the rule's function (same test as editing a rule).
create function public.rule_owned(p_rule text) returns public.rules
language plpgsql security definer set search_path = '' as $$
declare rl public.rules;
begin
  select * into rl from public.rules where org_id = public.current_org() and id = p_rule for update;
  if not found or not public.owns_rule(rl.owner_function) then
    raise exception 'not allowed' using errcode = '42501';
  end if;
  return rl;
end $$;

create function public.rule_undo(p_rule text) returns void
language plpgsql security definer set search_path = '' as $$
declare rl public.rules := public.rule_owned(p_rule);
begin
  if rl.tier <> 'brand' or rl.maturity <> 'blocking' or not rl.graduated_auto then
    raise exception 'only an automatic graduation can be undone' using errcode = '22023';
  end if;
  update public.rules set maturity = 'advisory', graduated_auto = false, pinned = true, updated_at = now()
    where org_id = rl.org_id and id = rl.id;
  insert into public.rule_changes (org_id, rule_id, kind, from_value, to_value, why, actor)
    values (rl.org_id, rl.id, 'undo', 'blocking', 'advisory',
      'The rule owner undid the graduation. Plumbline will not graduate this rule again unless it is released.',
      auth.uid());
end $$;

create function public.rule_unpin(p_rule text) returns void
language plpgsql security definer set search_path = '' as $$
declare rl public.rules := public.rule_owned(p_rule);
begin
  update public.rules set pinned = false, updated_at = now() where org_id = rl.org_id and id = rl.id;
  insert into public.rule_changes (org_id, rule_id, kind, from_value, to_value, why, actor)
    values (rl.org_id, rl.id, 'unpin', 'pinned', 'automatic',
      'The rule owner let Plumbline decide again.', auth.uid());
end $$;

-- A draft never changes a live rule. Only brand-tier rules are reworded here.
create function public.clarification_save(p_rule text, p_new jsonb, p_evidence jsonb, p_replay jsonb)
returns uuid language plpgsql security definer set search_path = '' as $$
declare rl public.rules := public.rule_owned(p_rule); cid uuid;
begin
  if rl.tier <> 'brand' then
    raise exception 'only brand rules can be reworded' using errcode = '22023';
  end if;
  update public.rule_clarifications set status = 'rejected', decided_by = auth.uid(), decided_at = now()
    where org_id = rl.org_id and rule_id = rl.id and status = 'draft';
  insert into public.rule_clarifications (org_id, rule_id, old_wording, new_wording, evidence, replay)
    values (rl.org_id, rl.id, public.rule_wording(rl), p_new, p_evidence, p_replay) returning id into cid;
  return cid;
end $$;

create function public.clarification_accept(p_id uuid, p_wording jsonb) returns void
language plpgsql security definer set search_path = '' as $$
declare cl public.rule_clarifications; rl public.rules;
begin
  select * into cl from public.rule_clarifications where id = p_id and org_id = public.current_org();
  if not found or cl.status <> 'draft' then
    raise exception 'no such draft' using errcode = '22023';
  end if;
  rl := public.rule_owned(cl.rule_id);
  update public.rules set title = p_wording->>'title',
      params = jsonb_set(params, '{instruction}', to_jsonb(p_wording->>'instruction')),
      examples_good = array(select jsonb_array_elements_text(p_wording->'examples_good')),
      examples_bad = array(select jsonb_array_elements_text(p_wording->'examples_bad')),
      updated_at = now()
    where org_id = rl.org_id and id = rl.id;
  update public.rule_clarifications set status = 'accepted', new_wording = p_wording,
      decided_by = auth.uid(), decided_at = now() where id = p_id;
  insert into public.rule_changes (org_id, rule_id, kind, why, actor, detail)
    values (rl.org_id, rl.id, 'clarify', 'The rule owner accepted a clearer wording.', auth.uid(),
      jsonb_build_object('clarification', p_id, 'old', cl.old_wording, 'new', p_wording));
end $$;

create function public.clarification_reject(p_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare cl public.rule_clarifications;
begin
  select * into cl from public.rule_clarifications where id = p_id and org_id = public.current_org();
  if not found or cl.status <> 'draft' then
    raise exception 'no such draft' using errcode = '22023';
  end if;
  perform public.rule_owned(cl.rule_id);
  update public.rule_clarifications set status = 'rejected', decided_by = auth.uid(), decided_at = now()
    where id = p_id;
end $$;

create function public.clarification_revert(p_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare cl public.rule_clarifications; rl public.rules;
begin
  select * into cl from public.rule_clarifications where id = p_id and org_id = public.current_org();
  if not found or cl.status <> 'accepted' then
    raise exception 'no such accepted rewording' using errcode = '22023';
  end if;
  rl := public.rule_owned(cl.rule_id);
  update public.rules set title = cl.old_wording->>'title',
      params = jsonb_set(params, '{instruction}', to_jsonb(cl.old_wording->>'instruction')),
      examples_good = array(select jsonb_array_elements_text(cl.old_wording->'examples_good')),
      examples_bad = array(select jsonb_array_elements_text(cl.old_wording->'examples_bad')),
      updated_at = now()
    where org_id = rl.org_id and id = rl.id;
  update public.rule_clarifications set status = 'reverted', decided_by = auth.uid(), decided_at = now()
    where id = p_id;
  insert into public.rule_changes (org_id, rule_id, kind, why, actor, detail)
    values (rl.org_id, rl.id, 'revert', 'The rule owner restored the earlier wording.', auth.uid(),
      jsonb_build_object('clarification', p_id));
end $$;

-- Disputed decisions on one rule, for drafting and replay: public versions only, no confidential facts.
create function public.rule_cases(p_rule text) returns table (quote text, action text, reason text)
language sql stable security definer set search_path = '' as $$
  select f.quote, dc.action, dc.reason
  from public.findings f
  join public.check_runs r on r.id = f.run_id
  join public.versions v on v.id = r.version_id and not v.private
  join public.decisions dc on dc.finding_id = f.id
  where f.org_id = public.current_org() and f.rule_id = p_rule and public.sees_org_insights()
    and f.fact_id is null
  order by dc.at
$$;

do $$
declare f record;
begin
  for f in select p.oid::regprocedure as sig from pg_proc p
    where p.pronamespace = 'public'::regnamespace
      and p.proname in ('rule_owned','rule_undo','rule_unpin','clarification_save','clarification_accept',
        'clarification_reject','clarification_revert','rule_cases') loop
    execute format('revoke all on function %s from public, anon', f.sig);
    execute format('grant execute on function %s to authenticated', f.sig);
  end loop;
  revoke all on function public.rule_counts(uuid, text) from public, anon, authenticated;
  revoke all on function public.graduate_on_decision() from public, anon, authenticated;
end $$;
