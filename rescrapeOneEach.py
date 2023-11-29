#!/usr/bin/env python
# like rescrapeOld, this program resrcapes pages held in minerva that were
# created from the hermes import -- that is pages that are mostly stripped
# down to just story text. The firstGoodId was determined through human query.
#
# Unlike rescrapeOld which selects random un-resraped urls to fetch, this
# script attepmts to get at least 1 page from each ffn fanfic in the database
# rescraped so we have workable metadata. It picks the earliest url contained
# in minerva, which due to a bug in the import is likely to be chapter 2.
#
# A more complete solution is still incoming.
from typing import Any, List, Sequence
import random
import sys
import time

import scrape

firstGoodId = 68830
batchSize = 100  # somewhere around an hours worth...
globalPattern = "%"


def getBatch(firstGoodId: int, batchSize: int, pattern: str) -> List[Sequence[Any]]:
    conn = scrape.openMinerva()

    curs = conn.cursor()
    curs.execute(
        """
with ffnIds as (
    select split_part(w.url, '/', 5) as fid, min(w.id) as wid
    from web w
    left join web r
        on (r.url = trim(trailing '/' from w.url)) and r.status = 200 and r.id >= %s
    where w.id < %s and r.id is null and w.url like 'http%%fanfiction.net/s/%%'
    group by split_part(w.url, '/', 5)
)
select f.wid, w.url
from ffnIds f
join web w on w.id = f.wid
left join web r
    on r.url like 'https://www.fanfiction.net/s/%%'
        and split_part(r.url, '/', 5) = f.fid
        and r.status = 200 and r.id >= %s
where r.id is null
limit %s
    """,
        (firstGoodId, firstGoodId, firstGoodId, batchSize),
    )
    res = curs.fetchall()

    curs.close()
    scrape.closeMinerva()
    return list(res)


def getLastScrapeTime(pattern: str) -> int:
    conn = scrape.openMinerva()

    curs = conn.cursor()
    curs.execute(
        """
    select w.status, w.created
    from web w
    where w.url like %s and w.created is not null
    order by w.created desc
    limit 1
    """,
        (pattern,),
    )
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
    strip = ["http://", "https://"]
    for s in strip:
        if url.startswith(s):
            url = url[len(s) :]
    p = url.split("/")
    d = p[0].split(".")
    base = ".".join(d[-2:])
    return base


if len(sys.argv) > 1:
    globalPattern = sys.argv[1]

while True:
    batch = getBatch(firstGoodId, batchSize, globalPattern)
    if len(batch) == 0:
        print("it seems we are done?")
        break
    for r in batch:
        wid = r[0]
        url = r[1]
        s = 10 + random.randint(0, 10)
        patt = f"%{getDomain(url)}%"
        while True:
            ls = getLastScrapeTime(patt)
            diff = (ls + s) - int(time.time())
            print((patt, int(time.time()), (ls + s), diff))
            if diff < 0:
                break
            else:
                time.sleep(diff + 1)
        time.sleep(3 * random.random())
        print(f"refetching {wid}: {url}")
        try:
            scrape.scrape(url)
        except:
            time.sleep(60)
