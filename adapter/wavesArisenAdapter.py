from typing import List
import re
import time
import dateutil.parser

from htypes import FicType, FicId
from store import OilTimestamp, Language, Fic, FicStatus, FicChapter, Fandom
import util
import scrape

from adapter.adapter import Adapter, edumpContent


class WavesArisenAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(
			True, 'https://wertifloke.wordpress.com', 'wertifloke.wordpress.com',
			FicType.wavesarisen
		)
		self.tocUrl = '{}/table-of-contents'.format(self.baseUrl)

	def canonizeUrl(self, url: str) -> str:
		url = scrape.canonizeUrl(url)
		prefixMap = [
			('http://', 'https://'),
			('https://www.', 'https://'),
		]
		for pm in prefixMap:
			if url.startswith(pm[0]):
				url = pm[1] + url[len(pm[0]):]
		return url

	def getChapterUrls(self, data: str = None) -> List[str]:
		from bs4 import BeautifulSoup  # type: ignore
		if data is None:
			data = scrape.softScrape(self.tocUrl)
		soup = BeautifulSoup(data, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		chapterUrls: List[str] = []
		for entryContent in entryContents:
			aTags = entryContent.findAll('a')
			for aTag in aTags:
				if aTag.get('href') is None:
					continue
				href = self.canonizeUrl(aTag.get('href'))
				if href in chapterUrls:
					continue
				chapterUrls += [href]
		return chapterUrls

	def getChapterPublishDate(self, url: str) -> OilTimestamp:
		from bs4 import BeautifulSoup
		url = self.canonizeUrl(url)
		data = scrape.softScrape(url)
		soup = BeautifulSoup(data, 'html5lib')
		publishTimes = soup.findAll('time', {'class': ['entry-date', 'published']})
		if len(publishTimes) != 1:
			raise Exception('cannot find publish time for {}'.format(url))
		uts = util.dtToUnix(dateutil.parser.parse(publishTimes[0].get('datetime')))
		return OilTimestamp(uts)

	def constructUrl(self, lid: str, cid: int = None) -> str:
		if cid is None:
			return self.baseUrl
		chapterUrls = self.getChapterUrls()
		return chapterUrls[cid - 1]

	def tryParseUrl(self, url: str) -> FicId:
		url = self.canonizeUrl(url)

		# if the url matches a chapter url, return it
		chapterUrls = self.getChapterUrls()
		if url in chapterUrls:
			return FicId(self.ftype, str(3), chapterUrls.index(url), False)

		# parahumans is id 3
		# TODO: change FicType.wavesarisen to wordpress?
		return FicId(self.ftype, str(3), ambiguous=False)

	def create(self, fic: Fic) -> Fic:
		return self.getCurrentInfo(fic)

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		if len(entryContents) != 1:
			return 'TODO'  # TODO
			raise Exception('cannot find entry-content')
		entryContent = entryContents[0]

		for script in entryContent.findAll('script'):
			script.decompose()

		content = str(entryContent)
		patt = "<a href=['\"]https?://(www.)wertifloke.wordpress.com[^'\"]*['\"]>(Last|Previous|Next) [Cc]hapter</a>"
		return re.sub(patt, '', content)

	def buildUrl(self, chapter: FicChapter) -> str:
		if len(chapter.url.strip()) > 0:
			return chapter.url
		return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)
		url = self.tocUrl
		data = scrape.scrape(url)
		edumpContent('<!-- {} -->\n{}'.format(url, data['raw']), 'wavesarisen_ec')

		fic = self.parseInfoInto(fic, data['raw'])
		fic.upsert()
		return Fic.lookup((fic.id, ))

	def parseInfoInto(self, fic: Fic, html: str) -> Fic:
		from bs4 import BeautifulSoup
		html = html.replace('\r\n', '\n')
		soup = BeautifulSoup(html, 'html.parser')

		# wooh hardcoding
		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")

		fic.title = 'The Waves Arisen'
		fic.ageRating = 'M'

		self.setAuthor(
			fic, 'wertifloke', 'https://wertifloke.wordpress.com/', str(2)
		)

		# taken from https://www.parahumans.net/about/
		fic.description = '''
A young Naruto found refuge in the village library, and grew up smart, but by blood he is Ninja, and what place is there for curiosity and calculation in this brutal world of warring states?

The Waves Arisen is a complete novel-length work of Rationalist Naruto Fanfiction. No prior knowledge of the Naruto universe is necessary to follow along. '''

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

		if oldChapterCount is None or fic.chapterCount > oldChapterCount:
			fic.wordCount = 0
		if fic.wordCount == 0:
			fic.upsert()
			for cid in range(1, fic.chapterCount + 1):
				c = fic.chapter(cid)
				c.cache()
				chtml = c.html()
				if chtml is not None:
					fic.wordCount += len(chtml.split())

		fic.add(Fandom.define('Naruto'))
		# TODO: chars/relationship?

		return fic
