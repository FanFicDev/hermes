import time
import random
import os
import sys
import traceback
import typing
from typing import List, Tuple, Dict, Optional, Any, Sequence
import util
import lite_oil

if typing.TYPE_CHECKING:
	import psycopg2
	import requests

__scrapeSource: Optional[str] = None

__oilConn = None
__oilCurs = None

__userAgent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'

decodeFailureDumpFile = '/tmp/hermes_decodeFailure.html'

_staleOnly = False
_staleBefore = None

utf8_to_cp1252: List[Tuple[bytes, bytes]] = []
cp1252_munge: List[Tuple[bytes, bytes]] = []


def importEnvironment() -> None:
	global _staleOnly, _staleBefore
	if 'HERMES_STALE' in os.environ:
		_staleOnly = True
	if 'HERMES_STALE_BEFORE' in os.environ:
		_staleBefore = int(os.environ['HERMES_STALE_BEFORE'])
		_staleOnly = True

	global __scrapeSource
	__scrapeSource = (
		__scrapeSource if 'OIL_SCRAPE_SOURCE' not in os.environ else
		os.environ['OIL_SCRAPE_SOURCE']
	)


def openMinerva() -> 'psycopg2.connection':
	global __oilConn
	if __oilConn is None:
		import psycopg2
		__oilConn = psycopg2.connect(lite_oil.getConnectionString())
		if __oilConn is None:
			raise Exception('__oilConn')
	return __oilConn


def closeMinerva() -> None:
	global __oilConn
	if __oilConn is None:
		return
	__oilConn.commit()
	__oilConn.close()
	__oilConn = None


def saveWebRequest(
	created: int,
	url: str,
	status: int,
	response: Optional[str],
	source: str = None
) -> None:
	#import psycopg2
	responseBytes: Optional[bytes] = None
	if response is not None:
		responseBytes = util.compress(response.encode('utf-8'))

	global __scrapeSource
	if source is None:
		source = __scrapeSource
	conn = openMinerva()

	curs = conn.cursor()
	curs.execute(
		(
			'insert into web(created, url, status, response, source)'
			+ 'values(%s, %s, %s, %s, %s)'
		), (created, url, status, responseBytes, source)
	)

	curs.close()
	closeMinerva()


def getAllUrlLike(like: str) -> List[str]:
	conn = openMinerva()
	curs = conn.cursor()
	stmt = '''
		select url from web
		where status = 200
			and url like %s
		order by created desc
	'''

	curs.execute(stmt, (like, ))
	res = curs.fetchall()

	curs.close()
	return [r[0] for r in res]


def getLastUrlLike(like: str) -> Optional[str]:
	conn = openMinerva()
	curs = conn.cursor()
	stmt = '''
		select url from web
		where status = 200
			and url like %s
		order by created desc
		limit 1
	'''

	curs.execute(stmt, (like, ))
	res = curs.fetchone()

	curs.close()
	if res is None:
		return None
	return str(res[0])


# takes a tuple with the first being an actual url
def getLastUrlLikeOrDefault(defaultAndLikes: Sequence[str]) -> str:
	conn = openMinerva()
	curs = conn.cursor()
	stmt = ''.join(
		[
			' select url from web where status = 200 ',
			' and (url = %s ',
			(' or url like %s ' * len(defaultAndLikes[1:])),
			' ) order by created desc ',
			' limit 1 ',
		]
	)

	curs.execute(stmt, defaultAndLikes)
	res = curs.fetchone()

	curs.close()
	if res is None:
		return defaultAndLikes[0]
	return str(res[0])


ScrapeMeta = Dict[str, Any]


def getMostRecentScrapeWithMeta(
	url: str,
	ulike: str = None,
	status: Optional[int] = 200,
	beforeId: Optional[int] = None
) -> Optional[ScrapeMeta]:
	conn = openMinerva()
	curs = conn.cursor()
	stmt = 'select id, created, url, response, status from web where '
	clauses: List[str] = []
	whereData: List[Any] = []
	if status is not None:
		clauses += ['status = %s']
		whereData += [status]
	if beforeId is not None:
		clauses += ['id <= %s']
		whereData += [beforeId]

	if ulike is None:
		clauses += ['url = %s']
		whereData += [url]
	else:
		clauses += ['url like %s']
		whereData += [ulike]

	stmt += ' and '.join(clauses)
	stmt += ' order by id desc'

	curs.execute(stmt, tuple(whereData))
	res = curs.fetchone()

	curs.close()
	if res is None:
		return None

	response = res[3]
	if response is not None:
		response = util.decompress(response.tobytes()).decode('utf-8')

	return {'url': res[2], 'fetched': res[1], 'raw': response, 'status': res[4]}


def getMostRecentScrape(url: str, ulike: str = None) -> Optional[str]:
	r = getMostRecentScrapeWithMeta(url, ulike)
	return None if r is None else r['raw']


def getMostRecentScrapeTime(url: str) -> Optional[int]:
	conn = openMinerva()
	curs = conn.cursor()
	stmt = 'select created from web where status = 200 '
	stmt += ' and url = %s'
	stmt += ' order by id desc'

	curs.execute(stmt, (url, ))
	res = curs.fetchone()

	curs.close()
	if res is None:
		return None
	return int(res[0])


def canonizeUrl(url: str) -> str:
	protocol = url[:url.find('://')]
	rest = url[url.find('://') + 3:]
	rest = rest.replace('//', '/')
	# TODO: are there more of these? better way to handle?
	if rest.endswith('/') and rest.find('phoenixsong.net') == -1:
		rest = rest[:-1]
	return protocol + '://' + rest


def softScrapeWithMeta(
	url: str,
	delay: float = 3,
	ulike: str = None,
	mustyThreshold: int = None,
	timeout: int = 15
) -> Optional[ScrapeMeta]:
	url = canonizeUrl(url)
	mostRecent = getMostRecentScrapeWithMeta(url, ulike, beforeId=_staleBefore)
	if (
		mostRecent is not None and mustyThreshold is not None
		and int(time.time()) - mustyThreshold > mostRecent['fetched']
	):
		mostRecent = None
		time.sleep(1)
	if mostRecent is None:
		scrape(url, delay=0.1, timeout=timeout)
		mostRecent = getMostRecentScrapeWithMeta(url)
		time.sleep(delay)
	return mostRecent


def softScrape(
	url: str,
	delay: float = 3,
	ulike: str = None,
	mustyThreshold: int = None,
	timeout: int = 15
) -> Optional[str]:
	r = softScrapeWithMeta(
		url,
		delay=delay,
		ulike=ulike,
		mustyThreshold=mustyThreshold,
		timeout=timeout
	)
	return None if r is None else r['raw']


def setupCP1252() -> None:
	global cp1252_munge, utf8_to_cp1252
	if len(cp1252_munge) > 0 and len(utf8_to_cp1252) > 0:
		return
	utf8_to_cp1252 = [
		(b'\xc2\xa9', b'\xa9'),  # ©
		(b'\xc2\xb0', b'\xb0'),  # °
		(b'\xc3\xa1', b'\xe1'),  # á
		(b'\xc3\xa7', b'\xe7'),  # ç
		(b'\xc3\xa8', b'\xe8'),  # è
		(b'\xc3\xa9', b'\xe9'),  # é
		(b'\xc3\xa0', b'\xe0'),  # à
		(b'\xe2\x80\xa6', b'\x85'),  # …
		(b'\xe2\x80\x93', b'\x96'),  # –
		(b'\xe2\x80\x99', b'\x92'),  # ’
		(b'\xe2\x80\x9c', b'\x93'),  # “
		(b'\xe2\x80\x9d', b'\x94'),  # ”
		(b'\xef\xbf\xbd', b'\x81'),  # literal question mark block >_>
	]
	# FIXME these are weird:
	#   \x98 ˜    \xa6 ¦
	cp1252_munge = [
		(b'\x81', b''),  # invalid
		(b'\x91', b"'"),  # ‘
		(b'\x92', b"'"),  # ’
		(b'\x93', b'"'),  # “
		(b'\x94', b'"'),  # ”
		(b'\x96', b'-'),  # –
		(b'\x97', b'-'),  # —
		(b'\x9d', b''),  # undefined
		(b'\xa0', b' '),  # nbsp
		(b'\xad', b''),  # soft hyphen
	]


def decodeRequest(data: Optional[bytes], url: str) -> Optional[str]:
	global decodeFailureDumpFile
	if data is None:
		return None

	try:
		return data.decode('utf-8')
	except:
		pass

	setupCP1252()

	# handle Mórrigan and façade in
	# http://www.fictionalley.org/authors/irina/galatea05.html
	# looks aggressively misencoded
	data = data.replace(b'M\xc3\x83\xc2\xb3rr\xc3\x83\xc2\xadgan', b'M\xf3rrigan')
	data = data.replace(b'fa\xc3\x83\xc2\xa7ade', b'fa\xe7ade')

	data = data.replace(
		b'#8211;&#8212;&#8211;\xb5&#8211;\xbb&#8211;\xb8',
		b'#8211;&#8212;&#8211;&#8211;&#8211;'
	)
	data = data.replace(
		b'#8211;&#8211;&#8211;\xb9 &#8211; &#8212;\x83',
		b'#8211;&#8211;&#8211; &#8211; &#8212;'
	)
	data = data.replace(
		b'&#8211;\xb9 &#8211; &#8212;\x83',
		b'#8211;&#8211;&#8211; &#8211; &#8212;&#8'
	)

	# replace misencoded utf-8 bits (likely from a header or footer) with their
	# cp1252 counterparts
	for utoc in utf8_to_cp1252:
		data = data.replace(utoc[0], utoc[1])

	# do some cleanup on the remaining cp1252 to normalize smart quotes and
	# delete a few invalid chars that may have leaked through
	for ctom in cp1252_munge:
		data = data.replace(ctom[0], ctom[1])

	try:
		return data.decode('cp1252')
	except Exception as e:
		util.logMessage(
			'error decoding {}: {}\n{}'.format(url, e, traceback.format_exc())
		)
		with open(decodeFailureDumpFile, 'wb') as f:
			f.write(data)
		raise


def resolveRedirects(
	url: str, cookies: 'requests.cookies.RequestsCookieJar' = None
) -> str:
	import requests
	url = canonizeUrl(url)
	headers = {'User-Agent': __userAgent}
	if cookies is None:
		import priv
		cookies = priv.getDefaultCookies()
	r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
	time.sleep(2 * random.random())
	return r.url


def delaySecs(secs: float) -> None:
	if secs < 0.05:
		time.sleep(0.10 * random.random() + 0.01)
	elif secs < 0.25:
		time.sleep(0.75 * random.random() + 0.25)
	else:
		time.sleep(3.5 * random.random() + 1.0)
	time.sleep(secs)


def scrape(
	url: str,
	cookies: 'requests.cookies.RequestsCookieJar' = None,
	delay: float = 3,
	timeout: int = 15
) -> ScrapeMeta:
	url = canonizeUrl(url)
	headers = {'User-Agent': __userAgent}
	ts = int(time.time())

	if _staleOnly:
		pass  # util.logMessage('staleScrape|{}'.format(url), 'scrape.log')

		last = getMostRecentScrapeWithMeta(url, beforeId=_staleBefore)
		if last is None or 'raw' not in last:
			raise Exception('failed to stale scrape url: {}'.format(url))
		return {'url': url, 'fetched': ts, 'raw': last['raw']}

	import requests
	if cookies is None:
		import priv
		cookies = priv.getDefaultCookies()
	r = None
	try:
		r = requests.get(url, headers=headers, cookies=cookies, timeout=timeout)
	except:
		util.logMessage('scrape|exception|{}'.format(url), 'scrape.log')
		raise

	if r.status_code != 200:
		saveWebRequest(ts, url, r.status_code, None)
		delaySecs(delay)
		raise Exception('failed to download url {}: {}'.format(r.status_code, url))

	raw = r.content
	text = decodeRequest(raw, url)

	saveWebRequest(ts, url, r.status_code, text)
	delaySecs(delay)
	return {'url': url, 'fetched': ts, 'raw': text}


if __name__ == '__main__':
	if len(sys.argv) != 4:
		print('usage: scrape.py ./file {url} {time stamp}')
		sys.exit(0)
	fname = sys.argv[1]
	url = sys.argv[2]
	import dateutil.parser
	ts = (dateutil.parser.parse(sys.argv[3]))
	uts = util.dtToUnix(ts)
	print(sys.argv)

	recent = getMostRecentScrape(url)
	if recent is not None:
		print('url is already in minerva')
		sys.exit(0)

	with open(fname, 'r') as f:
		content = f.read()
		saveWebRequest(uts, url, 200, content)

	sys.exit(0)
