create type importStatus as enum ('pending', 'metadata', 'content', 'deep');
create type ficStatus as enum ('broken', 'abandoned', 'ongoing', 'complete');

create table source (
	id serial primary key,
	url url not null,
	name varchar(1024) not null,
	description varchar(4096) not null
);
create table language (
	id serial primary key,
	name varchar(1024) not null unique
);


create table author (
	id bigserial primary key,
	name varchar(1024) not null,
	urlId varchar(12) not null unique
);
create table author_source (
	id bigserial primary key,
	authorId int8 not null references author(id),
	sourceId int4 not null references source(id),
	name varchar(1024) not null,
	url url not null,
	localId varchar(1024) not null
);


create table fic (
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

create index idx_fic_source_lid on fic ( sourceId, localId );
create index idx_fic_url on fic ( url );

create table fic_chapter (
	ficId int8 not null references fic(id),
	chapterId int4 not null,
	localChapterId varchar(1024) not null,

	url url not null,
	fetched oil_timestamp null,

	title varchar(4096) null,
	content bytea null,

	primary key(ficId, chapterId),
	unique(ficId, localChapterId)
);

create index idx_fic_chapter_cid on fic_chapter ( ficId, chapterId );
create index idx_fic_chapter_lid on fic_chapter ( ficId, localChapterId );


create type tag_type as enum ('genre', 'fandom', 'character', 'tag');

create table if not exists tag (
	id bigserial primary key,
	type tag_type not null,
	name text not null,
	parent bigint null,
	sourceId bigint null
);

create table if not exists fic_tag (
	ficId int8 not null references fic(id),
	tagId int8 not null references tag(id),
	priority int not null default(0)
);

