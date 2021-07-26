from enum import IntEnum
import typing
from typing import Dict, Optional, Tuple, Any
if typing.TYPE_CHECKING:
	from adapter.adapter import Adapter
from psycopg2.extensions import AsIs, register_adapter


class FicType(IntEnum):
	broken = 0
	manual = 1
	ff_net = 2
	dummy = 3
	ao3 = 4
	hpfanficarchive = 5
	fictionalley = 6
	fanficauthors = 7
	portkeyarchive = 8
	siye = 9
	fictionpress = 10
	fictionhunt = 11
	spacebattles = 12
	sufficientvelocity = 13
	questionablequesting = 14
	harrypotterfanfiction = 15
	parahumans = 16
	adultfanfiction = 17
	fanficsme = 18
	royalroadl = 19
	wavesarisen = 20
	sugarquill = 21
	bulbagarden = 22
	thefanfictionforum = 23
	fanficparadisesfw = 24
	fanficparadisensfw = 25
	wanderinginn = 26


def adaptFicType(ftype: FicType) -> AsIs:
	return AsIs(int(ftype))


register_adapter(FicType, adaptFicType)

# map FicType => Adapter
adapters: Dict[FicType, Optional['Adapter']] = {
	FicType.broken: None,
}


def getAdapter(ficType: FicType) -> 'Adapter':
	adapter = adapters[ficType]
	if adapter is not None:
		return adapter
	raise Exception(f'missing adapter for {ficType}')


class FicId:
	# TODO: is this cid or localChapterId?
	def __init__(
		self, ftype: FicType, lid: str, cid: int = None, ambiguous: bool = True
	):
		self.sourceId = ftype
		self.localId = lid
		self.chapterId = cid
		self.ambiguous = ambiguous

	def __key(self) -> Tuple[FicType, str, Optional[int], bool]:
		return (self.sourceId, self.localId, self.chapterId, self.ambiguous)

	def __eq__(self, other: Any) -> bool:
		return (isinstance(other, type(self)) and self.__key() == other.__key())

	def __hash__(self) -> int:
		return hash(self.__key())

	@staticmethod
	def parse(ident: str) -> 'FicId':
		ident = ident.strip()
		res = FicId.tryParse(ident)
		if res is None:
			raise Exception('unable to parse ident: {}'.format(ident))
		return res

	@staticmethod
	def cleanupIdent(ident: str) -> str:
		import urllib.parse
		# attempt to map various generic unsupported urls which redirect to
		# supported urls or are equivalent to supported urls to their supported
		# version (such as google or facebook redirect links)
		ident = ident.rstrip(':,')

		ident = ident.replace('http:/', 'http://').replace('https:/', 'https://')
		while ident.find('///') >= 0:
			ident = ident.replace('///', '//')

		# FIXME this needs to be more general :/
		if ident.find('//parahumans.wordpress.com/') >= 0:
			ident = 'https://parahumans.wordpress.com'

		if ident.find('fanfiction.ws/') >= 0:
			ident = ident.replace('fanfiction.ws/', 'fanfiction.net/')
		if ident.find('fanfiction.de/') >= 0:
			ident = ident.replace('fanfiction.de/', 'fanfiction.net/')

		if ident.lower().startswith('https://href.li/?'):
			ident = ident[len('https://href.li/?'):]

		if ident.lower().startswith('http://web.archive.org/'):
			ident = 'https://' + ident[len('http://'):]
		if ident.lower().startswith('https://web.archive.org/web/'):
			ident = '/'.join(ident.split('/')[5:])

		# if this is a google redirect url, extract the target
		if (
			ident.find('//') >= 0 and ident.find('google') >= 0
			and ident.find('/url?') >= 0 and ident.find('url=') >= 0
		):
			try:
				o = urllib.parse.urlparse(ident)
				q = urllib.parse.parse_qs(o.query)
				ident = q['url'][0]
			except:
				pass
		if (
			ident.find('//') >= 0 and ident.find('google') >= 0
			and ident.find('/url?') >= 0 and ident.find('q=') >= 0
		):
			try:
				o = urllib.parse.urlparse(ident)
				q = urllib.parse.parse_qs(o.query)
				ident = q['q'][0]
			except:
				pass

		# if this is a facebook redirect url, extract the target
		if (
			ident.find('//') >= 0 and ident.find('facebook.com/l.php') >= 0
			and ident.find('?') >= 0 and ident.find('u=') >= 0
		):
			try:
				o = urllib.parse.urlparse(ident)
				q = urllib.parse.parse_qs(o.query)
				ident = q['u'][0]
			except:
				pass

		return ident

	@staticmethod
	def tryParse(ident: str) -> Optional['FicId']:
		ident = FicId.cleanupIdent(ident)

		# try parsing as original case
		fid = FicId.__tryParse(ident)
		if fid is not None:
			return fid

		# fallback to trying to parse as lowercase
		ident = ident.lower()
		return FicId.__tryParse(ident)

	@staticmethod
	def __tryParse(ident: str) -> Optional['FicId']:
		if len(ident.strip()) < 1:
			return None

		# strip view-source from potential urls
		if ident.startswith('view-source:http'):
			ident = ident[len('view-source:'):]

		# guess url next
		if ident.startswith('http'):
			return FicId.tryParseUrl(ident)

		# check for link{site}(id) style idents
		for ftype in adapters:
			a = adapters[ftype]
			if a is None: continue
			if a.botLinkSuffix is None: continue
			l = 'link{}('.format(a.botLinkSuffix)
			if ident.startswith(l) and ident.endswith(')'):
				mid = ident[len(l):-1]
				if not mid.isnumeric():
					return FicId.tryParse(ident)
				return FicId(ftype, mid, ambiguous=False)

		# maybe it's an actual story id
		from store import Fic
		parts = ident.split('/')
		if parts[0].isnumeric():
			fic = Fic.get((int(parts[0]), ))
			if fic is not None:
				fid = fic.fid()
				if len(parts) == 2 and parts[1].isnumeric():
					fid.chapterId = int(parts[1])
					fid.ambiguous = False
				return fid

		# or maybe it's a url id...
		potential = Fic.select({'urlId': parts[0]})
		if len(potential) == 1:
			fid = potential[0].fid()
			if len(parts) == 2 and parts[1].isnumeric():
				fid.chapterId = int(parts[1])
				fid.ambiguous = False
			return fid

		# assume numeric is ffnet
		if ident.isnumeric():
			return FicId(FicType.ff_net, ident)

		# guess story/chapter on ffnet
		if len(parts) == 2 and parts[1].isnumeric():
			cid = int(parts[1])
			return FicId(FicType.ff_net, parts[0], cid, ambiguous=False)

		# try prepending https protocol
		if ident.find('://') < 0:
			ident = 'https://' + ident
			return FicId.tryParseUrl(ident)

		# just guess manual adapter
		return FicId.tryParseFallback(ident)

	@staticmethod
	def tryParseUrl(url: str) -> Optional['FicId']:
		for ftype in adapters:
			a = adapters[ftype]
			if a is None: continue
			for fragment in a.urlFragments:
				if url.find(fragment) != -1:
					return a.tryParseUrl(url)
		return FicId.tryParseFallback(url)

	@staticmethod
	def tryParseFallback(ident: str) -> Optional['FicId']:
		manualAdapter = adapters[FicType.manual]
		assert (manualAdapter is not None)
		fid = None
		try:
			fid = manualAdapter.tryParseUrl(ident)
		except:
			pass
		if fid is None:
			if not ident.endswith('/'):
				ident = ident + '/'
			else:
				ident = ident.rstrip('/')
			try:
				fid = manualAdapter.tryParseUrl(ident)
			except:
				pass
		return fid

	@staticmethod
	def guessFicType(ident: str) -> Tuple[Optional[FicType], Optional[str]]:
		for ftype in adapters:
			a = adapters[ftype]
			if a is None: continue
			for fragment in a.urlFragments:
				if ident.find(fragment) != -1:
					return (ftype, fragment)
		return (None, None)

	@staticmethod
	def help() -> str:
		return '\n'.join(
			[
				'FicId: #FFNetId',
				'       #FFNetId/#ChapterId',
				'       <story url>',
			]
		)
