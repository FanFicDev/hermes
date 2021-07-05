do $$ begin

create type ficStatus as enum ('broken', 'abandoned', 'ongoing', 'complete');

exception
	when duplicate_object then null;
end $$

