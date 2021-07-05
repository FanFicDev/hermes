create table if not exists users (
	id bigserial primary key,
	created int8,
	updated int8,
	name text unique,
	hash text,
	mail text unique,
	apiKey text unique
);

