create table if not exists web (
	id bigserial primary key,
	created int8,
	url varchar(2048), -- rfc 7230 says min 8k, most browsers/iis don't go over 2k
	status smallint,
	response text
);

create index idx_web_url on web ( url, status, created );

