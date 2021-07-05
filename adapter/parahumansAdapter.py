import re
from typing import List, Optional, cast
import time
import dateutil.parser
import urllib

from htypes import FicType, FicId
from store import OilTimestamp, Language, Fic, FicStatus, FicChapter, Fandom
import util
import scrape

from adapter.adapter import Adapter, edumpContent

class ParahumansAdapter(Adapter):
	def __init__(self) -> None:
		# https://www.parahumans.net/table-of-contents/
		super().__init__(True,
				'https://www.parahumans.net', 'parahumans.net',
				FicType.parahumans)
		self.tocUrl = '{}/table-of-contents'.format(self.baseUrl)

	def canonizeUrl(self, url: str) -> str:
		url = urllib.parse.urljoin(self.baseUrl, url)
		url = scrape.canonizeUrl(url)
		prefixMap = [ ('http://', 'https://'),
				('https://{}'.format(self.urlFragments[0])
				,'https://www.{}'.format(self.urlFragments[0])) ]
		for pm in prefixMap:
			if url.startswith(pm[0]):
				url = pm[1] + url[len(pm[0]):]
		if not url.endswith('/'):
			url += '/'
		return url

	def getChapterUrls(self, data: str = None) -> List[str]:
		from bs4 import BeautifulSoup # type: ignore
		if data is None:
			data = scrape.softScrape(self.tocUrl)
		soup = BeautifulSoup(data, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		chapterUrls: List[str] = []

		urlFixups = {
				self.canonizeUrl('/2018/11/24/interlude-10-x'): None,
				self.canonizeUrl('/2018/12/11/interlude-10-y'): None,
				self.canonizeUrl('/2019/04/27/black-13-8'):
				 self.canonizeUrl('/2019/04/30/black-13-x'),
			}

		for entryContent in entryContents:
			aTags = entryContent.findAll('a')
			for aTag in aTags:
				href = self.canonizeUrl(aTag.get('href'))
				if href in urlFixups \
						and len(chapterUrls) > 0 and chapterUrls[-1] == href:
					if urlFixups[href] is None:
						continue
					href = cast(str, urlFixups[href])
				if href in chapterUrls:
					raise Exception(f'duplicate chapter url: {href} {len(chapterUrls)}')
				chapterUrls += [href]
		return chapterUrls

		for entryContent in entryContents:
			aTags = entryContent.findAll('a')
			for aTag in aTags:
				href = self.canonizeUrl(aTag.get('href'))
				if href == 'https://www.parahumans.net/2018/11/24/interlude-10-x' \
						and len(chapterUrls) > 0 and chapterUrls[-1] == href:
					continue
				if href == 'https://www.parahumans.net/2018/12/11/interlude-10-y' \
						and len(chapterUrls) > 0 and chapterUrls[-1] == href:
					continue
				if href == 'https://www.parahumans.net/2019/04/27/black-13-8' \
						and len(chapterUrls) > 0 and chapterUrls[-1] == href:
					href = 'https://www.parahumans.net/2019/04/30/black-13-x'
				if href in chapterUrls:
					raise Exception(f'duplicate chapter url: {href} {len(chapterUrls)}')
				chapterUrls += [href]
		return chapterUrls

	def getChapterTitles(self, data: str = None) -> List[str]:
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
				if content == '(Tats)' \
						and len(chapterTitles) > 0 and chapterTitles[-1] == '10.x':
					chapterTitles[-1] = '10.x (Tats)'
					continue
				if content == '(Boy in the shell)' \
						and len(chapterTitles) > 0 and chapterTitles[-1] == '10.y':
					chapterTitles[-1] = '10.y (Boy in the shell)'
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
			raise Exception('cannot find publish time for {}'.format(url))
		uts = util.dtToUnix(dateutil.parser.parse(publishTimes[0].get('datetime')))
		return OilTimestamp(uts)

	def constructUrl(self, lid: str, cid: int = None) -> str:
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

		# parahumans is id 1
		# TODO: change FicType.parahumans to wordpress?
		return FicId(self.ftype, str(1), ambiguous=False)

	def create(self, fic: Fic) -> Fic:
		return self.getCurrentInfo(fic)

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html5lib')
		entryContents = soup.findAll('div', {'class': 'entry-content'})
		if len(entryContents) != 1:
			edumpContent(html, 'parahumans_ec')
			raise Exception('cannot find entry-content')
		entryContent = entryContents[0]

		shareDivs = entryContent.find_all('div', {'class', 'sharedaddy'})
		for shareDiv in shareDivs:
			shareDiv.extract()

		content = str(entryContent)
		patt = "<a href=['\"]https?://(www.)parahumans.net[^'\"]*['\"]>(Last|Previous|Next) Chapter</a>"
		return re.sub(patt, '', content)

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
		return Fic.lookup((fic.id,))

	def parseInfoInto(self, fic: Fic, html: str) -> Fic:
		from bs4 import BeautifulSoup
		html = html.replace('\r\n', '\n')
		soup = BeautifulSoup(html, 'html.parser')

		# wooh hardcoding
		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")

		fic.title = 'Ward'
		fic.ageRating = 'M'

		self.setAuthor(fic,
				'Wildbow', 'https://www.parahumans.net/support-wildbow', str(1))

		# taken from https://www.parahumans.net/about/
		fic.description = '''
The unwritten rules that govern the fights and outright wars between ‘capes’ have been amended: everyone gets their second chance.  It’s an uneasy thing to come to terms with when notorious supervillains and even monsters are playing at being hero.  The world ended two years ago, and as humanity straddles the old world and the new, there aren’t records, witnesses, or facilities to answer the villains’ past actions in the present.  One of many compromises, uneasy truces and deceptions that are starting to splinter as humanity rebuilds.

None feel the injustice of this new status quo or the lack of established footing more than the past residents of the parahuman asylums.  The facilities hosted parahumans and their victims, but the facilities are ruined or gone; one of many fragile ex-patients is left to find a place in a fractured world.  She’s perhaps the person least suited to have anything to do with this tenuous peace or to stand alongside these false heroes.  She’s put in a position to make the decision: will she compromise to help forge what they call, with dark sentiment, a second golden age?  Or will she stand tall as a gilded dark age dawns?'''

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
			# save urls first...
			for cid in range(1, fic.chapterCount + 1):
				c = fic.chapter(cid)
				c.localChapterId = str(cid)
				c.url = chapterUrls[cid - 1]
				c.upsert()

			# then attempt to set title and content
			for cid in range(1, fic.chapterCount + 1):
				if cid <= len(titles):
					c.title = titles[cid - 1]
				elif c.title is None:
					c.title = ''
				c.cache()
				chtml = c.html()
				c.upsert()
				if chtml is not None:
					fic.wordCount += len(chtml.split())

		fic.add(Fandom.define('Worm'))
		# TODO: chars/relationship?

		return fic

	def softScrape(self, chapter: FicChapter) -> Optional[str]:
		import scrape
		html = scrape.softScrape(chapter.url)
		if html is None:
			return html
		# TODO well this is a nightmare...
		if html.find('You are being redirected') < 0:
			return html

		import re
		match = re.search("window.location = ['\"]([^'\"]*)['\"];", html)
		if match is None or match.group(1) is None:
			return html

		if chapter.url == match.group(1):
			raise Exception('redirect loop')

		chapter.url = match.group(1)
		chapter.upsert()
		return self.softScrape(chapter)

