create table if not exists users (
	id bigserial primary key,
	created int8,
	updated int8,
	name text unique,
	hash text,
	mail text unique,
	apiKey text unique
);

create table if not exists sessions (
	id bigserial primary key,
	created int8,
	updated int8,
	expires int8,
	expired integer,
	uid int8 not null references users(id),
	remote text,
	cookie text
);


