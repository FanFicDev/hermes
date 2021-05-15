-- rfc 7230 says min 8k, most browsers/iis don't go over 2k
create domain url as varchar(2048);
create domain oil_timestamp as int8;

create or replace function oil_timestamp()
	returns oil_timestamp
	as 'select floor(extract(epoch from current_timestamp) * 1000) :: oil_timestamp;'
	language sql
	stable;

create function touch_modified() returns trigger as $touch_modified$
begin
	NEW.modified := oil_timestamp();
	RETURN NEW;
end
$touch_modified$ language plpgsql;

