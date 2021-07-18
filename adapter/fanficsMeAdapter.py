import time
import urllib
from typing import Optional, List

from htypes import FicType, FicId
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter, Fandom
import util
import scrape

from adapter.adapter import Adapter

class FanficsMeAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(True,
				'http://fanfics.me', 'fanfics.me',
				FicType.fanficsme)
		self.baseStoryUrl = self.baseUrl + '/read2.php'

	def constructUrl(self, storyId: str, chapterId: int = None) -> str:
		url = self.baseStoryUrl + '?id={}'.format(storyId)
		if chapterId is not None:
			url += '&chapter={}'.format(chapterId - 1)
		return url

	def buildUrl(self, chapter: 'FicChapter') -> str:
		if chapter.fic is None:
			chapter.fic = Fic.lookup((chapter.ficId,))
		return self.constructUrl(chapter.fic.localId, chapter.chapterId)

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		if not url.startswith(self.baseStoryUrl + '?'):
			return None
		qstring = url[len(self.baseStoryUrl + '?'):]

		qs = urllib.parse.parse_qs(qstring)
		if 'id' not in qs or len(qs['id']) != 1:
			return None

		lid = int(qs['id'][0])
		ficId = FicId(self.ftype, str(lid))

		if 'chapter' in qs and len(qs['chapter']) == 1:
			ficId.chapterId = int(qs['chapter'][0])

		return ficId

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)

		# scrape fresh info
		data = scrape.softScrape(fic.url)
		if data is None:
			raise Exception('unable to scrape? FIXME')

		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		return Fic.lookup((fic.id,))

	def extractContent(self, fic: Fic, html: str) -> str:
		# TODO: is this ok? it will never be called if its always prefetched by
		# TODO: getLatest grabbing it without the cid?
		from bs4 import BeautifulSoup # type: ignore
		soup = BeautifulSoup(html, 'html5lib')
		readContent = soup.find('div', { 'class': 'ReadContent' })
		header = readContent.find('h2') # TODO: this is the chapter title
		chapter = readContent.find('div', { 'class': 'chapter' })
		return str(chapter)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		data = scrape.scrape(fic.url)['raw'] # scrape fresh info
		return self.parseInfoInto(fic, data)

	def parseRussianDate(self, datestr: str) -> OilTimestamp:
		parts = datestr.split('.')
		dtstr = '{}.{}.{}'.format(parts[1], parts[0], parts[2])
		uts = util.parseDateAsUnix(dtstr, int(time.time()))
		return OilTimestamp(uts)

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		raise Exception('FIXME TODO fanfics me format has changed')
		from bs4 import BeautifulSoup # type: ignore
		soup = BeautifulSoup(wwwHtml, 'html5lib')

		ficHead = soup.find('div', { 'class': 'FicHead' })

		titleH1 = ficHead.find('h1')
		fic.title = titleH1.getText().strip()

		fandoms: List[str] = []
		trs = ficHead.findAll('div', { 'class': 'tr' })
		author = None
		for tr in trs:
			divTitle = tr.find('div', { 'class': 'title' })
			divContent = tr.find('div', { 'class': 'content' })

			t = str(divTitle.getText()).strip()
			v = str(divContent.getText()).strip()

			if t == 'Автор:':
				author = v
			elif t == 'Фандом:':
				if v == 'Harry Potter' or v == 'Harry Potter - J. K. Rowling':
					fandoms += ['Harry Potter']
				else:
					raise Exception('unknown fandom: ' + v)
			elif t == 'Статус:':
				if v == 'В процессе':
					fic.ficStatus = FicStatus.ongoing
				elif v == 'Закончен':
					fic.ficStatus = FicStatus.complete
				else:
					raise Exception('unknown write status: ' + v)
			elif t == 'Опубликован:':
				fic.published = self.parseRussianDate(v)
			elif t == 'Изменен:':
				fic.updated = self.parseRussianDate(v)
			elif t == 'Ссылка:':
				src = v # source archive url
			elif t == 'Читателей:':
				fic.followCount = int(v)
			elif t == 'Персонажи:':
				# characters, parse relationship?
				pass
			elif t == 'Рейтинг:':
				fic.ageRating = v
			elif t == 'Предупреждения:':
				# warnings?
				pass
			else:
				raise Exception('unknown metadata: ' + t)

		# TODO?
		assert(author is not None)
		authorUrl = author
		authorId = author
		self.setAuthor(fic, author, authorUrl, authorId)

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English") # TODO: don't hard code?

		if fic.url is None:
			fic.url = self.constructUrl(fic.localId)

		summaryTextDiv = soup.find('div', { 'class': 'summary_text' })
		if summaryTextDiv is None:
			summaryTextDiv = soup.find('div', { 'class': 'summary_text_fic3' })
		fic.description = summaryTextDiv.getText()

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		if fic.followCount is None:
			fic.followCount = 0

		fic.ageRating = 'M'

		ficContentsUl = soup.find('ul', { 'class': 'FicContents' })
		chapterLinks = ficContentsUl.findAll('li', { 'class': 't-b-dotted' })
		fic.chapterCount = len(chapterLinks)

		if fic.wordCount is None:
			fic.wordCount = 0
		fic.upsert()

		wordCount = 0
		for cid in range(1, fic.chapterCount + 1):
			chapter = fic.chapter(cid)
			chapter.localChapterId = str(cid)
			chapter.url = self.constructUrl(fic.localId, cid)

			# try to get it out of current blob first
			if chapter.html() is None:
				contentDiv = soup.find('div', { 'id': 'c{}'.format(cid - 1) })
				if contentDiv is not None:
					chapter.setHtml('<div class="ReadContent">' + str(contentDiv) + '</div>')

			if chapter.title is None or len(chapter.title) < 1:
				contentDiv = soup.find('div', { 'id': 'c{}'.format(cid - 1) })
				if contentDiv is not None:
					chapterTitle = contentDiv.previous_sibling
					if chapterTitle is not None and chapterTitle.name == 'h2':
						chapter.title = chapterTitle.getText()

			# fallback to scraping it directly
			if chapter.html() is None:
				cdata = scrape.softScrape(chapter.url)
				assert(cdata is not None)
				chapter.setHtml(self.extractContent(fic, cdata))
				csoup = BeautifulSoup(cdata, 'html5lib')
				contentDiv = csoup.find('div', { 'id': 'c{}'.format(cid - 1) })
				chapterTitle = contentDiv.previous_sibling
				if chapterTitle is not None and chapterTitle.name == 'h2':
					chapter.title = chapterTitle.getText()

			if chapter.title is not None and len(chapter.title) > 0:
				chapter.title = util.cleanChapterTitle(chapter.title, cid)

			chapter.upsert()
			wordCount += len(chapter.cachedContent().split())

		fic.wordCount = wordCount

		for fandom in fandoms:
			fic.add(Fandom.define(fandom))

		return fic

