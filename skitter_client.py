#!/usr/bin/env python3
from typing import Dict, Optional
import time
import urllib.parse

from scrape import (
	ScrapeMeta,
	canonizeUrl,
	decodeRequest,
	delaySecs,
	getLastUrlLike,
	getMostRecentScrapeWithMeta,
	saveWebRequest,
)
import util


def buildScrapeMeta(
	url: str, fetched: int, raw: Optional[str], status: int = 200
) -> ScrapeMeta:
	return {'url': url, 'fetched': fetched, 'raw': raw, 'status': status}


class SkitterClient:
	def __init__(
		self,
		baseUrl: str,
		apiKey: str,
		uname: str,
		upass: str,
		delay: float = 0.02,
		timeout: int = 30,
		ident: Optional[str] = None
	) -> None:
		#self.cookies = cookies if cookies is not None else cm.getDefaultCookies()
		self.delay = delay
		self.timeout = max(1, timeout)
		self.staleOnly = False
		self.headers = {'User-Agent': 'skitter_client/0.1.0'}

		self.baseUrl = baseUrl
		self.apiKey = apiKey
		self.extraData = {'apiKey': self.apiKey}
		self.auth = (uname, upass)

		self.ident = uname if ident is None else ident

	def _makeRequest(self, apiUrl: str,
										params: Optional[Dict[str, str]]) -> Optional[ScrapeMeta]:
		import requests
		r = None
		ts0 = time.time()
		# while we have time to retry
		while (time.time() - ts0) < self.timeout:
			try:
				# attempt a request
				timePassed = time.time() - ts0
				timeLeft = self.timeout - timePassed
				r = requests.get(
					apiUrl,
					headers=self.headers,
					params=params,
					data=self.extraData,
					auth=self.auth,
					timeout=max(1, timeLeft),
				)
			except:
				util.logMessage(
					f'SkitterClient._makeRequest|exception|{apiUrl}', 'scrape.log'
				)
				raise
			# if we got rate limited
			if r.status_code == 429:
				retryAfter = int(r.headers['Retry-After'])
				# and there's enough left in our timeout to retry, then retry
				if (time.time() + retryAfter - ts0) >= self.timeout:
					# otherwise break with the 429 response
					break
				time.sleep(retryAfter)
			else:
				# otherwise break with the non-429 response
				break

		if r is None:
			# this _should_ be unreachable
			raise Exception(
				f'SkitterClient._makeRequest: failed to make request: {apiUrl}'
			)

		if r.status_code == 404:
			return None

		if r.status_code != 200:
			raise Exception(
				'SkitterClient._makeRequest: failed to download url {}: {}'.format(
					r.status_code, apiUrl
				)
			)

		ts = int(r.headers['X-Weaver-Created'])
		url = str(r.headers['X-Weaver-Url'])

		raw = r.content
		text = decodeRequest(raw, url)

		delaySecs(self.delay)
		return buildScrapeMeta(url, ts, text, r.status_code)

	def cache(
		self,
		q: Optional[str] = None,
		u: Optional[str] = None,
		rev: bool = False
	) -> Optional[ScrapeMeta]:
		if (q is None and u is None) or (q is not None and u is not None):
			raise Exception('SkitterClient.cache: q or u must not be None')

		p = ('q', q)
		if u is not None:
			p = ('u', u)
		assert (p[1] is not None)
		#p = (p[0], urllib.parse.quote(p[1], safe=''))

		apiUrl = urllib.parse.urljoin(self.baseUrl, 'v0/cache')
		apiArgs = {p[0]: p[1]}
		if rev:
			apiArgs['r'] = '1'
		return self._makeRequest(apiUrl, apiArgs)

	def crawl(self, q: str) -> ScrapeMeta:
		apiUrl = urllib.parse.urljoin(self.baseUrl, 'v0/crawl')
		res = self._makeRequest(apiUrl, {'q': q})
		if res is None:
			raise Exception(f'SkitterClient.crawl: failed to crawl: {q}')
		return res

	def staleScrape(self, url: str) -> Optional[ScrapeMeta]:
		url = canonizeUrl(url)
		# check if we already have it in our db, return it if we do
		tmpUrl = getLastUrlLike(url)
		if tmpUrl is not None:
			res = getMostRecentScrapeWithMeta(url)
			assert (res is not None)
			return res

		# check if it's in .cache
		res = self.cache(url)
		if res is not None:
			saveWebRequest(res['fetched'], res['url'], res['status'], res['raw'])
			return res

		return None

	def softScrape(self, url: str) -> ScrapeMeta:
		# check if it's cached locally or in .cache
		res = self.staleScrape(url)
		if res is not None:
			return res

		# do .crawl
		return self.scrape(url)

	def scrape(self, url: str) -> ScrapeMeta:
		url = canonizeUrl(url)
		# TODO staleOnly?
		if self.staleOnly:
			util.logMessage(f'staleScrape|{url}', 'scrape.log')

			#r = getMostRecentScrapeWithMeta(url, beforeId = _staleBefore)
			#if r is None or 'raw' not in r:
			#	raise Exception('failed to stale scrape url: {}'.format(url))
			#return { 'url': url, 'fetched': ts, 'raw': r['raw'] }

		res = self.crawl(url)
		saveWebRequest(res['fetched'], res['url'], res['status'], res['raw'])
		return res
