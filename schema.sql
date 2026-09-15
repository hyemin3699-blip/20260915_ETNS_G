create table if not exists tasks (
    id bigint generated always as identity primary key,
    content text not null,
    done boolean not null default false,
    created_at text not null
);
