create table if not exists fic_tag (
	ficId int8 not null references fic(id),
	tagId int8 not null references tag(id),
	priority int not null default(0)
);

