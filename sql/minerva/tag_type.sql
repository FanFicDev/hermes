do $$ begin

create type tag_type as enum ('genre', 'fandom', 'character', 'tag');

exception
	when duplicate_object then null;
end $$

