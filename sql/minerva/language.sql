create table if not exists language (
	id serial primary key,
	name varchar(1024) not null unique
);

