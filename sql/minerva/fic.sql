create table if not exists fic (
	id bigserial primary key,
	urlId varchar(12) not null unique,

	sourceId int4 not null references source(id),

	localId varchar(1024) not null,
	url url not null,

	importStatus importStatus not null default('pending'),

	created oil_timestamp not null,
	fetched oil_timestamp not null,

	authorId int8 not null references author(id),

	-- optional metadata
	ficStatus ficStatus not null default('broken'),

	title varchar(4096) null,
	description text null,

	ageRating varchar(128) null,
	languageId int4 null references language(id),

	chapterCount int4 null,
	wordCount int4 null,

	reviewCount int4 null,
	favoriteCount int4 null,
	followCount int4 null,

	updated oil_timestamp null,
	published oil_timestamp null,

	extraMeta text,

	unique(sourceId, localId)
);

