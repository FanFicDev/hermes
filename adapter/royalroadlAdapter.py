import re
import time
import urllib
from typing import Optional, List

from htypes import FicType, FicId
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter
import util
import scrape
import skitter
from view import HtmlView

from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher

class RoyalRoadlAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(True,
				'https://www.royalroad.com', ['royalroad.com', 'royalroadl.com'],
				FicType.royalroadl)
		self.baseStoryUrl = self.baseUrl + '/fiction/'

	def constructUrl(self, storyId: str, chapterId: int = None) -> str:
		if chapterId is None:
			return '{}{}'.format(self.baseStoryUrl, storyId)
		# TODO: lookup url in existing chapters?
		raise NotImplementedError()

	def buildUrl(self, chapter: 'FicChapter') -> str:
		if len(chapter.url.strip()) == 0:
			raise NotImplementedError()
		return chapter.url

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		url = url.replace('royalroadl.com', 'royalroad.com')
		url = url.replace('https://royalroad.com', self.baseUrl)
		url = url.replace('http://', 'https://')
		if not url.startswith(self.baseStoryUrl):
			return None

		# TODO: is fiction a replacable category?
		# url like /fiction/{storyId}/{story name slug}
		# then optionally /chapter/{localChapterId}/{chapter title slug}
		rest = url[len(self.baseStoryUrl):]
		parts = rest.split('/')

		lid = int(parts[0])
		localChapterId = None

		if len(parts) > 2 and parts[1] == 'chapter':
			localChapterId = int(parts[2])
			return FicId(self.ftype, str(lid), localChapterId, False)

		return FicId(self.ftype, str(lid))

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)

		data = self.softScrapeUrl(fic.url)
		if data is None:
			raise Exception('unable to scrape? FIXME')

		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		return Fic.lookup((fic.id,))

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup # type: ignore
		soup = BeautifulSoup(html, 'html5lib')
		content = soup.find('div', { 'class': 'chapter-content' })
		return str(content)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		# FIXME when fics are deleted they 404:
		# https://www.royalroad.com/fiction/38947/
		# 404
		# Page Not Found
		# The server has returned the following error:
		# This fiction has been deleted
		fic.url = self.constructUrl(fic.localId)

		data = self.scrape(fic.url)
		if 'raw' not in data:
			raise Exception('unable to scrape? FIXME')
		raw = data['raw']

		return self.parseInfoInto(fic, raw)

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(wwwHtml, 'html5lib')

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English") # TODO: don't hard code?

		fic.url = self.constructUrl(fic.localId)

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		fic.ageRating = 'M' # TODO?

		ficTitleDiv = soup.find('div', { 'class': 'fic-title' })
		fic.title = ficTitleDiv.find('h1').getText().strip()

		authorLink = ficTitleDiv.find('h4', {'property': 'author'}).find('a')
		author = authorLink.getText().strip()
		authorUrl = self.baseUrl + authorLink.get('href')
		authorId = authorUrl.split('/')[-1]
		self.setAuthor(fic, author, authorUrl, authorId)

		divDescription = soup.find('div', {'class': 'description'})
		try:
			descView = HtmlView(str(divDescription), markdown=False)
			desc = ''.join(['<p>{}</p>'.format(l) for l in descView.text])
			fic.description = desc
		except:
			fic.description = divDescription.getText().strip()

		fictionInfo = str(soup.find('div', {'class': 'fiction-info'}))
		if fictionInfo.find('>ONGOING<') != -1:
			fic.ficStatus = FicStatus.ongoing
		elif fictionInfo.find('>COMPLETED<') != -1:
			fic.ficStatus = FicStatus.complete
		elif fictionInfo.find('>HIATUS<') != -1:
			fic.ficStatus = FicStatus.ongoing # TODO?
		elif fictionInfo.find('>STUB<') != -1:
			fic.ficStatus = FicStatus.ongoing # TODO?
		elif fictionInfo.find('>DROPPED<') != -1:
			fic.ficStatus = FicStatus.abandoned
		else:
			raise Exception('unable to find fic status')

		divStatsContent = soup.find('div', {'class': 'stats-content'})
		followers = divStatsContent.find(text='Followers :')
		ul = followers.parent.parent

		RegexMatcher(ul.getText(), {
			'followCount?': ('Followers\s+:\s+([\d,]+)', str),
			'favoriteCount?': ('Favorites\s+:\s+([\d,]+)', str),
			}).matchAll(fic)

		if str(fic.followCount).find(','):
			fic.followCount = int(str(fic.followCount).replace(',', ''))
		if str(fic.favoriteCount).find(','):
			fic.favoriteCount = int(str(fic.favoriteCount).replace(',', ''))


		tableChapters = soup.find('table', {'id': 'chapters'})
		chapterLinks = tableChapters.findAll('a')

		chapterUrls: List[str] = []
		chapterTitles: List[str] = []
		for chapterLink in chapterLinks:
			# TODO FIXME is this inverted?
			if chapterLink.find('time') is not None:
				continue
			chapterUrls += [chapterLink.get('href')]
			chapterTitles += [chapterLink.getText().strip()]

		chapterDates: List[int] = []
		for chapterLink in chapterLinks:
			if chapterLink.find('time') is None:
				continue
			timeElement = chapterLink.find('time')
			if timeElement.get('unixtime'):
				chapterDates += [int(timeElement.get('unixtime'))]
			else:
				chapterDates += [
						util.parseDateAsUnix(timeElement.get('title'), fic.fetched)
					]

		fic.published = OilTimestamp(min(chapterDates))
		fic.updated = OilTimestamp(max(chapterDates))
		fic.chapterCount = len(chapterUrls)

		if fic.wordCount is None:
			fic.wordCount = 0
		fic.upsert()

		for cid in range(1, fic.chapterCount + 1):
			chapter = fic.chapter(cid)
			chapter.url = self.baseUrl + chapterUrls[cid - 1]
			if chapterUrls[cid - 1].startswith('/fiction/chapter/'):
				# alternate chapter syntax if the chapter itself has no slug
				# /fiction/chapter/<lcid>fid=<lid>&fslug=<fic slug>
				chapter.localChapterId = (
					chapterUrls[cid - 1].split('/')[3].split('?')[0]
				)
			else:
				# standard chapter syntax
				# /fiction/<lid>/<fic slug>/chapter/<lcid>/<chapter slug>
				chapter.localChapterId = chapterUrls[cid - 1].split('/')[5]
			chapter.title = chapterTitles[cid - 1]

			if chapter.title is not None and len(chapter.title) > 0:
				chapter.title = util.cleanChapterTitle(chapter.title, cid)

			chapter.upsert()

		wordCount = 0
		for cid in range(1, fic.chapterCount + 1):
			chapter = fic.chapter(cid)
			if chapter.html() is None:
				chapter.cache()

			chapter.upsert()
			chtml = chapter.html()
			if chtml is not None:
				wordCount += len(chtml.split())

		fic.wordCount = wordCount

		return fic

	def scrape(self, url: str) -> scrape.ScrapeMeta:
		return skitter.scrape(url, fallback=True)

	def softScrapeUrl(self, origUrl: str) -> Optional[str]:
		url = origUrl
		lurl = scrape.getLastUrlLike(url)
		if lurl is not None:
			url = lurl

		data = skitter.softScrape(url, fallback=True)
		if 'raw' in data:
			return str(data['raw'])
		return None

	# get the most recent scrape for a chapter, or scrape it fresh
	def softScrape(self, chapter: FicChapter) -> Optional[str]:
		curl = self.buildUrl(chapter)
		return self.softScrapeUrl(curl)

