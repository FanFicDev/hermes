create table if not exists user_fic_chapter (
	userId int8 not null references users(id),
	ficId int8 not null references fic(id),
	localChapterId varchar(1024) not null,

	readStatus ficStatus not null default('ongoing'),

	line int4 not null default(0),
	subLine int4 not null default(0),

	modified oil_timestamp not null default(oil_timestamp()),
	markedRead oil_timestamp null,
	markedAbandoned oil_timestamp null,

	foreign key(ficId, localChapterId) references fic_chapter(ficId, localChapterId),
	primary key(userId, ficId, localChapterId)
);

