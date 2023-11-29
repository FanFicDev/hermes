#!/usr/bin/env python
from typing import Optional
import contextlib
import sys
import time
import urllib.parse

from bs4 import BeautifulSoup  # type: ignore

import scrape

archive = sys.argv[1]
url = f"http://{archive}.adult-fanfiction.org/search.php"
url += "?auth=&title=&summary=&tags=%2BCOMPLETE+-MM&cats=0&search=Search"
url += "&page={}"
url = scrape.canonizeUrl(url)


def fetch(url: str, pageNo: int, delay: int, force: bool = False) -> Optional[str]:
    url = url.format(pageNo)
    print(url)

    mostRecent = scrape.getMostRecentScrape(url)
    if mostRecent is not None and not force:
        print(f"url has already been scraped: {url}")
        return None

    res = scrape.scrape(url)
    print(res["fetched"])
    print(len(res["raw"]))

    time.sleep(delay)
    return str(res["raw"])


def getPageFromUrl(url: str, defl: int = -1) -> int:
    r = url[url.find("?") + 1 :]
    qs = urllib.parse.parse_qs(r)
    if "page" not in qs or len(qs["page"]) != 1 or not qs["page"][0].isnumeric():
        return defl
    with contextlib.suppress(ValueError):
        return int(qs["page"][0])
    return defl


prev = scrape.getAllUrlLike(url.format("%"))
print(prev)

if len(prev) < 1:
    fetch(url, 1, 3)
    prev = scrape.getAllUrlLike(url.format("%"))

print(prev)

firstPage = 1
for p in prev:
    firstPage = max(firstPage, getPageFromUrl(p, -1))

lastPage = -1
for p in prev:
    html = scrape.getMostRecentScrape(p)
    if html is None:
        continue
    soup = BeautifulSoup(html, "html5lib")
    for a in soup.findAll("a"):
        href = a.get("href")
        if href is None or not href.startswith("/search.php?"):
            continue

        lastPage = max(lastPage, getPageFromUrl(href, -1))

print(firstPage)
print(lastPage)

for pageNo in range(firstPage + 1, lastPage + 1):
    print(pageNo)
    html = fetch(url, pageNo, 3, False)
