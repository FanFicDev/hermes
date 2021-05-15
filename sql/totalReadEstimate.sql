.mode column
.header on
select sum(
	case when status = 2
		then wordCount
		else wordCount * 1.0 / chapterCount * lastChapterRead
	end) as total, julianday('now') - julianday('2016-03-01') as days,
	sum(
	case when status = 2
		then wordCount
		else wordCount * 1.0 / chapterCount * lastChapterRead
	end) / (julianday('now') - julianday('2016-03-01')) as average
from fics;

select printf("%.0f", sum(
	case when status = 2
		then wordCount
		else wordCount * 1.0 / chapterCount * lastChapterRead
	end)) as total,
	printf("%.2f",
		julianday('now') - julianday('2016-03-01')) as days,
	printf("%.2f", sum(case when status = 2
		then wordCount
		else wordCount * 1.0 / chapterCount * lastChapterRead
	end) / (julianday('now') - julianday('2016-03-01'))) as average
from fics;

