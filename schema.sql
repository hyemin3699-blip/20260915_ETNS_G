create table if not exists users (
    id bigint generated always as identity primary key,
    username text not null unique,
    password_hash text not null,
    created_at text not null
);

create table if not exists tasks (
    id bigint generated always as identity primary key,
    content text not null,
    done boolean not null default false,
    created_at text not null
);

alter table tasks add column if not exists user_id bigint references users(id);
