create table if not exists nemo_rating (
	id int8 not null references fic(id),
	rating smallint not null
);

