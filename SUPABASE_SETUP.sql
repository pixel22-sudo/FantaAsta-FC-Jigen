-- Tabella già predisposta nel progetto Supabase collegato.
-- Questo file documenta la struttura attesa.
create table if not exists public.fanta_auction_state (
  id text primary key,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.fanta_auction_state enable row level security;
