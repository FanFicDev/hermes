do $$ begin

create type FFNFavoriteStatus as enum (
	'exists',
	'unknown',
	'userRemoved',
	'siteRemoved'
);

exception
	when duplicate_object then null;
end $$

