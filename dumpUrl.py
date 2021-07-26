#!/usr/bin/env python
# usage: dumpUrl.py <url> [success delay] [force]
#   ensures that <url> has been scraped at least once
#   if it needs scraped and the request is successful, [success delay] can be
#     used to specify a delay before returning
#   if force is set the url is always fetched
import scrape
import sys
import time

url = sys.argv[1]
url = scrape.canonizeUrl(url)

force = False
if len(sys.argv) > 3 and sys.argv[3] == 'force':
	force = True

mostRecent = scrape.getMostRecentScrapeWithMeta(url, None, None)
if mostRecent is not None and not force:
	if mostRecent['raw'] is not None:
		print(mostRecent['raw'])
	else:
		print(f"{url} is empty, status: {mostRecent['status']}", file=sys.stderr)
	sys.exit(0)

res = scrape.scrape(url)

print(res['raw'])

if len(sys.argv) > 2:
	time.sleep(float(sys.argv[2]))
