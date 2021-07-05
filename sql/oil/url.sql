do $$ begin

-- rfc 7230 says min 8k, most browsers/iis don't go over 2k
create domain url as varchar(2048);

exception
	when duplicate_object then null;
end $$

