create table if not exists source (
	id serial primary key,
	url url not null,
	name varchar(1024) not null,
	description varchar(4096) not null
);

