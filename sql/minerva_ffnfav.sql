
CREATE TYPE FFNFavoriteStatus AS ENUM (
	'exists',
	'unknown',
	'userRemoved',
	'siteRemoved'
);

CREATE TABLE FFNUserFavorite (
	userId bigint NOT NULL,
	localId bigint NOT NULL,
	ficId bigint NOT NULL references fic(id),
	lastSeen oil_timestamp NOT NULL,
	status FFNFavoriteStatus DEFAULT 'exists'::FFNFavoriteStatus NOT NULL,

	PRIMARY KEY(userId, localId)
);

