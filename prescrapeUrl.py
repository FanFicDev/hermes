#!/usr/bin/env python
# usage: prescrapeUrl.py <url> [success delay] [force]
#   ensures that <url> has been scraped at least once
#   if it needs scraped and the request is successful, [success delay] can be
#     used to specify a delay before returning
#   if force is set the url is always fetched
import sys
import time

import scrape

url = sys.argv[1]
url = scrape.canonizeUrl(url)

force = False
if len(sys.argv) > 3 and sys.argv[3] == 'force':
	force = True

mostRecent = scrape.getMostRecentScrape(url)
if mostRecent is not None and not force:
	print(f'url has already been scraped: {url}')
	sys.exit(0)

print(f'scraping {url}')

res = scrape.scrape(url)

print(res['fetched'])
print(len(res['raw']))

if len(sys.argv) > 2:
	time.sleep(float(sys.argv[2]))
