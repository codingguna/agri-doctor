-- Supabase / Postgres schema for AgriDoctor
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  language text default 'en' check (language in ('en','hi','mr')),
  location text,
  created_at timestamptz default now()
);

create table if not exists predictions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete set null,
  image_path text not null,
  top_label text not null,
  confidence numeric not null,
  all_predictions jsonb not null,
  advisory_snapshot jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_predictions_user on predictions(user_id, created_at desc);

-- Storage bucket (create via dashboard or SQL):
-- insert into storage.buckets (id, name, public) values ('leaf-images','leaf-images', true);
