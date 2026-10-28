-- Construction Site Assistant
-- Migration 002: Generalized private project and observation evidence
--
-- Supports common image and document formats.
-- The schema can accommodate video metadata in a future release.
-- This migration does not modify or migrate existing photo records.

begin;

-- ============================================================
-- 1. EVIDENCE METADATA
-- Each record belongs to either a project or an observation.
-- If linked to an observation, its project is inherited through
-- the observation's existing project_id.
-- ============================================================

create table public.observation_evidence (
    evidence_id uuid primary key default gen_random_uuid(),

    owner_id uuid not null
        references auth.users(id) on delete cascade,

    project_id uuid,
    observation_id text,

    object_path text not null unique,
    original_filename text not null,
    mime_type text not null,
    file_size_bytes bigint not null
        check (file_size_bytes > 0),

    caption text not null default '',
    evidence_category text not null default 'Other',
    created_at timestamptz not null default now(),

    constraint evidence_exactly_one_parent
        check (
            (project_id is not null and observation_id is null)
            or
            (project_id is null and observation_id is not null)
        ),

    constraint evidence_project_same_owner_fk
        foreign key (owner_id, project_id)
        references public.projects(owner_id, id)
        on delete restrict,

    constraint evidence_observation_same_owner_fk
        foreign key (owner_id, observation_id)
        references public.observations(owner_id, observation_id)
        on delete restrict,

    constraint evidence_owner_path_unique
        unique (owner_id, object_path)
);

create index evidence_owner_created_idx
    on public.observation_evidence(owner_id, created_at desc);

create index evidence_owner_project_idx
    on public.observation_evidence(owner_id, project_id);

create index evidence_owner_observation_idx
    on public.observation_evidence(owner_id, observation_id);


-- ============================================================
-- 2. TABLE PERMISSIONS
-- ============================================================

grant select, insert, delete
    on public.observation_evidence to authenticated;

revoke update
    on public.observation_evidence from authenticated;

grant update (caption, evidence_category)
    on public.observation_evidence to authenticated;


-- ============================================================
-- 3. ROW LEVEL SECURITY
-- ============================================================

alter table public.observation_evidence
    enable row level security;

create policy "evidence_select_own"
on public.observation_evidence
for select to authenticated
using ((select auth.uid()) = owner_id);

create policy "evidence_insert_own"
on public.observation_evidence
for insert to authenticated
with check (
    (select auth.uid()) = owner_id
    and (
        (
            project_id is not null
            and observation_id is null
            and exists (
                select 1
                from public.projects p
                where p.id = observation_evidence.project_id
                  and p.owner_id = (select auth.uid())
            )
        )
        or
        (
            project_id is null
            and observation_id is not null
            and exists (
                select 1
                from public.observations o
                where o.observation_id =
                      observation_evidence.observation_id
                  and o.owner_id = (select auth.uid())
            )
        )
    )
);

create policy "evidence_update_own"
on public.observation_evidence
for update to authenticated
using ((select auth.uid()) = owner_id)
with check (
    (select auth.uid()) = owner_id
    and (
        (
            project_id is not null
            and observation_id is null
            and exists (
                select 1
                from public.projects p
                where p.id = observation_evidence.project_id
                  and p.owner_id = (select auth.uid())
            )
        )
        or
        (
            project_id is null
            and observation_id is not null
            and exists (
                select 1
                from public.observations o
                where o.observation_id =
                      observation_evidence.observation_id
                  and o.owner_id = (select auth.uid())
            )
        )
    )
);

create policy "evidence_delete_own"
on public.observation_evidence
for delete to authenticated
using ((select auth.uid()) = owner_id);


-- ============================================================
-- 4. PRIVATE STORAGE BUCKET
-- Expected object path:
-- <owner UUID>/<evidence UUID>/<unique filename>
-- ============================================================

insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values (
    'observation-evidence',
    'observation-evidence',
    false,
    52428800,
    array[
        'image/jpeg',
        'image/png',
        'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv'
    ]::text[]
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- ============================================================
-- 5. STORAGE ACCESS POLICIES
-- The matching metadata row must exist before upload.
-- ============================================================

create policy "storage_evidence_select_own"
on storage.objects
for select to authenticated
using (
    bucket_id = 'observation-evidence'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_evidence e
        where e.owner_id = (select auth.uid())
          and e.object_path = storage.objects.name
          and (storage.foldername(name))[2] =
              e.evidence_id::text
    )
);

create policy "storage_evidence_insert_own"
on storage.objects
for insert to authenticated
with check (
    bucket_id = 'observation-evidence'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_evidence e
        where e.owner_id = (select auth.uid())
          and e.object_path = storage.objects.name
          and (storage.foldername(name))[2] =
              e.evidence_id::text
    )
);

create policy "storage_evidence_delete_own"
on storage.objects
for delete to authenticated
using (
    bucket_id = 'observation-evidence'
    and (storage.foldername(name))[1] =
        (select auth.uid())::text
    and exists (
        select 1
        from public.observation_evidence e
        where e.owner_id = (select auth.uid())
          and e.object_path = storage.objects.name
          and (storage.foldername(name))[2] =
              e.evidence_id::text
    )
);

-- No Storage UPDATE policy is provided.
-- Replace a file by deleting the old object and metadata record,
-- then creating a new object and metadata record.

commit;