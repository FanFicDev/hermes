create table if not exists author (
	id bigserial primary key,
	name varchar(1024) not null,
	urlId varchar(12) not null unique
);

