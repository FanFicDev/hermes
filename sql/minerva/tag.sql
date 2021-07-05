create table if not exists tag (
	id bigserial primary key,
	type tag_type not null,
	name text not null,
	parent bigint null,
	sourceId bigint null
);

