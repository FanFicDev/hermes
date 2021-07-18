import re
import time
from typing import Optional, List

from htypes import FicType, FicId
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter
import util
import scrape

from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher

class ChapterInfo:
	def __init__(self) -> None:
		self.wordCount = 0
		self.reviewCount = 0
		self.updated: Optional[str] = None

class FanficAuthorsAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(True,
				'https://www.fanficauthors.net', 'fanficauthors.net',
				FicType.fanficauthors)
		self.baseStoryUrl = 'https://{}.fanficauthors.net/{}'

	def constructUrl(self, storyId: str, chapterId: int = None) -> str:
		authorLid = storyId.split('/')[0]
		storyLid = storyId.split('/')[1]
		url = self.baseStoryUrl.format(authorLid, storyLid)
		if chapterId is not None:
			url += '/Chapter_{}/'.format(chapterId)
		else:
			url += '/index/'
		return url

	def buildUrl(self, chapter: 'FicChapter') -> str:
		if chapter.fic is None:
			chapter.fic = Fic.lookup((chapter.ficId,))
		return self.constructUrl(chapter.fic.localId, chapter.chapterId)

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		parts = url.split('/')
		httpOrHttps = (parts[0] == 'https:' or parts[0] == 'http:')
		if len(parts) < 4:
			return None
		if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
			return None

		storyLid = parts[3]
		authorLid = parts[2].split('.')[0]
		lid = '{}/{}'.format(authorLid, storyLid)

		ficId = FicId(self.ftype, lid)

		if len(parts) > 4 and parts[4].startswith('Chapter_'):
			cid = int(parts[4][len('Chapter_'):])
			ficId.chapterId = cid
			ficId.ambiguous = False

		return ficId

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)
		data = scrape.softScrape(fic.url)
		if data is None:
			raise Exception('unable to scrape? FIXME')

		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		return Fic.lookup((fic.id,))

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup # type: ignore
		soup = BeautifulSoup(html, 'html5lib')
		storyChapterDisplay = soup.find('div',
				{'class': ['story', 'chapterDisplay']})

		# remove pager lists
		while True:
			pager = storyChapterDisplay.find('ul', {'class': ['pager', 'center-block']})
			if pager is None:
				break
			pager.extract()

		content = str(storyChapterDisplay)
		return content

	def getCurrentInfo(self, fic: Fic) -> Fic:
		data = scrape.scrape(self.constructUrl(fic.localId))['raw'] # scrape fresh info

		return self.parseInfoInto(fic, data)

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		from bs4 import BeautifulSoup
		authorLid = fic.localId.split('/')[0]
		storyLid = fic.localId.split('/')[1]

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English") # TODO: don't hard code?

		fic.url = self.constructUrl(fic.localId)

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		fic.ageRating = 'M'

		soup = BeautifulSoup(wwwHtml, 'html5lib')

		pageHeader = soup.find('div', {'class': 'page-header'})
		titleH2 = pageHeader.find('h2')
		fic.title = titleH2.getText().strip()

		authorLink = pageHeader.find('a')
		author = authorLink.getText().strip()
		authorId = authorLid
		authorUrl = self.baseStoryUrl.format(authorLid, 'contact/')
		self.setAuthor(fic, author, authorUrl, authorId)

		divWell = soup.find('div', {'class': 'well'})

		summaryQuote = divWell.find('blockquote')

		fic.description = str(summaryQuote.getText()).replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')
		while fic.description.find('  ') != -1:
			fic.description = fic.description.replace('  ', ' ')
		fic.description = fic.description.strip()

		divWellText = divWell.getText().strip()

		match = re.search('Status:\s*([^-]*) -', divWellText)
		if match is not None and match.group(1) == 'In progress':
			fic.ficStatus = FicStatus.ongoing
		else:
			raise Exception('unable to find fic status')

		RegexMatcher(divWellText, {
			'ageRating': ('Rating\s*:\s+([^-]+) -', str),
			'chapterCount': ('Chapters\s*:\s+(\d+) -', int),
			'wordCount': ('Word count\s*:\s+([\d,]+) -', str),
			}).matchAll(fic)
		assert(fic.chapterCount is not None)

		if str(fic.wordCount).find(',') != -1:
			fic.wordCount = int(str(fic.wordCount).replace(',', ''))

		wellParent = divWell.parent
		cid = 0
		wordCount = 0
		reviewCount = 0
		chapterDates: List[int] = []

		for child in wellParent.children:
			if child.name != 'p': continue
			cid += 1
			if str(child).find('Chapter {}'.format(cid)) == -1:
				continue
			chapterLink = child.find('a')
			expectedUrl = '/{}/Chapter_{}/'.format(storyLid, cid).lower()
			if chapterLink.get('href').lower() != expectedUrl:
				raise Exception('unexpected chapter url: ' + chapterLink.get('href'))

			chInfo = ChapterInfo()

			RegexMatcher(child.getText(), {
				'wordCount': ('Word count\s*:\s+([\d,]+) -', str),
				'reviewCount': ('Reviews\s*:\s+([^-]+) -', int),
				'updated': ('Uploaded on\s*:\s+(.+)', str),
				}).matchAll(chInfo)
			assert(chInfo.updated is not None)

			if str(chInfo.wordCount).find(',') != -1:
				chInfo.wordCount = int(str(chInfo.wordCount).replace(',', ''))

			wordCount += chInfo.wordCount
			reviewCount += chInfo.reviewCount

			dt = (util.parseDateAsUnix(chInfo.updated, int(time.time())))
			chapterDates += [dt]

		# wordCount is already set from overall metadata
		fic.reviewCount = reviewCount

		fic.published = OilTimestamp(min(chapterDates))
		fic.updated = OilTimestamp(max(chapterDates))

		fic.upsert()
		for cid in range(1, fic.chapterCount + 1):
			ch = fic.chapter(cid)
			ch.localChapterId = 'Chapter_{}'.format(cid)
			ch.url = self.constructUrl(fic.localId, cid)
			ch.upsert()

		return fic


