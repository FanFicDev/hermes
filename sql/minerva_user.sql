create table user_fic (
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

create table user_fic_chapter (
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

create trigger t_user_fic_chapter_modified
	after update on user_fic_chapter
	for each row execute procedure touch_modified();


create table if not exists read_event (
	userId int8 not null references users(id),
	ficId int8 not null references fic(id),
	localChapterId varchar(1024) not null,
	created oil_timestamp not null,
	ficStatus ficStatus not null default('complete'),
	foreign key(ficId, localChapterId) references fic_chapter(ficId, localChapterId)
);

create table nemo_rating (
	id int8 not null references fic(id),
	rating smallint not null
);

