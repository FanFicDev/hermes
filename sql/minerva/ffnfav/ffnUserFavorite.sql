create table if not exists FFNUserFavorite (
	userId bigint not null,
	localId bigint not null,
	ficId bigint not null references fic(id),
	lastSeen oil_timestamp not null,
	status FFNFavoriteStatus default 'exists'::FFNFavoriteStatus not null,

	primary key(userId, localId)
);

