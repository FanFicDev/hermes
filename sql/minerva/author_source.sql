create table if not exists author_source (
	id bigserial primary key,
	authorId int8 not null references author(id),
	sourceId int4 not null references source(id),
	name varchar(1024) not null,
	url url not null,
	localId varchar(1024) not null
);

