from typing import Optional
import re
import time
import urllib

from adapter.adapter import Adapter, edumpContent
from adapter.regex_matcher import RegexMatcher
from htypes import FicId, FicType
import scrape
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util


class HpFanficArchiveAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(
			True, 'http://www.hpfanficarchive.com/stories/', 'hpfanficarchive.com',
			FicType.hpfanficarchive
		)
		self.baseStoryUrl = 'http://www.hpfanficarchive.com/stories/viewstory.php'
		self.baseDelay = 5

	def constructUrl(self, lid: str, cid: Optional[int] = None) -> str:
		if cid is None:
			return f'{self.baseStoryUrl}?sid={lid}'
		return f'{self.baseStoryUrl}?sid={lid}&chapter={cid}'

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		if url.startswith("https://"):
			url = "http://" + url[len("https://"):]
		url = url.replace(
			'http://hpfanficarchive.com', 'http://www.hpfanficarchive.com'
		)
		if not url.startswith(self.baseStoryUrl):
			return None
		leftover = url[len(self.baseStoryUrl):]
		if not leftover.startswith('?'):
			return None
		leftover = leftover[1:]

		qs = urllib.parse.parse_qs(leftover)
		if 'sid' not in qs or len(qs['sid']) != 1:
			return None

		ficId = FicId(self.ftype, str(int(qs['sid'][0])))

		if 'chapter' in qs and len(qs['chapter']) == 1:
			ficId.chapterId = int(qs['chapter'][0])

		return ficId

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)

		# scrape fresh info
		data = scrape.scrape(fic.url)
		time.sleep(self.baseDelay)

		edumpContent(data['raw'], 'hpffa')

		fic = self.parseInfoInto(fic, data['raw'])
		fic.upsert()

		return Fic.lookup((fic.id, ))

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html.parser')
		mainpage = soup.find(id='mainpage')
		if mainpage is None:
			edumpContent(html, 'hpffa_ec')
			raise Exception('unable to find mainpage, e-dumped')

		blocks = mainpage.findAll('div', {'class': 'block'})
		for block in blocks:
			title = block.find('div', {'class': 'title'})
			if title is not None and title.contents[0] == 'Story':
				content = block.find('div', {'class': 'content'})
				if content is not None:
					return str(content)

		edumpContent(html, 'hpffa_ec')
		raise Exception('unable to find content, e-dumped')

	def buildUrl(self, chapter: 'FicChapter') -> str:
		if len(chapter.url.strip()) > 0:
			return chapter.url
		return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		url = self.constructUrl(fic.localId)
		# scrape fresh info
		data = scrape.scrape(url)
		time.sleep(self.baseDelay)

		edumpContent('<!-- {} -->\n{}'.format(url, data['raw']), 'hpffa_ec')
		return self.parseInfoInto(fic, data['raw'])

	def parseInfoInto(self, fic: Fic, html: str) -> Fic:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html.parser')

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")  # TODO: don't hard code?

		pagetitle = soup.find(id='pagetitle')
		aTags = pagetitle.findAll('a')
		author = None
		for a in aTags:
			href = a.get('href')
			if href.startswith('viewstory'):
				fic.title = a.contents[0].strip()
			elif href.startswith('viewuser.php?uid='):
				author = a.contents[0]
				authorUrl = self.baseUrl + href
				authorId = str(int(href[len('viewuser.php?uid='):]))
				self.setAuthor(fic, author, authorUrl, authorId)

		if fic.title is None:
			raise Exception('unable to find title')
		if author is None:
			raise Exception('unable to find author')

		lines = html.replace('\r', '\n').replace('<', '\n<').split('\n')
		inDescription = False
		description = ''
		for line in lines:
			cur = line.strip()
			if cur.find('!-- SUMMARY START --') != -1:
				inDescription = True
			elif cur.find('!-- SUMMARY END --') != -1:
				inDescription = False

			if inDescription == True:
				description += cur + '\n'

		fic.description = description

		fic.ageRating = '<unkown>'

		infoBlock = None
		infoText = None
		blocks = soup.findAll('div', {'class': 'block'})
		for block in blocks:
			title = block.find('div', {'class': 'title'})
			if title is None:
				continue
			if title.contents[0] != 'Story Information':
				continue
			infoBlock = block
			infoText = block.get_text()
			break
		else:
			raise Exception('unable to find info text')

		matcher = RegexMatcher(
			infoText, {
				'chapterCount': ('Chapters:\s+(\d+)', int),
				'wordCount': ('Word count:\s+(\S+)', int),
			}
		)
		matcher.matchAll(fic)

		sortDiv = soup.find(id='sort')
		match = re.search('Reviews\s*-\s*([^\]]+)', sortDiv.get_text())
		if match is not None:
			fic.reviewCount = int(match.group(1).replace(',', ''))
		else:
			fic.reviewCount = 0

		fic.favoriteCount = 0
		fic.followCount = 0

		infoBlockHtml = str(infoBlock)
		match = re.search(
			'<!-- PUBLISHED START -->([^<]*)<!-- PUBLISHED END -->', infoBlockHtml
		)
		if match is not None:
			publishedUts = util.parseDateAsUnix(match.group(1), fic.fetched)
			fic.published = OilTimestamp(publishedUts)

		match = re.search(
			'<!-- UPDATED START -->([^<]*)<!-- UPDATED END -->', infoBlockHtml
		)
		if match is not None:
			updatedUts = util.parseDateAsUnix(match.group(1), fic.fetched)
			fic.updated = OilTimestamp(updatedUts)

		if fic.updated is None:
			fic.updated = fic.published

		match = re.search('Completed:\s+(\S+)', infoText)
		if match is not None:
			complete = match.group(1)
			if complete == 'No':
				fic.ficStatus = FicStatus.ongoing
			elif complete == 'Yes':
				fic.ficStatus = FicStatus.complete
			else:
				raise Exception(f'unknown complete value: {complete}')

		match = re.search('Crossovers', infoText)
		if match is not None:
			pass  # raise Exception('Found unknown crossover in {0}: {1}'.format(fic.id, fic.url))
		else:
			# otherwise not a crossover and just harry potter
			fic.add(Fandom.define('Harry Potter'))

		return fic
