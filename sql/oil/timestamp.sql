do $$ begin

create domain oil_timestamp as int8;

exception
	when duplicate_object then null;
end $$

