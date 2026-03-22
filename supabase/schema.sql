create table if not exists public.workspace_snapshots (
  workspace_id text primary key,
  name text not null default 'Main Workspace',
  workspace jsonb not null,
  updated_at timestamptz not null default now()
);

create or replace function public.set_workspace_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists workspace_snapshots_set_updated_at on public.workspace_snapshots;
create trigger workspace_snapshots_set_updated_at
before update on public.workspace_snapshots
for each row
execute function public.set_workspace_updated_at();

alter table public.workspace_snapshots enable row level security;

drop policy if exists "workspace snapshots public read" on public.workspace_snapshots;
create policy "workspace snapshots public read"
on public.workspace_snapshots
for select
using (true);

drop policy if exists "workspace snapshots public insert" on public.workspace_snapshots;
create policy "workspace snapshots public insert"
on public.workspace_snapshots
for insert
with check (true);

drop policy if exists "workspace snapshots public update" on public.workspace_snapshots;
create policy "workspace snapshots public update"
on public.workspace_snapshots
for update
using (true)
with check (true);

comment on table public.workspace_snapshots is
'Demo-oriented workspace persistence for the Ponder-style platform. Tighten RLS before multi-user production.';
