-- Keep the free Render checker awake. GitHub's scheduled workflow ran once in ~4.5 hours
-- (scheduled runs are throttled), so the database pings the checker itself every 10 minutes.
-- The checker's /health also calls Supabase, which keeps this free project from pausing.
create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

select cron.schedule(
  'keepalive-checker',
  '*/10 * * * *',
  $$ select net.http_get('https://plumbline-checker.onrender.com/health', timeout_milliseconds := 60000) $$
);
