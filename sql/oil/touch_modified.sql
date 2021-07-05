create or replace function touch_modified() returns trigger as $touch_modified$
begin
	NEW.modified := oil_timestamp();
	RETURN NEW;
end
$touch_modified$ language plpgsql;

