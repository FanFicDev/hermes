with ffnIds as (
	select split_part(w.url, '/', 5) as fid, min(w.id) as wid
	from web w
	left join web r
		on (r.url = trim(trailing '/' from w.url)) and r.status = 200 and r.id >= 68830
	where w.id < 68830 and r.id is null and w.url like 'http%fanfiction.net/s/%'
	group by split_part(w.url, '/', 5)
)
select f.fid, f.wid, w.url
from ffnIds f
join web w on w.id = f.wid
left join web r
	on r.url like 'https://www.fanfiction.net/s/%'
		and split_part(r.url, '/', 5) = f.fid
		and r.status = 200 and r.id >= 68830
where r.id is null
