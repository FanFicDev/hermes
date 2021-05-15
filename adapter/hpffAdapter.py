import re
import math
import gzip
import time
from typing import Optional, List, Dict
import util
from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher
from htypes import FicId, FicType
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter, Fandom

class HarryPotterFanfictionAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(False,
				'https://harrypotterfanfiction.com',
				[ 'harrypotterfanfiction.com', 'fanfictionworld.net' ],
				FicType.harrypotterfanfiction, 'hpff')
		self.storyPrefix = '/viewstory.php?psid='
		self.chapterPrefix = '/viewstory.php?chapterid='
		self.archivePath = '/srv/{}'.format(self.urlFragments[0])
		self.storyMapPath = self.archivePath + '/' + 'story_map.gz'
		self.chapterMapPath = self.archivePath + '/' + 'chapter_map.gz'
		self.encoding = 'ISO-8859-1'

	def getArchiveStoryInfo(self, storyId: int) -> List[str]:
		# format is: storyId:author:story
		matching: List[List[str]] = []
		with gzip.open(self.storyMapPath, 'rb') as f:
			for l in f.readlines():
				line = l.decode('utf-8')[:-1]
				parts = line.split(':')
				if int(parts[0]) == storyId:
					matching += [parts]
		if len(matching) < 1:
			raise Exception('story {} is missing'.format(storyId))
		if len(matching) > 1:
			raise Exception('storyId is in map multiple times: {}'.format(storyId))
		return matching[0]

	def getArchiveChapterInfo(self, chapterId: int) -> Optional[List[str]]:
		# format is: storyId:author:story:cid:chapterId
		matching: List[List[str]] = []
		with gzip.open(self.chapterMapPath, 'rb') as f:
			for l in f.readlines():
				line = l.decode('utf-8')[:-1]
				parts = line.split(':')
				if int(parts[4]) == chapterId:
					matching += [parts]
		if len(matching) < 1:
			return None
		if len(matching) > 1:
			raise Exception('chapterId is in map multiple times: {}'.format(chapterId))
		return matching[0]

	def getChapterIds(self, storyId: int) -> Dict[int, str]:
		matching: List[List[str]] = []
		with gzip.open(self.chapterMapPath, 'rb') as f:
			for l in f.readlines():
				line = l.decode('utf-8')[:-1]
				parts = line.split(':')
				if int(parts[0]) == storyId:
					matching += [parts]
		# TODO FIXME int, int?
		localChapterIdMap: Dict[int, str] = { }
		for r in matching:
			if int(r[3]) in localChapterIdMap:
				raise Exception('chapterId is in map multiple times: {}'.format(r[3]))
			localChapterIdMap[int(r[3])] = r[4]
		return localChapterIdMap

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		stripSuffixes = ['&showRestricted']
		for suff in stripSuffixes:
			if url.lower().endswith(suff.lower()):
				url = url[:-len(suff)]
		mapPrefix = [ ('http://', 'https://'), ('https://www.', 'https://'),
				('https://fanfictionworld.net/hparchive', self.baseUrl),
				(self.baseUrl + '/viewstory2.php', self.baseUrl + '/viewstory.php'),
				(self.baseUrl + '/viewstory.php?sid=', self.baseUrl + '/viewstory.php?psid='),
				(self.baseUrl + '/reviews.php?storyid=', self.baseUrl + '/viewstory.php?psid='),
				]
		for prefix in mapPrefix:
			if url.startswith(prefix[0]):
				url = prefix[1] + url[len(prefix[0]):]

		if not url.startswith(self.baseUrl):
			return None
		url = url[len(self.baseUrl):]

		if url.startswith(self.storyPrefix):
			rest = url[len(self.storyPrefix):]
			if rest.isnumeric():
				return FicId(self.ftype, rest)

		if not url.startswith(self.chapterPrefix):
			return None

		chapterId = url[len(self.chapterPrefix):]
		if not chapterId.isnumeric():
			return None

		info = self.getArchiveChapterInfo(int(chapterId))
		if info is None:
			return None
		return FicId(self.ftype, info[0], int(info[3]))

	def constructUrl(self, storyId: str, chapterId: int = None) -> str:
		if chapterId is None:
			return '{}{}{}'.format(self.baseUrl, self.storyPrefix, storyId)
		return '{}{}{}'.format(self.baseUrl, self.chapterPrefix, chapterId)

	def buildUrl(self, chapter: 'FicChapter') -> str:
		# TODO: do we need these 2 lines or will they always be done by however
		# FicChapter is created?
		if chapter.fic is None:
			chapter.fic = Fic.lookup((chapter.ficId,))
		if chapter.localChapterId is None:
			raise Exception('chapter missing localChapterId? FIXME')
		return self.constructUrl(chapter.fic.localId, int(chapter.localChapterId))

	def get(self, localId: str) -> Fic:
		existing = Fic.select({'sourceId': self.ftype, 'localId': localId})
		if len(existing) == 1:
			return existing[0]

		fic = Fic.new()
		fic.sourceId = self.ftype
		fic.localId = localId
		fic.created = OilTimestamp.now()
		return self.create(fic)

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId)
		return self.getCurrentInfo(fic)

	def extractContent(self, fic: Fic, html: str) -> str:
		return html

	def fixEncoding(self, s: str) -> str:
		s = s.replace('\x91', "'").replace('\x92', "'")
		s = s.replace('\xa9', '©').replace('\xe9', 'é').replace('\xe0', 'à')
		s = s.replace('\r\n', '\n').replace('\r', '\n')
		return s

	def slurp(self, fname: str) -> str:
		with gzip.open(fname, 'rb') as f:
			datab = f.read()
			data = datab.decode(self.encoding)
			return self.fixEncoding(data)
	
	def getCurrentInfo(self, fic: Fic) -> Fic:
		# grab the content from disk
		info = self.getArchiveStoryInfo(int(fic.localId))
		spath = '{}/archive/{}/{}/summary.html.gz'.format( \
				self.archivePath, info[1], info[2])
		data = self.slurp(spath)
		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		chapterCount = fic.chapterCount or 1
		dCount = int(math.floor(math.log(chapterCount, 10) + 1))
		localChapterIdMap = self.getChapterIds(int(fic.localId))
		for cid in range(1, chapterCount + 1):
			pcid = str(cid).zfill(dCount)
			fpath = '{}/archive/{}/{}/chapters/chapter_{}.html.gz'.format( \
					self.archivePath, info[1], info[2], pcid)
			data = self.slurp(fpath)
			chapter = fic.chapter(cid)
			chapter.localChapterId = localChapterIdMap[cid]
			chapter.setHtml(data)
			chapter.upsert()

		return Fic.lookup((fic.id,))

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		from bs4 import BeautifulSoup # type: ignore
		soup = BeautifulSoup(wwwHtml, 'html.parser')
		storyMainInfo = soup.findAll('table', {'class': 'storymaininfo'})
		if len(storyMainInfo) != 1:
			raise Exception('unable to find main story info')
		storyMainInfo = storyMainInfo[0]

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English") # TODO: don't hard code?

		disclaimerJs = "javascript:if (confirm('Please note. This story may contain adult themes. By clicking here you are stating that you are over 17. Click cancel if you do not meet this requirement.')) location = '?psid="
		for a in soup.findAll('a'):
			href = a.get('href')
			if not href.startswith(disclaimerJs) \
					and href != '?psid={}'.format(fic.localId):
				continue
			fic.title = a.getText()
			break
		else:
			raise Exception('error: unable to find title')

		fic.url = self.constructUrl(fic.localId)

		storySummaryTable = soup.findAll('table', {'class': 'storysummary'})
		if len(storySummaryTable) != 1:
			raise Exception('cannot find story summary table')
		storySummaryTable = storySummaryTable[0]
		fic.description = (storySummaryTable.getText().strip())
		if fic.description is None:
			raise Exception('error: unable to find description')

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		text = storyMainInfo.getText().replace('\xa0', ' ')
		matcher = RegexMatcher(text, {
			'ageRating': ('Rating:\s+(Mature|15\+|12\+)', str),
			'chapterCount': ('Chapters:\s+(\d+)', int),
			'wordCount': ('Words:\s+(\d+)', int),
			'reviewCount': ('Story Reviews:\s*(\d+)', int),
			'favoriteCount': ('Favorite Story Of:\s+(\d+) users', int),
			'updated': ('Last Updated:\s+(\S+)', str),
			'published': ('First Published:\s+(\S+)', str),
		})
		matcher.matchAll(fic)

		if fic.published is not None:
			publishedUts = util.parseDateAsUnix(fic.published, fic.fetched)
			fic.published = OilTimestamp(publishedUts)

		if fic.updated is None:
			fic.updated = fic.published
		elif fic.updated is not None:
			updatedUts = util.parseDateAsUnix(fic.updated, fic.fetched)
			fic.updated = OilTimestamp(updatedUts)

		if fic.chapterCount is None:
			fic.chapterCount = 1

		match = re.search('Status:\s+(Completed|Work In Progress|Abandoned)', text)
		if match is None:
			raise Exception('cannot find write status')

		status = match.group(1)
		if status == 'Completed':
			fic.ficStatus = FicStatus.complete
		elif status == 'Work In Progress':
			fic.ficStatus = FicStatus.ongoing # should these be abandoned?
		elif status == 'Abandoned':
			fic.ficStatus = FicStatus.abandoned
		else:
			raise Exception('unknown status: {}'.format(status))

		for a in soup.findAll('a'):
			a_href = a.get('href')
			if a_href.startswith('viewuser.php?showuid='):
				author = a.get_text()
				authorUrl = self.baseUrl + '/' + a_href
				authorId = a_href[len('viewuser.php?showuid='):]
				self.setAuthor(fic, author, authorUrl, authorId)
				break
		else:
			raise Exception('unable to find author:\n{}'.format(text))

		# TODO: chars/pairings?
		fic.add(Fandom.define('Harry Potter'))
		return fic

