create table if not exists read_event (
	userId int8 not null references users(id),
	ficId int8 not null references fic(id),
	localChapterId varchar(1024) not null,
	created oil_timestamp not null,
	ficStatus ficStatus not null default('complete'),
	foreign key(ficId, localChapterId) references fic_chapter(ficId, localChapterId)
);

