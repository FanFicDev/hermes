from typing import Dict, List, Set, Optional, Tuple, Union, Any, cast
import typing
if typing.TYPE_CHECKING:
	from bs4 import BeautifulSoup  # type: ignore
import time
import dateutil.parser
import traceback
import urllib
from html import escape as htmlEscape

from htypes import FicType, FicId
from store import (
	OilTimestamp, Language, FicStatus, Fic, FicChapter, Fandom, Character, Tag
)
import util
import scrape
from view import HtmlView

from adapter.adapter import Adapter, edumpContent


class XenForoAdapter(Adapter):
	def __init__(
		self,
		baseUrl: str,
		urlFragments: Union[str, List[str]] = [],
		ftype: FicType = FicType.broken,
		titleSuffix: str = '',
		rewrites: List[Tuple[str, str]] = None,
		postContainer: Union[str, List[str]] = 'li',
		postsPerPage: int = 10
	):
		super().__init__(True, baseUrl, urlFragments, ftype)
		self.titleSuffix = titleSuffix
		self.defaultDelay = 10
		self.containers = [('(', ')'), ('[', ']'), ('{', '}')]
		self.rewrites = [] if rewrites is None else rewrites
		self.postContainer = postContainer
		self.postsPerPage = postsPerPage
		self.mustyThreshold = 60 * 60 * 24 * 30 * 3  # 3 months ago

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		if self.baseUrl.endswith('/'):
			url = url.replace(self.baseUrl + '/', self.baseUrl)
		for rw in self.rewrites:
			url = url.replace(rw[0], rw[1])
		parts = url.split('/')
		httpOrHttps = (parts[0] == 'https:' or parts[0] == 'http:')
		if len(parts) < 5:
			return None
		frag = parts[2]
		if self.urlFragments[0].find('/') >= 0:
			frag += '/' + parts[3]
		if (not frag.endswith(self.urlFragments[0])) or (not httpOrHttps):
			return None

		parts = url[len(self.baseUrl):].split('/')

		if parts[0] == 'posts':
			nurl = scrape.resolveRedirects(url)
			if nurl == url:
				raise Exception('unable to resolve redirects: {}'.format(url))
			return self.tryParseUrl(nurl)
		if not parts[0].endswith('threads'):
			return None
		if len(parts) < 2 or len(parts[1].strip()) < 1:
			return None

		storyId_s = parts[1]
		storyId_s = storyId_s.split('.')[-1]
		if not storyId_s.isnumeric():
			return None  # might not have a full id yet
		storyId = int(storyId_s)
		chapterId = None
		ambi = True  # TODO: ? len(parts) < 6
		if ambi == False and len(parts[2].strip()) > 0:
			chapterId = int(parts[2])
		return FicId(self.ftype, str(storyId), chapterId, ambi)

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
		# TODO: should we try to get the actual url here, including the url safe
		# version of the title before the lid? Needs done elsewhere in this
		# adapter as well
		fic.url = self.baseUrl + 'threads/' + str(fic.localId)

		# scrape fresh info
		data = self.scrapeLike(fic.url)

		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		return Fic.lookup((fic.id, ))

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		contentId = util.randomString(8)
		while html.find(contentId) >= 0:
			contentId = util.randomString(len(contentId) + 1)
		soup = BeautifulSoup(f'<div id="{contentId}">{html}</div>', 'html5lib')

		# SB
		for spoiler in soup.find_all('div', {'class': 'bbCodeSpoiler'}):
			button = spoiler.find('button')
			title = spoiler.find('span', {'class': 'bbCodeSpoiler-button-title'})
			if title is not None and button is not None:
				t = soup.new_tag('span')
				t.append(title.get_text())
				button.insert_after(t)
			if button is not None:
				button.extract()
		for spoiler in soup.find_all('div', {'class': 'bbCodeSpoiler-content'}):
			spoiler.attrs['class'] = 'spoiler'

		# QQ
		for spoiler in soup.find_all('div', {'class': 'bbCodeSpoilerContainer'}):
			spoiler.attrs.pop('class')
			spoiler.name = 'span'
		for spoiler in soup.find_all('div', {'class': 'bbCodeSpoilerText'}):
			spoiler.attrs['class'] = 'spoiler'

		# for the proxy js based img tags, fiddle with their attributes so the
		# html cleanup code gets the proxy url out of .data-url and the original
		# upstream url from .src (or the proxy url if we don't have a real
		# upstream)
		for img in soup.find_all('img'):
			# proxy img tags have data-src but no actual src
			if 'data-src' not in img.attrs:
				continue
			if 'src' in img.attrs:
				continue

			src = img.attrs['data-src']
			if not src.startswith('http'):
				src = self.baseUrl + src
			altSrc = None
			if 'data-url' in img.attrs:
				altSrc = img.attrs['data-url']
			img.attrs['data-url'] = src
			img.attrs['src'] = src
			if altSrc:
				img.attrs['src'] = altSrc

		# general 'click to expand' nonsense
		for div in soup.find_all('div', {'class': 'quoteExpand'}):
			if div.get_text().strip() in {'Click to expand...', 'Click to expand…'}:
				div.extract()

		# CloudFlare protected "emails"
		for e in soup.find_all('a', {'class': '__cf_email__'}):
			if 'data-cfemail' not in e.attrs:
				continue
			t = e.get_text()
			if not t.startswith('[email') or not t.endswith('protected]'):
				continue
			cfemail = e.attrs['data-cfemail']
			email = util.decodeCloudFlareEmail(cfemail)
			util.logMessage(f'decoding email|{cfemail}|{email}')

			e.name = 'span'
			e.attrs.clear()
			e.string = email

		content = soup.find('div', {'id': contentId})
		content = content.contents
		if isinstance(content, list):
			content = content[0]
		return str(content)

	def getRealAuthorPost(self, fic: 'Fic') -> Any:
		from bs4 import BeautifulSoup
		url = self.baseUrl + 'threads/' + str(fic.localId)
		data = self.scrapeLike(url)

		soup = BeautifulSoup(data, 'html5lib')

		posts = soup.find_all(self.postContainer, {'class': 'message'})
		if len(posts) < 1:
			edumpContent(data, 'xen')
			raise Exception(f'error: unable to find author from {url}')
		return posts[0]

	def getCurrentInfo(self, fic: Fic) -> Fic:
		# scrape fresh info
		self.rescrapeFreshInfo(fic)

		data = self.scrapeLike(fic.url)
		return self.parseInfoInto(fic, data)

	def getPageCount(self, soup: Any) -> Tuple[int, bool]:
		# old style
		pageNav = soup.find_all('div', {'class': 'PageNav'})
		if (
			len(pageNav) >= 1 and pageNav[0] is not None
			and pageNav[0].get('data-last') is not None
		):
			pageNav = pageNav[0]
			pageCount = int(pageNav.get('data-last'))
			return (pageCount, True)

		# new style
		pageNav = soup.find('div', {'class': 'pageNav'})
		if pageNav is None:
			return (1, True)  # TODO?
		pageCount = 1
		for link in pageNav.findAll('li', {'class': 'pageNav-page'}):
			a = link.find('a')
			t = a.getText().strip()
			if not t.isnumeric():
				continue
			pageCount = max(pageCount, int(t))
		return (pageCount, False)

	def getDeepPageUrls(self, fic: Fic) -> List[str]:
		from bs4 import BeautifulSoup
		ficUrl = '{}threads/{}'.format(self.baseUrl, fic.localId)
		wwwHtml = self.scrapeLike(ficUrl)
		soup = BeautifulSoup(wwwHtml, 'html5lib')
		pageCount, _ = self.getPageCount(soup)
		if pageCount <= 1:
			return [ficUrl]
		urls = [ficUrl]
		for i in range(2, pageCount + 1):
			purl = self.baseUrl + 'threads/{}/page-{}'.format(fic.localId, i)
			urls += [purl]
		return urls

	def getReaderUrls(self, fic: Fic) -> List[str]:
		from bs4 import BeautifulSoup
		readerUrl = '{}threads/{}/reader'.format(self.baseUrl, fic.localId)
		wwwHtml = self.scrapeLike(readerUrl)
		soup = BeautifulSoup(wwwHtml, 'html5lib')
		pageCount, oldStyle = self.getPageCount(soup)
		if pageCount <= 1:
			# TODO? raise Exception('error: unable to find PageNav')
			return [readerUrl]
		urls = [readerUrl]
		for i in range(2, pageCount + 1):
			if oldStyle:
				if self.baseUrl.find('?') < 0:
					purl = f'{self.baseUrl}threads/{fic.localId}/reader?page={i}'
				else:
					purl = f'{self.baseUrl}threads/{fic.localId}/reader&page={i}'
			else:
				purl = f'{self.baseUrl}threads/{fic.localId}/reader/page-{i}'
			urls += [purl]
		return urls

	def deepSoftScrape(self, fic: Fic) -> None:
		# try to grab reader pages first to be sure we have them
		try:
			self.readerSoftScrape(fic)
		except:
			pass

		urls = self.getDeepPageUrls(fic)
		util.logMessage('deepSoftScrape|{}|{}'.format(fic.id, len(urls)))
		for url in urls:
			self.scrapeLike(url, 5)

	def readerSoftScrape(self, fic: Fic) -> None:
		urls = self.getReaderUrls(fic)
		util.logMessage(
			'readerSoftScrape|fic.id: {}|len(urls): {}'.format(fic.id, len(urls))
		)
		for url in urls:
			self.scrapeLike(url)

	def extractPostThreadmarkTitle(self, postSoup: Any) -> Optional[str]:
		title = ''
		# try to grab the title from the threadmark label
		try:
			labelSpans = postSoup.find_all('span', {'class': 'threadmarkLabel'})
			if len(labelSpans) < 1:
				return None
			if len(labelSpans) > 1:
				util.logMessage(
					f'XenForoAdapter: too many threadmark labels: len: {len(labelSpans)}'
				)
			return str(labelSpans[0].get_text()).strip()
		except Exception as e:
			util.logMessage(
				'\n'.join(
					[
						f'XenForoAdapter.extractPostThreadmarkTitle: exception FIXME: {e}',
						traceback.format_exc()
					]
				)
			)
		return None

	def getReaderPosts(self, fic: Fic) -> Tuple[Dict[str, Any], Dict[int, str]]:
		from bs4 import BeautifulSoup
		urls = self.getReaderUrls(fic)
		soups = {}
		titles = {}
		for url in urls:
			pageContent = self.scrapeLike(url)
			pageSoup = BeautifulSoup(pageContent, 'html5lib')
			posts = pageSoup.find_all(self.postContainer, {'class': 'message'})
			if len(posts) < self.postsPerPage and url != urls[-1]:
				util.logMessage(
					f'XenForoAdapter.getReaderPosts: {url} is not the last page but is incomplete with {len(posts)} posts; attempting to refetch'
				)
				pageContent = scrape.scrape(url, timeout=30)['raw']
				time.sleep(self.defaultDelay)
				pageSoup = BeautifulSoup(pageContent, 'html5lib')
				posts = pageSoup.find_all(self.postContainer, {'class': 'message'})
			if len(posts) < self.postsPerPage and url != urls[-1]:
				raise Exception(
					f'XenForoAdapter.getReaderPosts: {url} is not the last page but is incomplete with {len(posts)} posts'
				)
			for post in posts:
				pid = post.get('id')
				if pid.startswith('js-'):
					pid = pid[len('js-'):]
				soups[pid] = post
				title = self.extractPostThreadmarkTitle(post)
				if title is None:
					title = ''
				titles[len(soups)] = title

		util.logMessage(f'XenForoAdapter.getReaderPostUrls|{fic.id}|{len(soups)}')
		return (soups, titles)

	def getReaderPostUrls(self, fic: Fic) -> List[str]:
		from bs4 import BeautifulSoup
		urls = self.getReaderUrls(fic)
		postUrls: List[str] = []
		for url in urls:
			pageContent = self.scrapeLike(url)
			pageSoup = BeautifulSoup(pageContent, 'html5lib')
			posts = pageSoup.find_all(self.postContainer, {'class': 'message'})
			for post in posts:
				postUrls += [url + '#' + post.get('id')]
		return postUrls

	def getDeepAuthorPosts(self, fic: Fic) -> Dict[str, Any]:
		from bs4 import BeautifulSoup
		urls = self.getDeepPageUrls(fic)
		soups: Dict[str, Any] = {}
		for url in urls:
			pageContent = self.scrapeLike(url)
			pageSoup = BeautifulSoup(pageContent, 'html5lib')
			posts = pageSoup.find_all(
				self.postContainer, {
					'class': 'message',
					'data-author': fic.getAuthorName()
				}
			)
			for post in posts:
				soups[post.get('id')] = post
		return soups

	def getDeepAuthorPostUrls(self, fic: Fic) -> List[str]:
		urls = self.getDeepPageUrls(fic)
		util.logMessage(f'XenForo.getDeepAuthorPostUrls|deep page urls: {urls}')
		# TODO this should probably be more comprehensive...
		author = fic.getAuthorName()
		altAuthor = author.replace("'", '&#039;')
		postUrls: List[str] = []
		seenIdStubs = set()
		for url in urls:
			pageContent = self.scrapeLike(url)

			# See getReaderPostUrls for a fully parsed version
			for b in pageContent.split('<'):
				e = b.find('>')
				if e == -1:
					continue
				s = b[:e]
				# TODO FIXME this is bad :(
				# looking for li or article (the post container)
				if not (b.startswith('li id=') or b.startswith('article class=')):
					continue
				# check for 'message' -- simulates checking for message class
				if not 'message' in s:
					continue
				# to check the data-author we simply look for the author and hope
				# there aren't collisions
				if s.find(author) < 0 and s.find(altAuthor) < 0:
					continue
				# loop over spaced tokens looking for an unspaced id attribute
				for sb in s.split():
					if not sb.startswith('id="') or not sb.endswith('"'):
						continue
					idStub = sb[len('id="'):-1]
					if idStub.startswith('js-'):
						idStub = idStub[len('js-'):]
					postUrl = url + '#' + idStub
					if idStub not in seenIdStubs:
						postUrls += [postUrl]
					seenIdStubs |= {idStub}
		util.logMessage(f'XenForo.getDeepAuthorPostUrls|postUrls: {postUrls}')
		return postUrls

	def cacheAuthorPostImages(self, fic: Fic) -> None:
		purls = self.getDeepAuthorPostUrls(fic)
		posts = self.getDeepAuthorPosts(fic)  # Dict[str, BeautifulSoup]:
		dataUrls: Set[str] = set()
		imgSrc: Set[str] = set()

		ignoredAttrs = {'height', 'width', 'class', 'data-url', 'data-src'}
		usedAttrs = {'src', 'alt', 'title'}
		attrs: Set[str] = set()

		for purl in purls:
			pid = purl.split('#')[-1]
			if pid not in posts:
				raise Exception('unable to find soup for ' + pid)
			soup = posts[pid]
			imgs = soup.findAll('img')
			for img in imgs:
				for k in img.attrs:
					attrs |= {k}
				attrs = attrs - usedAttrs - ignoredAttrs
				if len(attrs) > 0:
					raise Exception('unknown attrs: {}'.format(attrs))

				src = img.get('src')
				if src is None:
					dataUrls |= {img.get('data-url')}
					continue
				if src.startswith('proxy.php?'):
					r = src[src.find('?') + 1:]
					qs = urllib.parse.parse_qs(r)
					if 'image' in qs and len(qs['image']) == 1:
						src = qs['image'][0]

				if src in imgSrc:
					continue

				title = img.get('title')
				alt = img.get('alt')
				if alt is not None:  # get rid of ZWS
					alt = alt.replace('\u200b', '').strip()

				# throwaway useless alts
				if alt is not None and alt.lower() == '[img]':
					alt = None

				print('    src: "{}"'.format(src))
				if title is not None:
					print('  title: "{}"'.format(title))
				if alt is not None:
					print('    alt: "{}" ({})'.format(alt, len(alt)))

				raise NotImplementedError('TODO: actually scrape images')
				#imgSrc |= { src }

		leftover = dataUrls - imgSrc
		if len(leftover) > 0:
			raise Exception('leftover img urls: {}'.format(leftover))

	def getLastFetchedThreadmarksUrl(self, fic: Fic) -> str:
		if self.baseUrl.find('?') >= 0:
			return self.getLastLikeOrDefault(
				[
					f'{self.baseUrl}threads/{fic.localId}/threadmarks&category_id=1',
					f'{self.baseUrl}threads/%.{fic.localId}/threadmarks&category_id=1',
				], f'{self.baseUrl}threads/{fic.localId}/threadmarks&category_id=1'
			)
		return self.getLastLikeOrDefault(
			[
				f'{self.baseUrl}threads/{fic.localId}/threadmarks?category_id=1',
				f'{self.baseUrl}threads/%.{fic.localId}/threadmarks?category_id=1',
			], f'{self.baseUrl}threads/{fic.localId}/threadmarks?category_id=1'
		)

	def getLastFetchedReaderUrl(self, fic: Fic) -> str:
		return self.getLastLikeOrDefault(
			[
				'{}threads/{}/reader_%'.format(self.baseUrl, fic.localId),
				'{}threads/%.{}/reader_%'.format(self.baseUrl, fic.localId),
			], '{}threads/{}/reader'.format(self.baseUrl, fic.localId)
		)

	def getLastFetchedReaderStartUrl(self, fic: Fic) -> str:
		return self.getLastLikeOrDefault(
			[
				'{}threads/{}/reader'.format(self.baseUrl, fic.localId),
				'{}threads/%.{}/reader'.format(self.baseUrl, fic.localId),
			], '{}threads/{}/reader'.format(self.baseUrl, fic.localId)
		)

	def getLastFetchedDeepUrl(self, fic: Fic) -> str:
		return self.getLastLikeOrDefault(
			[
				'{}threads/{}/page-%'.format(self.baseUrl, fic.localId),
				'{}threads/%.{}/page-%'.format(self.baseUrl, fic.localId),
			], '{}threads/{}'.format(self.baseUrl, fic.localId)
		)

	def getLastFetchedDeepStartUrl(self, fic: Fic) -> str:
		return self.getLastLikeOrDefault(
			[
				'{}threads/{}'.format(self.baseUrl, fic.localId),
				'{}threads/%.{}'.format(self.baseUrl, fic.localId),
			], '{}threads/{}'.format(self.baseUrl, fic.localId)
		)

	def getUrlsToRefetch(self, fic: Fic) -> Set[str]:
		return {
			self.getLastFetchedDeepUrl(fic),
			self.getLastFetchedDeepStartUrl(fic),
		}

	def rescrapeFreshInfo(self, fic: Fic) -> None:
		if scrape._staleOnly:
			return
		urls = self.getUrlsToRefetch(fic)
		for url in urls:
			scrape.scrape(url, timeout=30)
			time.sleep(self.defaultDelay)

		canFail = {
			self.getLastFetchedThreadmarksUrl(fic),
			self.getLastFetchedReaderUrl(fic),
			self.getLastFetchedReaderStartUrl(fic),
		}
		for url in canFail:
			try:
				scrape.scrape(url, timeout=30)
				time.sleep(self.defaultDelay)
			except Exception as e:
				# TODO
				if e.args[0].startswith('failed to download url 404:'):
					pass
				else:
					raise

	def getPostUpdatedOrPublished(self, post: Any) -> int:
		# old style xen foro
		messageMeta = post.find_all('div', {'class': 'messageMeta'})
		if len(messageMeta) == 1:
			dt = messageMeta[0].find_all('span', {'class': 'DateTime'})
			ts = None
			if len(dt) == 1:
				dt = dt[0]
				ts = dt.get('title')
			else:
				dt = messageMeta[0].find_all('abbr', {'class': 'DateTime'})
				if len(dt) != 1:
					raise Exception('error: unable to find message meta datetime')
				dt = dt[0]
				ts = dt.get_text()

			tsp = dateutil.parser.parse(ts)
			uts = util.dtToUnix(tsp)
			return uts

		if len(messageMeta) > 1:
			raise Exception('error: unable to find message meta')

		# new xen foro style
		lastEdit = post.find('div', {'class': 'message-lastEdit'})
		if lastEdit is not None:
			t = lastEdit.find('time')
			return int(t.get('data-time'))

		postPublish = post.find('div', {'class': 'message-attribution-main'})
		if postPublish is not None:
			t = postPublish.find('time')
			return int(t.get('data-time'))

		postPublish = post.find('header', {'class': 'message-attribution'})
		if postPublish is not None:
			t = postPublish.find('time')
			return int(t.get('data-time'))

		edumpContent(str(post), 'xen_post' + util.randomString())
		raise Exception('unable to find post update or publish ts')

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(wwwHtml, 'html5lib')

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")  # TODO: don't hard code?
		if fic.ficStatus is None or fic.ficStatus == FicStatus.broken:
			fic.ficStatus = FicStatus.ongoing

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0
		fic.ageRating = 'M'  # TODO?

		# grab title from <title> element
		titles = soup.find('head').find_all('title')
		if len(titles) != 1:
			raise Exception(f'error: cannot find title: {len(titles)}')
		ntitle = ''
		try:
			ntitle = titles[0].get_text()
		except:
			pass  # TODO FIXME
		if fic.title is None or len(ntitle.strip()) > 0:
			fic.title = ntitle
		if len(self.titleSuffix) > 0 and fic.title.endswith(self.titleSuffix):
			fic.title = fic.title[:-len(self.titleSuffix)]
		fic.title = fic.title.strip()

		# determine author
		authorPost = self.getRealAuthorPost(fic)
		authorPostUsernames = authorPost.find_all('a', {'class': 'username'})
		if len(authorPostUsernames) < 1:
			raise Exception('error: unable to find author username')
		author = authorPostUsernames[0].get_text()
		auth_href = authorPostUsernames[0].get('href')
		authorUrl = urllib.parse.urljoin(self.baseUrl, auth_href)
		if not authorUrl.startswith(self.baseUrl):
			raise Exception('error: unknown username href format')
		authorId = authorUrl[len(self.baseUrl):]
		if not authorId.startswith('members/'):
			raise Exception(f'error: unknown author id format: {authorId}')
		authorId = authorId.split('/')[1]
		self.setAuthor(fic, author, authorUrl, authorId)

		if fic.description is None:
			# TODO?
			fic.description = htmlEscape(fic.title + ' by ' + fic.getAuthorName())

		# try grabbing reader version, fallback to full pages
		threadmarksHtml = None
		try:
			sep = '?' if self.baseUrl.find('?') < 0 else '&'
			url = f'{self.baseUrl}threads/{fic.localId}/threadmarks{sep}category_id=1'
			threadmarksHtml = self.scrapeLike(url)
			self.readerSoftScrape(fic)
		except:
			# note: we do this before the theardmarks check for old-style fics
			# soft scrape all thread pages to ensure we have everything
			self.deepSoftScrape(fic)

		postSoups: Dict[str, Any] = {}

		postUrls: List[str] = []
		chapterTitles = {}
		try:
			# scrape the threadmarks page, assuming there is one
			threadmarksSoup = BeautifulSoup(threadmarksHtml, 'html5lib')

			# attempt to extract a fic description
			threadmarkExtraInfo = threadmarksSoup.find(
				'div', {'class': 'threadmarkListingHeader-extraInfo'}
			)
			if threadmarkExtraInfo is not None:
				bbWrapper = threadmarkExtraInfo.find('div', {'class': 'bbWrapper'})
				if bbWrapper is not None:
					desc = bbWrapper.decode_contents()
					descView = HtmlView(desc, markdown=False)
					fic.description = ''.join([f'<p>{l}</p>' for l in descView.text])

			# determine chapter count based on threadmarks
			threadmarkList = threadmarksSoup.find('div', {'class': 'threadmarkList'})
			threadmarks = None
			if threadmarkList is not None:
				threadmarks = threadmarkList.find_all(
					'li', {'class': 'threadmarkListItem'}
				)
			else:
				threadmarkList = threadmarksSoup.find(
					'div', {'class': 'block-body--threadmarkBody'}
				)
				if threadmarkList is None:
					raise Exception('error: unable to find threadmark menu')
				if threadmarkList.find(class_='fa-ellipsis-h') is not None:
					raise Exception('unable to handle elided threamdarks')
				threadmarks = threadmarkList.find_all('li')
				if len(threadmarks) == 0:
					threadmarks = threadmarkList.find_all('tr')
				util.logMessage(f'XenForo|new threadmarks count|{len(threadmarks)}')

			for threadmark in threadmarks:
				if threadmark.find(
					'span', {'class': 'message-newIndicator'}
				) is not None:
					continue
				a = threadmark.find('a')
				purl = a.get('href')
				if purl.startswith('threads/'):
					purl = '{}{}'.format(self.baseUrl, purl)
				elif purl.startswith('/threads/'):
					purl = '{}{}'.format(self.baseUrl, purl[1:])
				postUrls += [purl]

				chapterTitles[len(postUrls)] = a.getText().strip()

			try:
				postSoups, _ = self.getReaderPosts(fic)
			except Exception as ie:
				# FIXME oh boy:
				# https://forum.questionablequesting.com/threads/worm-cyoa-things-to-do-in-brockton-bay-when-youre-a-bored-demigod.1247/reader
				# Reader page says 36 threadmarks, but actual threadmark list says 33
				# First reader page abruptly stops at 27 threadmarks
				util.logMessage(
					'XenForoAdapter: unable to getReaderPosts: {}\n{}'.format(
						ie, traceback.format_exc()
					)
				)
		except Exception as e:
			util.logMessage(
				'XenForoAdapter: unable to parse threadmarks: {}\n{}'.format(
					e, traceback.format_exc()
				)
			)
			try:
				postUrls = self.getReaderPostUrls(fic)
				postSoups, chapterTitles = self.getReaderPosts(fic)
			except Exception as ie:
				util.logMessage(
					'XenForoAdapter: unable to parse reader posts: {}\n{}'.format(
						ie, traceback.format_exc()
					)
				)
				postUrls = self.getDeepAuthorPostUrls(fic)
				# if we fallback to here, don't immediately setup postSoups at all;
				# they'll be fetched as needed later

		fic.chapterCount = len(postUrls)

		chapterPosts: List[Optional[str]] = []
		chapterUrls: List[str] = []
		chapterPostIds: List[str] = []

		lastSoupUrl: Optional[str] = None
		lastSoup: Optional[Any] = None

		for purl in postUrls:
			parts = purl.split('#')
			burl = parts[0]
			postId = authorPost.get('id') if len(parts) < 2 else parts[1]

			rawPost = None
			# first try getting the post from the reader pages
			if postId in postSoups and postSoups[postId] is not None:
				rawPost = str(postSoups[postId])
			else:
				# if needed, fallback to grabbing that page from the entire thread
				pageSoup = None
				if lastSoupUrl is not None and lastSoupUrl == burl:
					pageSoup = lastSoup
				else:
					pageContent = self.scrapeLike(burl)
					pageSoup = BeautifulSoup(pageContent, 'html5lib')
					lastSoupUrl = burl
					lastSoup = pageSoup
				assert (pageSoup is not None)
				if postId is not None:
					poss = pageSoup.find_all(self.postContainer, {'id': postId})
					if len(poss) != 1:
						# XenForo2 often has js- prefixed on the actual id attr
						poss = pageSoup.find_all(self.postContainer, {'id': 'js-' + postId})
					if len(poss) != 1:
						raise Exception(f'error: cannot find post for chapter {postId}')
					rawPost = str(poss[0])
				else:
					rawPost = str(
						pageSoup.find_all(self.postContainer, {'class': 'message'})[0]
					)

			chapterPosts += [rawPost]
			chapterUrls += [burl]
			chapterPostIds += [postId]

		fic.wordCount = 0
		fic.published = None
		fic.updated = None

		chapterContents: List[str] = []
		for rawPost in chapterPosts:
			post = BeautifulSoup(rawPost, 'html5lib')
			content = post.find_all(
				'div', {'class': ['messageContent', 'message-content']}
			)
			if len(content) != 1:
				raise Exception('error: cannot find content for chapter post')
			content = content[0]

			lastEditedDivs = content.find_all('div', {'class': 'message-lastEdit'})
			for lastEditedDiv in lastEditedDivs:
				br = soup.new_tag("br")
				lastEditedDiv.insert_before(br)

			chapterContents += [str(content)]
			fic.wordCount += len(str(content).split())

			uts = self.getPostUpdatedOrPublished(post)

			if fic.published is None:
				fic.published = OilTimestamp(uts)
			fic.updated = OilTimestamp(uts)

		if fic.updated is None:
			raise Exception(
				f'unable to determine updated date: {len(chapterPosts)} {len(postUrls)}'
			)

		fic.upsert()
		for cid in range(fic.chapterCount):
			chapter = fic.chapter(cid + 1)
			chapter.url = chapterUrls[cid]
			chapter.localChapterId = chapterPostIds[cid]
			if (cid + 1) in chapterTitles:
				chapter.title = chapterTitles[(cid + 1)]
			chapter.upsert()

			chapter.setHtml(str(chapterContents[cid]))

		# TODO: word count, published, updated can only be found once all chapters

		# each post is inside an li id="post-{number}" class="message"
		# each post has data-author="{author}"

		self.updateTitle(fic)

		return fic

	def updateTitle(self, fic: Fic) -> None:
		if fic.title is None: return
		completeTags = ['complete', 'completed']
		# look for Complete tag in the title
		for cont in self.containers:
			for completeTag in completeTags:
				ctag = cont[0] + completeTag + cont[1]
				cloc = fic.title.lower().find(ctag)
				if cloc != -1:
					fic.title = fic.title[:cloc] + fic.title[cloc + len(ctag):]
					fic.ficStatus = FicStatus.complete
				fic.title = fic.title.strip()
				fic.title = fic.title.replace('  ', ' ')

		# strip '[nsfw]' tag from anywhere in title
		for cont in self.containers:
			ntag = cont[0] + 'nsfw' + cont[1]
			nloc = fic.title.lower().find(ntag)
			if nloc != -1:
				fic.title = fic.title[:nloc] + fic.title[nloc + len(ntag):]
				fic.ageRating = 'M'  # TODO?
			fic.title = fic.title.strip()
			fic.title = fic.title.replace('  ', ' ')

		res = self.cleanTitle(fic.title)
		fic.title = res[0]
		for fan in res[1]:
			fic.add(Fandom.define(fan))
		for tag in res[2]:
			fic.add(Tag.define(tag))
		fic.upsert()

	def cleanTitle(self, title: str) -> Tuple[str, Set[str], Set[str]]:
		# TODO: look for bits inside containers, then try to split on common
		# things like , and /, then match against existing known fandoms
		# (fragment, [fandom], [tags])
		fandomFragments: List[Tuple[str, List[str], List[str]]] = [
			('Alt!Power', [], ['altpower']),
			('Altpower!Taylor / Worm', ['Worm'], ['altpower']),
			('A:tLA', ['Avatar'], []),
			('Dragon Ball', ['Dragon Ball'], []),
			('Exalted/Worm', ['Worm', 'Exalted'], []),
			('Gundam x Worm', ['Worm', 'Gundam'], []),
			('Harry Potter AU', ['Harry Potter'], []),
			('Harry Potter', ['Harry Potter'], []),
			('Harry Potter/Star Wars', ['Harry Potter', 'Star Wars'], []),
			('Infinite Stratos', ['Infinite Stratos'], []),
			('LoZ', ['Legend of Zelda'], []),
			('Modified Pokemon CYOA', ['Pokemon'], ['CYOA']),
			('Naruto', ['Naruto'], []),
			('Neon Genesis Evangelion', ['Neon Genesis Evangelion'], []),
			('Overwatch', ['Overwatch'], []),
			('Pokemon', ['Pokemon'], []),
			('RWBY/The Gamer', ['RWBY', 'The Gamer'], []),
			('Sailor Moon', ['Sailor Moon'], []),
			('SAO', ['Sword Art Online'], []),
			('Stargate: Atlantis', ['Stargate Atlantis'], []),
			('Worm Altpower/AU', ['Worm'], ['altpower']),
			(
				'Worm alt power/crossover Hellsing Ultimate', ['Worm', 'Hellsing'], [
					'altpower'
				]
			),
			('Worm Altpower Fic', ['Worm'], ['altpower']),
			(
				'Worm | AltPower | Simurgh!Taylor', ['Worm'], [
					'altpower', 'Simurgh!Taylor'
				]
			),
			('Worm altpower!Taylor', ['Worm'], ['altpower']),
			('Worm Altpower', ['Worm'], ['altpower']),
			('Worm Alt!Power', ['Worm'], ['altpower']),
			('Worm, Alt Power', ['Worm'], ['altpower']),
			('Worm Alt Power/X-Men', ['Worm', 'X-Men'], ['altpower']),
			('Worm AU, Altpower', ['Worm'], ['altpower']),
			('Worm AU/Altpower', ['Worm'], ['altpower']),
			('Worm/AU/Altpower', ['Worm'], ['altpower']),
			('Worm AU Alt!Power', ['Worm'], ['altpower']),
			('Worm, AU, Alt-Power', ['Worm'], ['altpower']),
			('Worm, AU, AltPower', ['Worm'], ['altpower']),
			('Worm/AU/Alt-Power', ['Worm'], ['altpower']),
			('Worm AU fanfic', ['Worm'], []),
			('Worm AU', ['Worm'], []),
			('Worm/Bayonetta', ['Worm', 'Bayonetta'], []),
			('Worm/Bionicle', ['Worm', 'Bionicle'], []),
			('Worm/Bleach', ['Worm', 'Bleach'], []),
			('Worm/Bloodborne Crackfic', ['Worm', 'Bloodborne'], ['crackfic']),
			('Worm CYOA/SI', ['Worm'], ['CYOA', "SI"]),
			('Worm/Diebuster', ['Worm', 'Diebuster'], []),
			('Worm/Dragonball', ['Worm', 'Dragon Ball'], []),
			('Worm/Exalted Crossover', ['Worm', 'Exalted'], []),
			('Worm/Exalted', ['Worm', 'Exalted'], []),
			('Worm Fanfic (AU)', ['Worm'], []),
			('Worm Fic', ['Worm'], []),
			('Worm/Heroes', ['Worm', 'Heroes'], []),
			('Worm/JoJo SI', ['Worm', "JoJo's Bizarre Adventure"], ["SI"]),
			('Worm/Lilo and Stitch', ['Worm', 'Lilo and Stitch'], []),
			('Worm/Okami', ['Worm', 'Okami'], []),
			('Worm/Overwatch', ['Worm', 'Overwatch'], []),
			('Worm/Pokemon', ['Worm', 'Pokemon'], []),
			('Worm/Skyrim/Gamer', ['Worm', 'Skyrim'], ['gamer']),
			('Worm/Spore', ['Worm', 'Spore'], []),
			('Worm/Stargate', ['Worm', 'Stargate'], []),
			('Worm/Steven Universe', ['Worm', 'Steven Universe'], []),
			('Worm/SupCom', ['Worm', 'Supreme Commander'], []),
			('Worm/Supreme Commander', ['Worm', 'Supreme Commander'], []),
			('Worm/Tokyo Ghoul', ['Worm', 'Tokyo Ghoul'], []),
			('Worm/Transformers', ['Worm', 'Transformers'], []),
			('Worm', ['Worm'], []),
			('Worm/WTNV', ['Worm', 'Welcome to Night Vale'], []),
			('Worm|Xiaolin Showdown', ['Worm', 'Xiaolin Showdown'], []),
			('Worm x Naruto', ['Worm', 'Naruto'], []),
			('Worm X Undertale', ['Worm', 'Undertale'], []),
		]
		titleFandoms: Set[str] = set()
		titleTags: Set[str] = set()

		hadFrag = True
		while hadFrag:
			title = title.replace('  ', ' ')
			title = title.strip()
			hadFrag = False
			for ff in fandomFragments:
				fragContents = ff[0]
				fans: List[str] = ff[1]
				tags: List[str] = ff[2]
				for cont in self.containers:
					frag = cont[0] + fragContents + cont[1]
					fragLoc = title.lower().find(frag.lower())
					if fragLoc != -1:
						hadFrag = True
						title = title[:fragLoc] + title[fragLoc + len(frag):]
						for fan in fans:
							titleFandoms |= {fan}
						for tag in tags:
							titleTags |= {tag}

		if title.startswith('- '):
			title = title[len('- '):]

		title = title.strip()
		title = title.replace('  ', ' ')
		return (title, titleFandoms, titleTags)

	def scrapeLike(self, url: str, delay: int = None) -> str:
		url = scrape.canonizeUrl(url)
		if delay is None:
			delay = self.defaultDelay
		prefix = self.baseUrl + 'threads/'
		if not url.startswith(prefix):
			data = scrape.softScrape(url, delay, mustyThreshold=self.mustyThreshold)
			if data is None:
				raise Exception('unable to soft scrape? FIXME')
			return data

		ulike = url[len(prefix):]
		parts = ulike.split('/')
		parts[0] = parts[0].split('.')[-1]
		canon = prefix + '/'.join(parts)
		parts[0] = '%.' + parts[0]
		ulike = prefix + '/'.join(parts)

		# FIXME canon may find an older url than ulike :/

		canonRes = scrape.getMostRecentScrapeWithMeta(canon)
		if (
			canonRes is not None
			and int(time.time()) - self.mustyThreshold < canonRes['fetched']
		):
			return cast(str, canonRes['raw'])

		data = scrape.softScrape(
			url, delay, ulike, mustyThreshold=self.mustyThreshold
		)
		if data is None:
			raise Exception('unable to soft scrape? FIXME')
		return data
