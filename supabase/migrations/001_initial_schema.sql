
-- Construction Site Assistant
-- Migration 001: Private multi-user database
-- Target: Supabase PostgreSQL
--
-- IMPORTANT:
-- 1. Review before executing.
-- 2. This creates the cloud schema; it does not migrate local records.
-- 3. Photo metadata must be inserted before uploading its storage object.
-- 4. Delete a storage object before deleting its metadata row.
-- 5. Do not use a service-role key in the Streamlit client.

begin;

-- ============================================================
-- 1. USER PROFILES
-- Supabase Auth manages passwords and authentication.
-- ============================================================

create table public.profiles (
    id uuid primary key
        references auth.users(id) on delete cascade,
    display_name text,
    created_at timestamptz not null default now()
);

create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id)
    values (new.id);

    return new;
end;
$$;

revoke all on function public.handle_new_user() from public;
revoke all on function public.handle_new_user() from anon;
revoke all on function public.handle_new_user() from authenticated;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();


-- ============================================================
-- 2. PROJECTS
-- Project codes may repeat across different owners, but not
-- within the same owner's workspace.
-- ============================================================

create table public.projects (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null
        references auth.users(id) on delete cascade,
    project_code text not null,
    project_name text not null,
    location text not null,
    created_at timestamptz not null default now(),

    constraint projects_owner_code_unique
        unique (owner_id, project_code),

    constraint projects_owner_id_unique
        unique (owner_id, id)
);


-- ============================================================
-- 3. OBSERVATIONS
-- observation_id is unique within each owner's workspace.
-- project_id is optional. If supplied, the project must belong
-- to the same owner.
-- ============================================================

create table public.observations (
    observation_id text not null,
    owner_id uuid not null
        references auth.users(id) on delete cascade,

    report_date date not null,
    site text not null default '',
    location text not null,
    contractor text not null,
    category text not null,
    information_source text not null,
    description text not null,
    required_action text not null,
    responsible_party text not null,
    status text not null default 'Open',
    verification_notes text,
    due_date date,
    project_id uuid,
    created_at timestamptz not null default now(),

    primary key (owner_id, observation_id),

    constraint observations_project_same_owner_fk
        foreign key (owner_id, project_id)
        references public.projects(owner_id, id)
        on delete restrict
);

create index observations_owner_date_idx
    on public.observations(owner_id, report_date desc);

create index observations_owner_project_idx
    on public.observations(owner_id, project_id);


-- ============================================================
-- 4. OBSERVATION PHOTO METADATA
-- The actual image files live in private Supabase Storage.
-- object_path is a storage key, never a public URL.
-- ============================================================

create table public.observation_photos (
    photo_id uuid primary key default gen_random_uuid(),
    owner_id uuid not null,
    observation_id text not null,
    object_path text not null unique,
    original_filename text not null,
    caption text not null default '',
    created_at timestamptz not null default now(),

    constraint observation_photos_observation_fk
        foreign key (owner_id, observation_id)
        references public.observations(owner_id, observation_id)
        on delete cascade,

    constraint observation_photos_owner_path_unique
        unique (owner_id, object_path)
);

create index observation_photos_owner_observation_idx
    on public.observation_photos(owner_id, observation_id);


-- ============================================================
-- 5. TABLE PERMISSIONS
-- RLS controls which rows are accessible; GRANT controls
-- which operations the authenticated role may attempt.
-- ============================================================

grant usage on schema public to authenticated;

grant select, update on public.profiles to authenticated;
grant select, insert, update, delete
    on public.projects to authenticated;
grant select, insert, update, delete
    on public.observations to authenticated;
grant select, insert, update, delete
    on public.observation_photos to authenticated;

-- Users may update only their display name through this table.
revoke update on public.profiles from authenticated;
grant update (display_name)
    on public.profiles to authenticated;


-- ============================================================
-- 6. ROW LEVEL SECURITY
-- ============================================================

alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.observations enable row level security;
alter table public.observation_photos enable row level security;


-- Profiles: read and update only your own profile.
create policy "profile_select_own"
on public.profiles
for select to authenticated
using ((select auth.uid()) = id);

create policy "profile_update_own"
on public.profiles
for update to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);


-- Projects: all operations are owner-scoped.
create policy "projects_select_own"
on public.projects
for select to authenticated
using ((select auth.uid()) = owner_id);

create policy "projects_insert_own"
on public.projects
for insert to authenticated
with check ((select auth.uid()) = owner_id);

create policy "projects_update_own"
on public.projects
for update to authenticated
using ((select auth.uid()) = owner_id)
with check ((select auth.uid()) = owner_id);

create policy "projects_delete_own"
on public.projects
for delete to authenticated
using ((select auth.uid()) = owner_id);


-- Observations: all operations are owner-scoped.
create policy "observations_select_own"
on public.observations
for select to authenticated
using ((select auth.uid()) = owner_id);

create policy "observations_insert_own"
on public.observations
for insert to authenticated
with check ((select auth.uid()) = owner_id);

create policy "observations_update_own"
on public.observations
for update to authenticated
using ((select auth.uid()) = owner_id)
with check ((select auth.uid()) = owner_id);

create policy "observations_delete_own"
on public.observations
for delete to authenticated
using ((select auth.uid()) = owner_id);


-- Photo metadata: an owner can access only their own metadata.
create policy "photos_select_own"
on public.observation_photos
for select to authenticated
using ((select auth.uid()) = owner_id);

create policy "photos_insert_own"
on public.observation_photos
for insert to authenticated
with check (
    (select auth.uid()) = owner_id
    and exists (
        select 1
        from public.observations o
        where o.owner_id = (select auth.uid())
          and o.observation_id =
              observation_photos.observation_id
    )
);

create policy "photos_update_own"
on public.observation_photos
for update to authenticated
using ((select auth.uid()) = owner_id)
with check (
    (select auth.uid()) = owner_id
    and exists (
        select 1
        from public.observations o
        where o.owner_id = (select auth.uid())
          and o.observation_id =
              observation_photos.observation_id
    )
);

create policy "photos_delete_own"
on public.observation_photos
for delete to authenticated
using ((select auth.uid()) = owner_id);


-- ============================================================
-- 7. PRIVATE STORAGE BUCKET
-- Expected object path:
-- <owner UUID>/<observation ID>/<unique filename>
--
-- The metadata row must exist before an upload is attempted.
-- ============================================================

insert into storage.buckets (id, name, public)
values ('observation-photos', 'observation-photos', false)
on conflict (id) do update
set public = false;


-- Storage file access requires a matching metadata row and
-- an observation owned by the authenticated user.

create policy "storage_photos_select_own"
on storage.objects
for select to authenticated
using (
    bucket_id = 'observation-photos'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_photos p
        join public.observations o
          on o.owner_id = p.owner_id
         and o.observation_id = p.observation_id
        where p.owner_id = (select auth.uid())
          and p.object_path = storage.objects.name
          and o.owner_id = (select auth.uid())
          and (storage.foldername(name))[2] =
              p.observation_id
    )
);

create policy "storage_photos_insert_own"
on storage.objects
for insert to authenticated
with check (
    bucket_id = 'observation-photos'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_photos p
        join public.observations o
          on o.owner_id = p.owner_id
         and o.observation_id = p.observation_id
        where p.owner_id = (select auth.uid())
          and p.object_path = storage.objects.name
          and o.owner_id = (select auth.uid())
          and (storage.foldername(name))[2] =
              p.observation_id
    )
);

create policy "storage_photos_delete_own"
on storage.objects
for delete to authenticated
using (
    bucket_id = 'observation-photos'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_photos p
        join public.observations o
          on o.owner_id = p.owner_id
         and o.observation_id = p.observation_id
        where p.owner_id = (select auth.uid())
          and p.object_path = storage.objects.name
          and o.owner_id = (select auth.uid())
          and (storage.foldername(name))[2] =
              p.observation_id
    )
);

-- No Storage UPDATE policy is provided. Treat object paths as
-- immutable: create a new object and metadata record if a file
-- must be replaced.

commit;
