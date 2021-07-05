create table if not exists fic_chapter (
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

