from typing import Dict, List, Optional, Tuple, Union, cast
import re
import urllib

import dateutil.parser

from adapter.adapter import Adapter
from htypes import FicId, FicType
import scrape
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util


class WordpressAdapter(Adapter):
	def __init__(
		self,
		baseUrl: str,
		urlFragments: Union[str, List[str]],
		ftype: FicType,
		title: str,
		fandom: str,
		ageRating: str,
		author: str,
		authorUrl: str,
		description: str,
		contentRe: Tuple[str, str],
	) -> None:
		super().__init__(True, baseUrl, urlFragments, ftype)

		self.title = title
		self.fandom = fandom
		self.ageRating = ageRating
		self.author = author
		self.authorUrl = authorUrl
		self.description = description

		self.contentRe = contentRe

		self.tocUrl = f'{self.baseUrl}/table-of-contents'

		# map from source url to real url, or none if it should be skipped
		self.urlFixups: Dict[str, Optional[str]] = {}
		# map from source title to what appears just before it and what it should
		# be replaced with, combining the key and val.0 into val.1
		self.titleFixups: Dict[str, Tuple[str, str]] = {}

	def canonizeUrl(self, url: str) -> str:
		url = urllib.parse.urljoin(self.baseUrl, url)
		url = scrape.canonizeUrl(url)
		prefixMap = [
			('http://', 'https://'),
			(
				f'https://{self.urlFragments[0]}', f'https://www.{self.urlFragments[0]}'
			),
		]
		for pm in prefixMap:
			if url.startswith(pm[0]):
				url = pm[1] + url[len(pm[0]):]
		if not url.endswith('/'):
			url += '/'
		return url

	def getChapterUrls(self, data: Optional[str] = None) -> List[str]:
		from bs4 import BeautifulSoup
		if data is None:
			data = scrape.softScrape(self.tocUrl)
		soup = BeautifulSoup(data, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		chapterUrls: List[str] = []

		for entryContent in entryContents:
			aTags = entryContent.findAll('a')
			for aTag in aTags:
				href = self.canonizeUrl(aTag.get('href'))
				if (
					href in self.urlFixups and len(chapterUrls) > 0
					and chapterUrls[-1] == href
				):
					if self.urlFixups[href] is None:
						continue
					href = cast(str, self.urlFixups[href])
				if href in chapterUrls:
					raise Exception(f'duplicate chapter url: {href} {len(chapterUrls)}')
				chapterUrls += [href]
		return chapterUrls

	def getChapterTitles(self, data: Optional[str] = None) -> List[str]:
		from bs4 import BeautifulSoup
		if data is None:
			data = scrape.softScrape(self.tocUrl)
		soup = BeautifulSoup(data, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		chapterTitles: List[str] = []

		for entryContent in entryContents:
			aTags = entryContent.findAll('a')
			for aTag in aTags:
				content = aTag.get_text().strip()
				if (
					content in self.titleFixups and len(chapterTitles) > 0
					and chapterTitles[-1] == self.titleFixups[content][0]
				):
					chapterTitles[-1] = self.titleFixups[content][1]
					continue
				chapterTitles += [content]
		return chapterTitles

	def getChapterPublishDate(self, url: str) -> OilTimestamp:
		from bs4 import BeautifulSoup
		url = self.canonizeUrl(url)
		data = scrape.softScrape(url)
		soup = BeautifulSoup(data, 'html5lib')
		publishTimes = soup.findAll('time', {'class': ['entry-date', 'published']})
		if len(publishTimes) != 1:
			raise Exception(f'cannot find publish time for {url}')
		uts = util.dtToUnix(dateutil.parser.parse(publishTimes[0].get('datetime')))
		return OilTimestamp(uts)

	def constructUrl(self, lid: str, cid: Optional[int] = None) -> str:
		if cid is None:
			return self.baseUrl
		chapterUrls = self.getChapterUrls()
		return chapterUrls[cid - 1]

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		url = self.canonizeUrl(url)

		# if the url matches a chapter url, return it
		chapterUrls = self.getChapterUrls()
		if url in chapterUrls:
			return FicId(self.ftype, str(1), chapterUrls.index(url), False)

		# TODO: we should not rely on a single ftype with localId per story
		return FicId(self.ftype, str(1), ambiguous=False)

	def create(self, fic: Fic) -> Fic:
		return self.getCurrentInfo(fic)

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		if len(entryContents) != 1:
			raise Exception('cannot find entry-content')
		entryContent = entryContents[0]

		shareDivs = entryContent.find_all('div', {'class', 'sharedaddy'})
		for shareDiv in shareDivs:
			shareDiv.extract()

		for audio in entryContent.find_all('audio'):
			audio.extract()

		content = str(entryContent)
		# TODO: generalize contentRe
		return re.sub(self.contentRe[0], self.contentRe[1], content)

	def buildUrl(self, chapter: FicChapter) -> str:
		if len(chapter.url.strip()) > 0:
			return chapter.url
		return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)
		url = self.tocUrl
		data = scrape.scrape(url)

		fic = self.parseInfoInto(fic, data['raw'])
		fic.upsert()
		return Fic.lookup((fic.id, ))

	def parseInfoInto(self, fic: Fic, html: str) -> Fic:
		html = html.replace('\r\n', '\n')

		# wooh hardcoding
		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")

		fic.title = self.title
		fic.ageRating = self.ageRating

		self.setAuthor(fic, self.author, self.authorUrl, str(1))

		# taken from https://www.parahumans.net/about/
		fic.description = self.description

		chapterUrls = self.getChapterUrls(html)
		oldChapterCount = fic.chapterCount
		fic.chapterCount = len(chapterUrls)

		# TODO?
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		if fic.ficStatus is None or fic.ficStatus == FicStatus.broken:
			fic.ficStatus = FicStatus.ongoing

		fic.published = self.getChapterPublishDate(chapterUrls[0])
		fic.updated = self.getChapterPublishDate(chapterUrls[-1])

		titles = self.getChapterTitles()

		if oldChapterCount is None or fic.chapterCount > oldChapterCount:
			fic.wordCount = 0
		fic.wordCount = 0
		if fic.wordCount == 0:
			fic.upsert()
			# save urls and title first...
			for cid in range(1, fic.chapterCount + 1):
				c = fic.chapter(cid)
				c.localChapterId = str(cid)
				c.url = chapterUrls[cid - 1]
				if cid <= len(titles):
					c.title = titles[cid - 1]
				elif c.title is None:
					c.title = ''
				c.upsert()

			# then attempt to set content
			for cid in range(1, fic.chapterCount + 1):
				c = fic.chapter(cid)
				c.cache()
				chtml = c.html()
				c.upsert()
				if chtml is not None:
					fic.wordCount += len(chtml.split())

		fic.add(Fandom.define(self.fandom))
		# TODO: chars/relationship?

		return fic
