import time
import zlib
from typing import List, Optional, Dict, Set, Type, Union, Any, TypeVar, Tuple
from enum import IntEnum

from lite import StoreType
import store_bases
from store_bases import OilTimestamp, ImportStatus, FicStatus, TagType
from htypes import FicId, FicType, getAdapter
import scrape
import util

defaultUserId = 1 # FIXME

T = TypeVar('T', bound='TagBase')
class TagBase(store_bases.Tag):
	ttype: Optional[TagType] = None
	@classmethod
	def define(cls: Type[T], name: str, parent: int = None, sourceId: int = None
			) -> T:
		assert(cls.ttype is not None)
		whereData = { 'type': cls.ttype, 'name': name }
		if parent is not None:
			whereData['parent'] = parent
		if sourceId is not None:
			whereData['sourceId'] = sourceId
		es = cls.select(whereData)
		if parent is None:
			es = [e for e in es if e.parent is None]
		if sourceId is None:
			es = [e for e in es if e.sourceId is None]
		if len(es) == 1:
			return es[0]
		if len(es) > 0:
			raise Exception(f'FIXME dup cls.ttype={cls.ttype} name={name} sourceId={sourceId}')
		e = cls.new()
		e.type = cls.ttype
		e.name = name
		e.parent = parent
		e.sourceId = sourceId
		e.insert()
		return cls.define(name, parent, sourceId)
	def add(self, fic: 'Fic') -> StoreType:
		e = FicTagBase.select({'ficId': fic.id, 'tagId': self.id})
		if len(e) > 0:
			return e[0]
		n = FicTagBase.new()
		n.ficId = fic.id
		n.tagId = self.id
		n.priority = 1
		n.insert()
		return n
class Genre(TagBase):
	ttype = TagType.genre
class Tag(TagBase):
	ttype = TagType.tag
class Fandom(TagBase):
	ttype = TagType.fandom
class Character(TagBase):
	ttype = TagType.character
	@staticmethod
	def defineInFandom(fandom: Fandom, name: str, sourceId: int = None
			) -> 'Character':
		return Character.define(name, fandom.id, sourceId)

	@staticmethod
	def find(fandom: Fandom, name: str) -> Optional['Character']:
		chars = Character.select({'parent': fandom.id, 'name': name})
		if len(chars) == 1:
			return chars[0]
		return None

T2 = TypeVar('T2', bound='FicTagBase')
class FicTagBase(store_bases.FicTag):
	ttype: Optional[TagType] = None
	@classmethod
	def forFic(cls: Type[T2], ficId: int) -> List[T2]:
		assert(cls.ttype is not None)
		with cls.getConnection().cursor() as curs:
			curs.execute('''
			select ft.*
			from fic_tag ft
			join tag t on t.id = ft.tagId
			where t.type = %s and ft.ficId = %s
			''', (cls.ttype, ficId))
			return [cls.fromRow(r) for r in curs]
class FicGenre(FicTagBase):
	ttype = TagType.genre
class FicTag(FicTagBase):
	ttype = TagType.tag
class FicFandom(FicTagBase):
	ttype = TagType.fandom
class FicCharacter(FicTagBase):
	ttype = TagType.character


class ReadEvent(store_bases.ReadEvent):
	@classmethod
	def record(cls, userId: int, ficId: int, localChapterId: str,
			ficStatus: FicStatus = FicStatus.complete) -> 'ReadEvent':
		re = cls()
		re.userId = userId
		re.ficId = ficId
		re.localChapterId = localChapterId
		re.created = OilTimestamp.now()
		re.ficStatus = ficStatus
		re.insert()
		return re


_authorCache: Dict[int, 'Author'] = {}
_authorSourceCache: Dict[int, Dict[int, 'AuthorSource']] = {}
_ficTagCache: Dict[int, List[FicTag]] = {}
def initFicTagCache() -> None:
	global _ficTagCache
	_ficTagCache = {}
	for ft in FicTag.select():
		if ft.ficId not in _ficTagCache:
			_ficTagCache[ft.ficId] = []
		_ficTagCache[ft.ficId].append(ft)
	for f in Fic.select():
		if f.id not in _ficTagCache:
			_ficTagCache[f.id] = []

class Fic(store_bases.Fic):
	def __init__(self) -> None:
		self._cachedFandoms: Optional[List[Fandom]] = None
		self.urlId = util.randomString(8, charset=util.urlIdCharset)
		self.importStatus = ImportStatus.pending

	def fid(self) -> FicId:
		return FicId(FicType(self.sourceId), self.localId, ambiguous=False)

	def getAuthorName(self) -> str:
		global _authorCache, _authorSourceCache

		if len(_authorCache) == 0:
			_authorCache = {a.id: a for a in Author.select({})}
		a = None
		if self.authorId in _authorCache:
			a = _authorCache[self.authorId]
		else:
			a = Author.lookup((self.authorId,))

		if self.sourceId not in _authorSourceCache:
			_authorSourceCache[self.sourceId] = {}
		if len(_authorSourceCache[self.sourceId]) == 0:
			_authorSourceCache[self.sourceId] = \
				{s.authorId: s for s in AuthorSource.select({'sourceId': self.sourceId})}

		if self.authorId in _authorSourceCache[self.sourceId]:
			return _authorSourceCache[self.sourceId][self.authorId].name

		s = AuthorSource.select({'authorId': self.authorId, 'sourceId': self.sourceId})
		if len(s) == 1:
			return s[0].name
		raise Exception(f'unable to find self.authorId={self.authorId}, self.sourceId={self.sourceId}, len(s)={len(s)}')

	@staticmethod
	def list(where: Dict[str, Any] = None) -> List['Fic']:
		#Sql.execute((Fic, UserFic), '''
		#select f.*, uf.*
		#from fic f
		#join user_fic uf on uf.ficId = f.id
		#where uf.userId = 1
		#order by uf.rating desc nulls last
		#''', (,))

		#Fic.join(UserFic, equals(UserFic.ficId, Fic.id))
		#	.where(equals(UserFic.userId, 1))
		#	.order(UserFic.rating, desc=True, nulls_last=True)
		#	.select()

		# FIXME: needs join to UserFic
		#'''
		#	  CASE WHEN status == 1 THEN 9 ELSE 0 END ASC
		#	, CASE WHEN favorite == 2 THEN 9 ELSE importStatus END DESC
		#	, CASE WHEN favorite == 2 THEN 1 ELSE 0 END DESC
		#	, status DESC
		#	, CASE WHEN status == 3 THEN 9 - ficStatus ELSE ficStatus END DESC
		#	, rating DESC
		#	, favorite DESC
		#	, lastViewed DESC'''
		return Fic.select(where, '''
				case when exists (
					select 1 from user_fic uf
					where uf.userId = 1 and uf.ficId = id
				) then 1 else 0 end desc,
				case when ficStatus = 'abandoned' then -1 else 1 end desc,
				case when ficStatus = 'complete' then 1 else -1 end desc,
				created desc
				''')

	@staticmethod
	def listAdded() -> List['Fic']:
		return Fic.list({'importStatus': ImportStatus.metadata})

	@staticmethod
	def load(ficId: FicId) -> 'Fic':
		fic = getAdapter(ficId.sourceId).get(ficId.localId)
		if fic is None:
			raise Exception('TODO FIXME')
		return fic

	@staticmethod
	def tryLoad(ficId: FicId) -> Optional['Fic']:
		existing = Fic.select({'sourceId': ficId.sourceId, 'localId': ficId.localId})
		if len(existing) != 1:
			return None
		return existing[0]

	def chapter(self, chapterId: int) -> 'FicChapter':
		chapter = FicChapter.getOrDefault((self.id, chapterId))
		chapter.fic = self
		return chapter

	def fandoms(self) -> List['Fandom']:
		if self._cachedFandoms is not None:
			return self._cachedFandoms
		#global _ficTagCache
		#if self.id not in _ficTagCache:
		#	_ficTagCache[self.id] = [ft for ft in FicTag.select({'ficId': self.id})]
		ours = FicFandom.forFic(self.id)
		#ours = FicFandom.select({'ficId': self.id})
		self._cachedFandoms = [Fandom.lookup((our.tagId,)) for our in ours]
		return self._cachedFandoms

	def genres(self) -> List['Genre']:
		ours = FicGenre.forFic(self.id)
		return [Genre.lookup((our.tagId,)) for our in ours]

	def characters(self) -> List['Character']:
		ours = FicCharacter.forFic(self.id)
		return [Character.lookup((our.tagId,)) for our in ours]

	def tags(self) -> List['Tag']:
		ours = FicTag.forFic(self.id)
		return [Tag.lookup((our.tagId,)) for our in ours]

	def cache(self, upto: int = None) -> None:
		upto = upto or self.chapterCount or -1
		for cid in range(1, upto + 1):
			self.chapter(cid).cache()

	def add(self, simpleTag: TagBase) -> StoreType:
		return simpleTag.add(self)

	def checkForUpdates(self) -> None:
		self._cachedFandoms = None
		ccount = self.chapterCount
		getAdapter(FicType(self.sourceId)).getCurrentInfo(self)
		if self.chapterCount is None: return
		if ccount is not None and ccount >= self.chapterCount:
			return
		# need to invalidate read status -- can be done in a single update
		cufs = UserFic.select({'ficId': self.id, 'readStatus': FicStatus.complete})
		for cuf in cufs:
			if cuf.lastChapterRead is None: continue
			if self.chapterCount < cuf.lastChapterRead:
				raise Exception('{self.chapterCount} < {cuf.lastChapterRead}?')
			cuf.readStatus = FicStatus.ongoing
			cuf.upsert()

	def getUserFic(self, userId: int = defaultUserId) -> 'UserFic':
		return UserFic.getOrDefault((userId, self.id))

class UserFic(store_bases.UserFic):
	@classmethod
	def default(cls, pkTuple: Tuple[int, int]) -> 'UserFic':
		self = UserFic.new()
		self.userId, self.ficId = pkTuple
		self.readStatus = FicStatus.ongoing
		self.lastChapterRead = None
		self.lastChapterViewed = None
		self.rating = None
		self.isFavorite = False
		self.lastViewed = None
		return self

	@classmethod
	def getOrDefault(cls, pkTuple: Tuple[int, int]) -> 'UserFic':
		e = UserFic.get(pkTuple)
		if e is not None:
			return e
		return UserFic.default(pkTuple)

	def updateLastViewed(self, chapterId: int) -> None:
		self.lastViewed = OilTimestamp.now()
		self.lastChapterViewed = chapterId
		self.update()

	def updateLastRead(self, chapterId: int) -> None:
		if (self.lastChapterRead or -1) >= chapterId:
			return
		self.lastChapterRead = chapterId
		self.update()


class UserFicChapter(store_bases.UserFicChapter):
	def __init__(self) -> None:
		self.lastLine: int = -1

	@classmethod
	def getOrDefault(cls, pkTuple: Tuple[int, int, str]) -> 'UserFicChapter':
		e = UserFicChapter.get(pkTuple)
		if e is not None:
			return e
		self = UserFicChapter.new()
		self.userId, self.ficId, self.localChapterId = pkTuple
		self.readStatus = FicStatus.ongoing
		self.line = 0
		self.subLine = 0
		self.modified = OilTimestamp.now()
		self.markedRead = None
		self.markedAbandoned = None
		return self

	def savePosition(self) -> None:
		# TODO: not this
		if self.line == self.lastLine:
			return
		self.lastLine = self.line
		self.subLine = 0
		self.modified = OilTimestamp.now()
		self.upsert()

	def markRead(self) -> None:
		e = ReadEvent.record(self.userId, self.ficId, self.localChapterId,
				FicStatus.complete)

		if self.readStatus == FicStatus.complete:
			return
		self.readStatus = FicStatus.complete

		if self.markedRead is None:
			self.markedRead = OilTimestamp.now()
		self.upsert()

	def markAbandoned(self) -> None:
		e = ReadEvent.record(self.userId, self.ficId, self.localChapterId,
				FicStatus.abandoned)

		if self.readStatus == FicStatus.abandoned:
			return
		self.readStatus = FicStatus.abandoned

		if self.markedRead is None:
			self.markedRead = OilTimestamp.now()
		self.upsert()

class FicChapter(store_bases.FicChapter):
	def __init__(self) -> None:
		self.fic: Optional[Fic] = None

	@classmethod
	def getOrDefault(cls, pkTuple: Tuple[int, int]) -> 'FicChapter':
		e = FicChapter.get(pkTuple)
		if e is not None:
			return e
		self = FicChapter.new()
		self.ficId, self.chapterId = pkTuple
		return self

	def getUserFicChapter(self, userId: int = defaultUserId) -> UserFicChapter:
		return UserFicChapter.getOrDefault((userId, self.ficId, self.localChapterId))

	def getFic(self) -> Fic:
		if self.fic is None:
			self.fic = Fic.lookup((self.ficId,))
		return self.fic

	@staticmethod
	def getNeedsCacheInfo() -> Dict[int, Set[int]]:
		conn = FicChapter.getConnection()
		sql = '''
		; with mcc as (select max(coalasce(chapterCount, -1)) as n from fic)
		select f.ficId, n as chapterId
		from fic f
		join mcc mcc on 1=1
		join generate_series(1, mcc.n) n
		left join fic_chapter fc
		  on fc.ficId = f.id and fc.chapterId = n
		where fc.ficId is null or fc.content is null
		'''
		with conn.cursor() as curs:
			curs.execute(sql, ())

			cacheInfo: Dict[int, Set[int]] = {}
			for r in curs:
				if r[0] not in cacheInfo:
					cacheInfo[r[0]] = { r[1] }
				else:
					cacheInfo[r[0]] |= { r[1] }

		return cacheInfo

	def cachedContent(self) -> str:
		self.cache()
		html = self.html()
		if html is None:
			raise Exception('unable to cache content? FIXME')
		return html

	def cache(self) -> None:
		# already scraped, nothing to do
		if self.content is not None:
			return

		# never fetched, scrape fresh
		fic = self.getFic()
		adapter = getAdapter(FicType(fic.sourceId))
		if not adapter.cacheable:
			raise Exception(f'unable to cache {FicType(fic.sourceId).name}:{fic.id}')

		data = adapter.softScrape(self)

		self.fetched = OilTimestamp.now()
		self.upsert()

		if data is not None:
			self.setHtml(data)
		else:
			raise Exception('unable to scrape chapter? FIXME')
		self.upsert()

	def html(self) -> Optional[str]:
		if self.content is None:
			return None
		util.logMessage(repr(self.content[:10]))
		return str(util.decompress(self.content), 'utf-8')

	def setHtml(self, html: str) -> None:
		if self.fic is None:
			self.fic = Fic.lookup((self.ficId,))
		html = getAdapter(FicType(self.fic.sourceId)).extractContent(self.fic, html)
		self.content = util.compress(bytes(html, 'utf-8'))
		self.upsert()

class Language(store_bases.Language):
	@classmethod
	def getId(cls, language: str) -> int:
		es = Language.select({'name': language})
		if len(es) == 1:
			return es[0].id
		if len(es) > 0:
			raise Exception(f'multiple {language} languages?')
		e = Language.new()
		e.name = language
		e.insert()
		return Language.getId(language)

class Author(store_bases.Author):
	@classmethod
	def getId(cls, name: str, sourceId: int) -> int:
		assert(isinstance(sourceId, int))
		es = Author.select({'name': name}, f'''
			case when exists (
				select 1 from author_source s
				where s.authorId = authorId and s.sourceId = {sourceId}
			) then 1 else 0 end desc''')
		if len(es) > 1:
			util.logMessage(f'many authors: name={name} sourceId={sourceId}')
		if len(es) >= 1:
			return es[0].id
		if len(es) > 0:
			raise Exception('FIXME')
		e = Author.new()
		e.name = name
		e.urlId = util.randomString(8, charset=util.urlIdCharset)
		e.insert()
		return Author.getId(name, sourceId)

class AuthorSource(store_bases.AuthorSource):
	@classmethod
	def getId(cls, authorId: int, sourceId: int,
			name: str, url: str, localId: str) -> int:
		es = AuthorSource.select({'authorId': authorId, 'sourceId': sourceId})
		if len(es) > 1:
			util.logMessage(f'many author source: authorId={authorId} sourceId={sourceId}')
		if len(es) >= 1:
			es[0].name = name
			es[0].url = url
			es[0].localId = localId
			es[0].update()
			return es[0].id
		if len(es) > 0:
			raise Exception('FIXME')

		e = AuthorSource.new()
		e.authorId = authorId
		e.sourceId = sourceId
		e.name = name
		e.url = url
		e.localId = localId
		e.insert()
		return AuthorSource.getId(authorId, sourceId, name, url, localId)

# TODO FIXME
#class QueueStatus(IntEnum):
#	pending = 0
#	done = 1
#	broken = 2
#
#class ImportQueue(store_bases.ImportQueueBase):
#	def __init__(self, genId: bool = False):
#		pass
#	@staticmethod
#	def enqueue(ident: str) -> None:
#		q = ImportQueue.new()
#		q.ident = ident
#		q.added = int(time.time())
#		q.touched = None
#		q.tries = 0
#		q.status = QueueStatus.pending
#		q.upsert()

initFicTagCache()

