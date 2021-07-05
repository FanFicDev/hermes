do $$ begin

create trigger t_user_fic_chapter_modified
	after update on user_fic_chapter
	for each row execute procedure touch_modified();

exception
	when duplicate_object then null;
end $$

