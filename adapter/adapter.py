import os
import time

from typing import List, Optional, Union
from htypes import FicType, FicId
from store import OilTimestamp, Author, AuthorSource, Fic, FicChapter

edumpContentDir = './edump/'


def edumpContent(html: str, which: str) -> None:
	import util
	util.unslurp(html, f'{which}_content.html', edumpContentDir)

	# TODO this is a hacky workaround for shared log files
	fname = os.path.join(edumpContentDir, f'{which}_content.html')
	try:
		os.chmod(fname, 0o666)  # rw-rw-rw-
	except:
		pass


# used to extract specific pieces from raw page content
class Adapter(object):
	def __init__(
		self,
		cacheable: bool,
		baseUrl: str,
		urlFragments: Union[str, List[str]] = [],
		ftype: FicType = FicType.broken,
		botLinkSuffix: str = None
	):
		self.cacheable = cacheable
		self.baseUrl = baseUrl
		self.urlFragments = urlFragments
		self.ftype = ftype
		self.botLinkSuffix = botLinkSuffix
		if isinstance(self.urlFragments, str):
			self.urlFragments = [self.urlFragments]

	# try to parse a url into a FicId
	def tryParseUrl(self, url: str) -> Optional[FicId]:
		# by default, we simply try to look up the url in existing chapters or fics
		chaps = FicChapter.select({'url': url})
		if len(chaps) == 1:
			fic = Fic.get((chaps[0].ficId, ))
			if fic is not None:
				return FicId(
					FicType(fic.sourceId), fic.localId, chaps[0].chapterId, False
				)

		fics = Fic.select({'url': url})
		if len(fics) == 1:
			return FicId(FicType(fics[0].sourceId), fics[0].localId)

		raise NotImplementedError()

	# return a Fic of this type, get info in needed
	# probably don't need to override this specifically
	def get(self, localId: str) -> Fic:
		existing = Fic.select({'sourceId': self.ftype, 'localId': localId})
		if len(existing) == 1:
			return existing[0]
		if not self.cacheable:
			raise Exception('cannot cache {}/{}'.format(localId, self.ftype))

		fic = Fic.new()
		fic.sourceId = self.ftype
		fic.localId = localId
		fic.created = OilTimestamp.now()
		return self.create(fic)

	# do any work needed to fully create fic
	def create(self, fic: Fic) -> Fic:
		raise NotImplementedError()

	# extract the html text which contains the story itself
	def extractContent(self, fic: Fic, html: str) -> str:
		raise NotImplementedError()

	# build a url from a FicChapter
	# TODO: should this be pretty or not?
	# TODO: many of these can be deduped to constructUrl -- new base?
	def buildUrl(self, chapter: 'FicChapter') -> str:
		if len(chapter.url.strip()) == 0:
			raise NotImplementedError()
		return chapter.url

	# get current info for fic
	def getCurrentInfo(self, fic: Fic) -> Fic:
		raise NotImplementedError()

	# helper method to get last scraped url like a list or a default
	def getLastLikeOrDefault(self, likes: List[str], default: str) -> str:
		import scrape
		for like in likes:
			u = scrape.getLastUrlLike(like)
			if u is not None:
				return u
		return default

	# get the most recent scrape for a chapter, or scrape it fresh
	def softScrape(self, chapter: FicChapter) -> Optional[str]:
		import scrape
		return scrape.softScrape(chapter.url)

	# define the author and author source and attach it to the Fic
	def setAuthor(
		self, fic: Fic, author: str, authorUrl: str, authorLocalId: str
	) -> None:
		fic.authorId = Author.getId(author, self.ftype)
		AuthorSource.getId(
			fic.authorId, self.ftype, author, authorUrl, authorLocalId
		)


class ManualAdapter(Adapter):
	def __init__(
		self,
		baseUrl: str,
		urlFragments: Union[str, List[str]] = [],
		ftype: FicType = FicType.manual
	):
		super().__init__(False, baseUrl, urlFragments, ftype)

	def extractContent(self, fic: Fic, html: str) -> str:
		return html  # assume it's already been done
