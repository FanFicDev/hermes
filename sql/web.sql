create table web (
	id bigserial primary key,
	created oil_timestamp not null default(oil_timestamp()),
	url url not null,
	status smallint not null,
	source varchar(64) null,
	response bytea not null
);

create index idx_web_url on web ( url, status, created );

