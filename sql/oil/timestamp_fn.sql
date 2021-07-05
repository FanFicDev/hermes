create or replace function oil_timestamp()
	returns oil_timestamp
	as 'select floor(extract(epoch from current_timestamp) * 1000) :: oil_timestamp;'
	language sql
	stable;

