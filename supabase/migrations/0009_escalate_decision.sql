-- A writer can't dismiss a blocking finding, and some can't be fixed by the writer at all (a claim
-- with no approved wording, an embargo). "Escalate" records that they've passed it to a reviewer,
-- which lets them submit (plan Task 15: "...or the remaining blocking items carry decisions").
alter table public.decisions drop constraint decisions_action_check;
alter table public.decisions add constraint decisions_action_check
  check (action in ('accept', 'edit', 'dismiss', 'uphold', 'overrule', 'escalate'));
