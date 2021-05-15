#!/usr/bin/env python
# this program resrcapes pages held in minerva that were created from the
# hermes import -- that is pages that are mostly stripped down to just story
# text. The firstGoodId was determined through human query.
#
# Optionally a url pattern can be given on the command line:
#     ./rescrapeOld.py '%archiveofourown.org%'
# this will limit it to urls that match like the argument. This is used to run
# an instance of this script per domain in minerva for simple parallelism
# gains.
#
# This script scrapes slowly and delays since the _last_ time the domain was
# hit. If hermes hits a domain while this script is paused, this script will
# wait longer to avoid excessive requests.
import scrape
import random
import time
import sys
from typing import List, Iterable, Sequence, Any

firstGoodId = 68830
batchSize = 100 # somewhere around an hours worth...
globalPattern = '%'


def getBatch(firstGoodId: int, batchSize: int, pattern: str
		) -> List[Sequence[Any]]:
	conn = scrape.openMinerva()

	curs = conn.cursor()
	curs.execute('''
	select w.id, w.url
		--, r.id, w.id, w.created, w.url, w.status, octet_length(w.response)
	from web w
	left join web r
		on (r.url = trim(trailing '/' from w.url))
			and r.status = 200 and r.id >= %s
	where w.id < %s and r.id is null and w.url like %s
	order by random() -- w.id asc
	limit %s
	''', (firstGoodId, firstGoodId, pattern, batchSize))
	res = curs.fetchall()

	curs.close()
	scrape.closeMinerva()
	return list(res)

def isOld(firstGoodId: int, url: str) -> bool:
	matching = getBatch(firstGoodId, 1, url)
	return len(matching) > 0

def getLastScrapeTime(pattern: str, source: str) -> int:
	conn = scrape.openMinerva()

	curs = conn.cursor()
	curs.execute('''
	select w.status, w.created
	from web w
	where w.url like %s and w.created is not null
		and (w.source = %s or w.source is null)
	order by w.created desc
	limit 1
	''', (pattern, source))
	res = curs.fetchone()

	curs.close()
	scrape.closeMinerva()

	if res is None:
		return int(time.time()) - 300
	if int(res[0]) == 429:
		# add extra delay for too many requests
		return int(res[1]) + 60
	return int(res[1])

def getDomain(url: str) -> str:
	strip = ['http://', 'https://']
	for s in strip:
		if url.startswith(s):
			url = url[len(s):]
	p = url.split('/')
	d = p[0].split('.')
	base = '.'.join(d[-2:])
	return base

if len(sys.argv) > 1:
	globalPattern = sys.argv[1]

scrape.importEnvironment()
print('source: {}'.format(scrape.__scrapeSource))
assert(scrape.__scrapeSource is not None)

while True:
	batch = getBatch(firstGoodId, batchSize, globalPattern)
	if len(batch) == 0:
		print('it seems we are done?')
		break
	for r in batch:
		wid = r[0]
		url = r[1]
		s = 15 + random.randint(0, 5)
		patt = '%{}%'.format(getDomain(url))
		while True:
			if not isOld(firstGoodId, url):
				print('not old anymore')
				break # has since been rescraped
			ls = getLastScrapeTime(patt, scrape.__scrapeSource)
			diff = (ls + s) - int(time.time())
			print((patt, int(time.time()), (ls + s), diff))
			if diff < 0:
				break
			else:
				time.sleep(diff + 1)
		if not isOld(firstGoodId, url):
			print('not old anymore')
			continue # has since been rescraped
		time.sleep(3 * random.random())
		print('refetching {}: {}'.format(wid, url))
		try:
			if not isOld(firstGoodId, url):
				print('not old anymore')
				continue # has since been rescraped
			res = scrape.scrape(url)
			print(len(res['raw']))
		except:
			time.sleep(60)

