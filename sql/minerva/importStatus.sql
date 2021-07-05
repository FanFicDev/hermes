do $$ begin

create type importStatus as enum ('pending', 'metadata', 'content', 'deep');

exception
	when duplicate_object then null;
end $$

