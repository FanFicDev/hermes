create table if not exists user_fic (
	userId int8 not null references users(id),
	ficId int8 not null references fic(id),

	readStatus ficStatus not null default('ongoing'),

	lastChapterRead int4 null,
	lastChapterViewed int4 null,

	rating smallint null,
	isFavorite boolean not null default(false),

	lastViewed oil_timestamp null,

	primary key(userId, ficId)
);

