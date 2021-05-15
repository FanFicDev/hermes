select count(1)
	, round(count(1) * 15. / 60 / 60 / 24, 2) as minDays
	, round(count(1) * 20. / 60 / 60 / 24, 2) as maxDays
	, round(count(1) * 15. / 60 / 60, 2) as minHours
	, round(count(1) * 20. / 60 / 60, 2) as maxHours
from web w
left join web r
	on (r.url = trim(trailing '/' from w.url)) and r.status = 200 and r.id >= 68830
where w.id < 68830 and r.id is null;
with needsRefetched as (
	select w.url
	from web w
	left join web r
		on (r.url = trim(trailing '/' from w.url)) and r.status = 200 and r.id >= 68830
	where w.id < 68830 and r.id is null
), needsRefetchedCount as (
	select count(1) as freq, split_part(nr.url, '/', 3) as domain
	from needsRefetched nr
	group by split_part(nr.url, '/', 3)
), totalCount as (
	select split_part(w.url, '/', 3) as domain, count(1) as freq
	from web w
	group by split_part(w.url, '/', 3)
)
select tc.domain, tc.freq as total, nrc.freq as remaining
from totalCount tc
left join needsRefetchedCount nrc on nrc.domain = tc.domain
order by nrc.freq desc nulls last, tc.freq desc;
