from typing import Optional
import urllib.parse
from scrape import (
	ScrapeMeta,
	canonizeUrl,
	getLastUrlLike,
	getMostRecentScrapeWithMeta,
)
from skitter_client import SkitterClient, saveWebRequest


class WeaverClient(SkitterClient):
	def __init__(
		self,
		baseUrl: str,
		apiKey: str,
		uname: str,
		upass: str,
		delay: float = 0.02,
		timeout: int = 90,
		ident: Optional[str] = None
	) -> None:
		super().__init__(baseUrl, apiKey, uname, upass, delay, timeout, ident)
		self.headers = {'User-Agent': 'weaver_client/0.1.0'}

	def cache(
		self,
		q: Optional[str] = None,
		u: Optional[str] = None,
		rev: bool = False
	) -> Optional[ScrapeMeta]:
		# TODO u support
		if q is None:
			raise Exception('WeaverClient.cache: q must not be None')
		return super().cache(q, u, rev)

	def softScrape(self, url: str) -> ScrapeMeta:
		url = canonizeUrl(url)
		# check if we already have it in our db, return it if we do
		tmpUrl = getLastUrlLike(url)
		if tmpUrl is not None:
			res = getMostRecentScrapeWithMeta(url)
			assert (res is not None)
			return res

		# otherwise call upstream .softCrawl
		apiUrl = urllib.parse.urljoin(self.baseUrl, 'v0/softCrawl')
		res = self._makeRequest(apiUrl, {'q': url})
		if res is None:
			raise Exception(f'SkitterClient.crawl: failed to crawl: {url}')
		saveWebRequest(res['fetched'], res['url'], res['status'], res['raw'])
		return res
