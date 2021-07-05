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

