import curses
import re
from typing import TYPE_CHECKING, List, Tuple, Union, Dict, Optional, Any
if TYPE_CHECKING:
	from hermes import Hermes
import html

import util
from htypes import FicType
from store import FicStatus, Fic, FicChapter
from view.widget import Widget


class HtmlView:
	def __init__(
		self,
		html: str,
		markdown: bool = True,
		extraTitles: List[str] = None
	) -> None:
		hrRes = [
			'[!/\\\\&#~*_XxIiOoHhPpsVv80°¤ :.…=><12)(+\[\]-]{3,}',
			'[~0-9]{3,}',
			'[ua-]{5,}',
			'(.)\\1{10,}',
			'(.)(.)(\\1\\2){5,}\\1?\\2?',
			'(.)(.)(.)(\\1\\2\\3){5,}\\1?\\2?\\3?',
			'(.{2,}) ?(\\1 ?){3,}',
			'(.{5,}) ?(\\1 ?){2,}',
			'[\'~`^,._=-]{4,}',
		]
		self.gamerRe = re.compile(
			'^([HhMmXx][Pp]:? [0-9]+|[+-]?[0-9]+ [HhMmXx][Pp].?)'
		)
		self.hrRes = [re.compile('^' + r + '$') for r in hrRes]
		self.extraTitles: List[str] = [] if extraTitles is None else extraTitles
		self.spaceRe = re.compile('\s+')
		self.text: List[str] = []
		self.markdown = markdown
		self.__processHTML(html)

	def __addLines(self, lines: List[str]) -> None:
		for line in lines:
			self.__addLine(line)

	def __addLine(self, line: str) -> None:
		if self.markdown:
			line = html.unescape(line)
		line = util.filterUnicode(line)

		line = line.replace('Sony', 'Sonny')  # TODO: hack...
		line = line.strip()

		if line in {
			'Work Text:', 'Chapter Text', 'Next Chapter', 'Last Chapter Next Chapter'
		}:
			return

		# filter out blank/all-space lines
		if line.isspace() or len(line) == 0:
			return

		if line.strip() in {'_‗_', '___', 'Prev Main Next'}:
			return

		hrTitles = [
			"~~bonds of blood~~", "~~bonds of bloods~~", "- dp & sw: ribsr -",
			"- dp & sw: tfop -", "hp & ha - safh", "_‗_", "-==(oio)==-", '\\""/', 'ˇ',
			'#', '##', '###', '* *', ' ', '.', '-.-fh-.-', '-break-',
			'oracle2phoenix', '/', '(break)', 'dghpdghpdghp', 'my',
			'hp*the aftermath*hp', '~~~core threads~~~',
			'-saving her saving himself-', '{1}', '{2}', '{3}', 'scene break',
			'scenebreak', 'xxscenebreakxx', '[-]', '{-}', 'x', '_x_', '%', '[{o}]',
			'section break', '- break -', '-- story --', '(line break)', '-()-', '<>',
			'~<>~', '~', '(⊙_⊙) ', '(∞)', '!', "','", '!ditg!', '-{}-',
			'┐(￣ヘ￣)┌┐(￣ヘ￣)┌┐(￣ヘ￣)┌', "'OvO'", 'www', '-|-|-', '~•~', '::',
			'scene break>', '-l-l-l-', '-line break-', ':)', ';)', ':', '-= LP =-',
			'f/klpt', '~*~*~*~*~ harry&pansy ~*~*~*~*~', '....', '….', '%%%', '˄',
			'˅', '-----===ͽ ˂ O ˃ ͼ===-----', '-----===ͽ Δ ͼ===-----',
			'xxxxxxx story xxxxxxx', 'line break', 'titanfall'
		] + self.extraTitles

		squiggleBreaks = ['flashback', 'end flashback', 'time skip']

		# strip markdown tags
		mhr = line.strip('*_').lower()

		# strip non-markdown tags
		while (
			(mhr.startswith('<strong>') and mhr.endswith('</strong>'))
			or (mhr.startswith('<em>') and mhr.endswith('</em>'))
		):
			if (mhr.startswith('<strong>') and mhr.endswith('</strong>')):
				mhr = mhr[len('<strong>'):-len('</strong>')]
			if (mhr.startswith('<em>') and mhr.endswith('</em>')):
				mhr = mhr[len('<em>'):-len('</em>')]

		matchesHrRe = False
		for hrRe in self.hrRes:
			if hrRe.match(mhr) is not None:
				matchesHrRe = True
				break
		if mhr == '"yes." "yes." "yes."' or mhr.startswith('hp: '):
			matchesHrRe = False
		if matchesHrRe and self.gamerRe.match(mhr):
			matchesHrRe = False
		# normalize weird h-rules
		if (
			line == '***' or mhr == '<hr />' or mhr == '-' or mhr == '--'
			or (len(line) > 0 and len(mhr) == 0) or matchesHrRe
		):
			line = '<hr />'
		else:
			for hrTitle in hrTitles:
				if mhr == hrTitle.lower():
					line = '<hr />'
					break
			sq = mhr.strip('~')
			for squiggleBreak in squiggleBreaks:
				if sq == squiggleBreak:
					line = '<hr />'
					break
		if (
			(len(line) - len(line.strip('=')) > 8)
			and (line.strip('=') == 'HG/MM' or line.strip('=') == 'MM/HG')
		):
			line = '<hr />'
		if (mhr.strip('~') == 'avengers tower'):
			line = '*Avengers Tower*'  # TODO
		if (mhr.find('oo--oo--') >= 0 and mhr.find('FLASHBACK')):
			line = '<hr />'
		if mhr.find('hp - 260 g o 16 - hp - 260 g o 16 - hp - 260 g o 16') != -1:
			line = '<hr />'
		if len(mhr) > 10 and mhr.count('x') > len(mhr) * 0.7:
			line = '<hr />'

		if len(self.text) > 0 and line == '<hr />' and self.text[-1] == '<hr />':
			return

		line = util.filterEmptyTags(line)

		# blow up on very long lines (TODO: graceful)
		if len(line) > (80 * 60 * 1000000):  # TODO
			raise Exception(
				'error: extremely long line: {}\n{}'.format(len(line), line)
			)

		self.text += [line]

	def __processHTML(self, htmlText: str) -> None:
		# strip simple scripts TODO needs to be much better...
		try:
			htmlText = re.sub('<script>.*?</script>', '', htmlText, flags=re.DOTALL)
			htmlText = re.sub(
				'<noscript>.*?</noscript>', '', htmlText, flags=re.DOTALL
			)
			htmlText = re.sub(
				'<!--\[if lt IE 8\]>.*?<!\[endif\]-->', '', htmlText, flags=re.DOTALL
			)
			htmlText = htmlText.replace(
				'Buy our stuff, go here to find out more: <a href="https://forums.spacebattles.com/threads/spacebattles-merchandise.398032/">https://forums.spacebattles.com/threads/spacebattles-merchandise.398032/</A>',
				''
			)
		except:
			pass

		# bleh, remove badly encoded newlines and extra backslashes
		htmlText = htmlText.replace('\\n', '\n')  # bleh
		htmlText = htmlText.replace('\\r', '\n')  # bleh
		htmlText = htmlText.replace('\\\\', '\\')  # bleh

		# remove redundant open/close tags; prevents extra space from next step
		for t in ['strong', 'b', 'bold', 'em', 'i']:
			htmlText = htmlText.replace(f'</{t}><{t}>', '')

		# add an extra space after em close, it'll get squashed later if it's a
		# duplicate, otherwise it keeps words from running together
		htmlText = htmlText.replace('</em>', '</em> ')

		# replace whitespace only divs with line breaks
		htmlText = htmlText.replace('<div>&nbsp;</div>', '<br>')  # FIXME
		htmlText = htmlText.replace('<div> </div>', '<br>')  # FIXME
		htmlText = htmlText.replace(u'<div>\u200b</div>', '<br>')  # FIXME

		# decode nbsp into regular space
		htmlText = htmlText.replace("&nbsp;", ' ').replace('&#8203;', ' ')

		# squash two single quotes into double quotes
		htmlText = htmlText.replace("‘’", '"').replace("’’", '"').replace("''", '"')

		# strip pointless tags around spaces
		for t in ['strong', 'b', 'bold', 'em', 'i']:
			htmlText = htmlText.replace(f'<{t}> </{t}>', ' ')

		emptyThreshold = 0.35
		# if more than emptyThreshold% of all paragraphs are empty, then the text
		# is probably double spaced and we can just remove the empty ones
		emptyP = '<p> </p>'
		if (htmlText.count(emptyP) > emptyThreshold * htmlText.count('<p>')):
			htmlText = htmlText.replace(emptyP, '')

		# otherwise double spacing is probably meant to be a scene break
		if htmlText.count('<p> </p>') <= 160:
			htmlText = htmlText.replace('<p> </p>', '<hr />')

		# squash multiple breaks embedded in paragraphs into a single scene break
		htmlText = htmlText.replace('<br>\n' * 8, '<br><br>')
		htmlText = htmlText.replace('<br>\n\n' * 8, '<br><br>')
		breakRe = re.compile('<p>([\s\n]*<br/?>[\s\n]*)+</p>', re.MULTILINE)
		htmlText = breakRe.sub('<hr />', htmlText)
		htmlText = htmlText.replace('<p><br/>\n<br/>\n</p>', '<hr />')
		htmlText = htmlText.replace('<p><br/>\n<br/>\n<br/>\n</p>', '<hr />')

		# replace unicode nbsp with regular space
		htmlText = htmlText.replace(' ', ' ').replace(u'\u200b', ' ')

		# replace centered stars with scene break
		htmlText = htmlText.replace(
			'<div style="text-align: center">*** </div>', '<hr />'
		)

		# fix annoying <<< >>> scene breaks...
		# looking at you stranger in an unholy land
		htmlText = htmlText.replace('<<< >>>', '<hr />')

		# normalize all spaces into actual spaces (newlines, tabs, etc)
		htmlText = self.spaceRe.sub(' ', htmlText)

		if htmlText.find('<') == -1:
			self.__addLine(htmlText)
			return

		htmlText = htmlText.replace('<col/>', '')  # FIXME
		# TODO something more generic?
		# https://harrypotterfanfiction.com/viewstory.php?psid=126760
		htmlText = htmlText.replace('<I/>', '</i>').replace('<i/>', '</i>')
		# https://www.fanfiction.net/s/1638751/2
		htmlText = htmlText.replace('</i? she', '</i>? she')

		# we generate our own word breaks...
		htmlText = htmlText.replace('<wbr/>', '')
		htmlText = htmlText.replace('<wbr>', '')

		# FIXME ch16 is broken
		# https://www.fanfiction.net/s/6859461/16/I-Put-On-My-Robe-And-Wizard-Hat
		htmlText = htmlText.replace(
			b''.join(
				[
					b'p\xe2\x89\xaf\xcc\xa2\xcc\xa9\xcc\xab\xcc\xa0\xcc\x89\xcc\x8a\xcd'
					b'\xa6\xcd\xa4\xcd\xad\xcc\x8a..\xcc\xb7\xcd\x99\xcd\xaf\xcc\x8a\xcc',
					b'\xbd\xcc\x93\xcd\x86\xcc\x89\xcd\xab.\xcd\x87\xcc\xaa\xcd\xa7\xcc',
					b'\x85\xcc\x81</p',
				]
			).decode('utf-8'), 'p>../.</p'
		)

		# FIXME https://www.fanfiction.net/s/26926/1/Destiny-s-Child
		htmlText = htmlText.replace('<saran@first.com.my>', 'saran@first.com.my')
		htmlText = htmlText.replace('<ranmas@kode.net>', 'ranmas@kode.net')
		if (
			htmlText.find("<\"I'm sorry Miss") >= 0
			or htmlText.find("<\"Great Grandmother,") >= 0
		):
			from bs4 import BeautifulSoup  # type: ignore
			soup = BeautifulSoup(htmlText, 'html5lib')
			htmlText = str(soup)

		# FIXME https://www.fanfiction.net/s/2644/1/The-Bodyguard
		htmlText = htmlText.replace(
			'<efrancis@earthlink.net>', 'efrancis@earthlink.net'
		)

		# skip all tags that start with... (case insensitive)
		ignoreTags = [
			'!doctype', '!--', 'html', '/html',
			'head', '/head', 'peta', '/peta', 'title', '/title',
			'body', '/body', 'pont', '/pont', 'font', '/font',
			'o:p', '/o:p', 'fido', '/fido',
			'span', '/span',
			'h2',
			'/hr', '/br',
			'select', '/select', 'option',
			'button', '/button',
			'center', '/center',
			'sup', '/sup',
			'h3', 'ul', '/ul', 'li', '/li',
			'iframe', '/iframe',
			'h1', 'u', '/u',
			'x1',
			'del', '/del', 'address', '/address',
			'big', '/big', 'ol', '/ol',
			'table', '/table', 'tbody', '/tbody', 'tr', '/tr', 'td', '/td',
			'thead', '/thead',
			'time', '/time', 'footer', '/footer',
			'small', '/small',
			'xtml', '/xtml', 'xead', '/xead', 'dir', '/dir',
			'strike', '/strike', # TODO don't ignore
			'h4', '/h4', 'h5', '/h5', 'h6', '/h6',
			'pre', '/pre', # TODO
			'article', '/article',
			'aside', '/aside', # TODO
			'noscript', '/noscript', # TODO
			'dl', '/dl', 'dt', '/dt', 'dd', '/dd', # TODO
			'script', '/script', # TODO: dump contents too
			'![cdata[', # TODO
			'ppan', '/ppan', # TODO
			'cite', '/cite', # TODO
			'abbr', '/abbr', # TODO
			'sub', '/sub', # TODO
			'code', '/code', # TODO
			'meta', # TODO
			'kbd', '/kbd', # TODO
			'link', # TODO
			'xink', # TODO https://www.fanfiction.net/s/194972/1/Evolution
			'xlink', 'xmeta', 'xbody', # TODO https://www.fanfiction.net/s/736414
			'acronym', '/acronym', # TODO

			'xml', '/xml',
			'style', '/style', 'ptyle', '/ptyle',
			'form', '/form', 'object', '/object',
			'al', '/al', 'blink', '/blink', 'blue', '/blue', 'doc', '/doc',
			'input', '/input', 'marquee', '/marquee', 'noembed', '/noembed',
			'option', '/option', 'o:smarttagtype', '/o:smarttagtype',
			'u1:p', '/u1:p', 'u2:p', '/u2:p',

			'th', '/th', 'tt', '/tt',
			'url', '/url', 'vr', '/vr', 'wbr', '/wbr',

			'fieldset', '/fieldset',
			'legend', '/legend',

			'nav', '/nav',

			'caption', '/caption', # TODO
			'main', '/main', # TODO
			'section', '/section', # TODO
			'header', '/header', # TODO
			'base', '/base', # TODO
			'label', '/label', # TODO
			'![if', '![endif]--', '![endif]', # TODO

			'ruby', '/ruby', 'rb', '/rb', 'rp', '/rp', 'rt', '/rt', # TODO oogways owl

			'colgroup', '/colgroup', 'col', '/col', # TODO

			# TODO svg elements
			'svg', '/svg', 'g', '/g', 'path', '/path', 'text', '/text',
			'circle', '/circle',

			'figure', '/figure', # TODO is this also svg or just caption like?

			'dfn', '/dfn', # FIXME https://royalroad.com/fiction/25137

			# FIXME https://forums.spacebattles.com/threads/476176
			'video', '/video', 'source', '/source',

			'o:documentproperties', '/o:documentproperties',
			'o:author', '/o:author', 'o:lastauthor', '/o:lastauthor',
			'o:template', '/o:template',
			'o:revision', '/o:revision',
		] # yapf: disable

		# FIXME nested tags: <!-- <p>thing</p> -->
		if self.markdown:
			ignoreTags += ['div', '/div']

		# st1: and st2: ?
		#	city, place, country-region, placename, platetype, postalcode, street,
		#	address, state, time, date, personname, givenname, sn,
		#	metricconverter, stockticker, numconv, middlename

		tagCount = 0
		cline = ""
		idx = 0
		textLen = len(htmlText)

		while idx < textLen:
			# find next tag
			nopen = htmlText.find('<', idx)

			# if there are no more tags, the rest is pure text
			if nopen == -1:
				cline += htmlText[idx:]
				break

			# if there's text before the tag, add it to the current line
			if nopen != 0:
				cline += htmlText[idx:nopen]
				idx = nopen

			tagCount += 1
			# there is another tag, find the end
			nclose = htmlText.find('>', nopen)

			if nclose < nopen:
				raise Exception('open tag with no close: {}'.format(nopen))

			# yank tag body
			originalFullInner = htmlText[nopen + 1:nclose].strip()
			fullInner = originalFullInner.lower()
			inner = fullInner
			if len(fullInner.split()) > 0:
				# only look at the initial piece of the tag
				inner = fullInner.split()[0]

			if inner.startswith('!--') or len(inner) < 1:
				idx = nclose + 1
				continue

			# check if it's in our generic ignore list
			didIgnore = False
			for itag in ignoreTags:
				if inner == itag:
					idx = nclose + 1
					didIgnore = True
					break
			if (
				inner[:4] == 'st1:' or inner[:4] == 'st2:' or inner[:5] == '/st1:'
				or inner[:5] == '/st2:' or inner[:2] == 'o:' or inner[:3] == '/o:'
				or inner[:2] == 'w:' or inner[:3] == '/w:'
			):
				idx = nclose + 1
				didIgnore = True
			if didIgnore:
				continue

			# in non-markdown we keep plain divs
			if not self.markdown:
				if inner == '/div':
					cline += '</div>'
					idx = nclose + 1
					continue
				if fullInner == 'div class="spoiler"':
					cline += '<div class="spoiler">'
					idx = nclose + 1
					continue
				if inner == 'div':
					cline += '<div>'
					idx = nclose + 1
					continue

			# images are replaced with their src
			if inner == 'img':
				if len(cline) > 0:
					self.__addLine(cline)
					cline = ''
				try:
					from bs4 import BeautifulSoup
					soup = BeautifulSoup(f'<{originalFullInner}>', 'html5lib')
					img = soup.find('img')
					src = None
					ltext = None
					if 'data-url' in img.attrs:
						src = img.attrs['data-url']
						if 'src' in img.attrs:
							ltext = img.attrs['src']
					else:
						src = img.attrs['src']
					if ltext is None:
						ltext = src
					if src.startswith('http://') or src.startswith('https://'):
						self.__addLine(
							f'[img: <a href="{src}" rel="noopener noreferrer">{ltext}</a>]'
						)
				except:
					util.logMessage(f"HtmlView: error: bad img: {fullInner}")
					pass
				idx = nclose + 1
				continue

			# links keep only their href if it's http/https
			if inner == '/a':
				cline += '</a>'
				idx = nclose + 1
				continue
			if inner == 'a':
				try:
					from bs4 import BeautifulSoup
					soup = BeautifulSoup(f'<{originalFullInner}>', 'html5lib')
					a = soup.find('a')
					href = a.attrs['href']
					if href.startswith('http://') or href.startswith('https://'):
						cline += f'<a href="{href}" rel="noopener noreferrer">'
				except:
					if fullInner != 'a':
						util.logMessage(f"HtmlView: error: bad a: {fullInner}")
					pass
				idx = nclose + 1
				continue

			# horizontal rules remain like html; translate blockquote into hr
			if inner in {'hr', 'hr/', 'blockquote', '/blockquote'}:
				self.__addLines([cline, '<hr />'])
				cline = ''
				idx = nclose + 1
				continue

			# a few things advance to the next line
			if inner == 'br' or inner == 'br/':
				# if we've just got a start tag don't actually advance the line
				if not (
					len(cline.strip()) == 1 and len(cline.strip().strip('*_')) == 0
				):
					self.__addLine(cline)
					cline = ''
				idx = nclose + 1
				continue

			if inner in {'p', '/p', '/h1', '/h2', '/h3'}:
				if len(cline) > 0:
					self.__addLine(cline)
				cline = ''
				idx = nclose + 1
				continue

			# if our target is not markdown, only standardize on strong and em
			if self.markdown == False:
				if (inner == 'strong' or inner == 'b' or inner == 'bold'):
					cline += '<strong>'
					idx = nclose + 1
					continue
				if (inner == '/strong' or inner == '/b' or inner == '/bold'):
					cline += '</strong>'
					idx = nclose + 1
					continue
				if (inner == 'em' or inner == 'i'):
					cline += '<em>'
					idx = nclose + 1
					continue
				if (inner == '/em' or inner == '/i'):
					cline += '</em>'
					idx = nclose + 1
					continue
				if inner == 's':
					cline += '<s>'
					idx = nclose + 1
					continue
				if inner == '/s':
					cline += '</s>'
					idx = nclose + 1
					continue

			# convert bold into markdown bold
			if inner == 'strong' or inner == 'b' or inner == 'bold':
				if (nclose + 1) < textLen and htmlText[nclose + 1] == ' ':
					cline += ' *'
					idx = nclose + 2
				else:
					cline += "*"
					idx = nclose + 1
				continue
			if inner == '/strong' or inner == '/b' or inner == '/bold':
				if (
					len(cline.strip()) == 0 and len(self.text) > 0
					and self.text[-1] != '<hr />'
				):
					self.text[-1] += '*'
				elif cline.endswith(' '):
					cline = cline[:-1] + '* '
				else:
					cline += '*'
				idx = nclose + 1
				continue

			# convert italics into markdown italics
			if inner == 'em' or inner == 'i':
				if (nclose + 1) < textLen and htmlText[nclose + 1] == ' ':
					cline += ' _'
					idx = nclose + 2
				else:
					cline += '_'
					idx = nclose + 1
				continue
			if inner == '/em' or inner == '/i':
				if (
					len(cline.strip()) == 0 and len(self.text) > 0
					and self.text[-1] != '<hr />'
				):
					self.text[-1] += '_'
				elif cline.endswith(' '):
					cline = cline[:-1] + '_ '
				else:
					cline += '_'
				if len(cline.strip('_ \t\r\n')) == 0:
					cline = ''
				idx = nclose + 1
				continue

			# strikethrough
			if inner == 's' or inner == '/s':
				cline += '-'
				idx = nclose + 1
				continue

			# unable to categorize tag, dump debugging info
			raise Exception(
				'unable to process tag "{}":\n{}\n{!r}'.format(
					inner, htmlText[idx - 90:nclose + 90], inner.encode('utf-8')
				)
			)

		self.__addLine(cline)

		while len(self.text) > 0 and self.text[-1] in ['< Prev', 'Next >']:
			self.text = self.text[:-1]


class ChapterView:
	def __init__(
		self,
		chapter: FicChapter,
		header: bool = True,
		markdown: bool = True,
		footer: bool = True
	):
		self.chapter = chapter

		fic = chapter.getFic()
		extraTitle = ''.join([s[0] for s in (fic.title or '').split()]).lower()
		# FIXME this handles symbols badly like "Foo (complete)"
		#util.logMessage(f"using {extraTitle} as extraTitle in ChapterView")

		content = self.chapter.cachedContent()
		if content is None:
			raise Exception('missing content? FIXME')
		contentView = HtmlView(
			content, markdown=markdown, extraTitles=[extraTitle, f"-{extraTitle}-"]
		)
		self.totalWords = sum([len(l.split()) for l in contentView.text])

		self.text: List[Union[str, List[str]]] = []

		if header == True:
			descriptionView = HtmlView(fic.description or '{missing description}')
			self.text += [
				['', '"{}"'.format(fic.title), ''],
				['', 'by {}'.format(fic.getAuthorName()), ''],
				[
					'chapter {}'.format(chapter.chapterId),
					'words: {}'.format(util.formatNumber(self.totalWords))
				]
			]
			if chapter.chapterId >= 1:
				self.text += descriptionView.text
			if chapter.title is not None and len(chapter.title) > 0:
				self.text += [
					['', 'Chapter {}: {}'.format(chapter.chapterId, chapter.title), '']
				]
			if len(contentView.text) > 0 and contentView.text[0] != '<hr />':
				self.text += ['<hr />']

		self.headerLength = len(self.text)

		self.text += contentView.text
		if footer == True:
			if len(contentView.text) > 0 and contentView.text[-1] != '<hr />':
				self.text += ['<hr />']
			if chapter.title is not None and len(chapter.title) > 0:
				self.text += [
					['', 'Chapter {}: {}'.format(chapter.chapterId, chapter.title), '']
				]
			self.text += [
				[
					'chapter {}'.format(chapter.chapterId),
					'words: {}'.format(util.formatNumber(self.totalWords))
				],
				['"{}"'.format(fic.title), 'by {}'.format(fic.getAuthorName())],
			]

		self.cumulativeLength = [0] * len(self.text)
		cumLen = 0
		for idx in range(len(self.text)):
			self.cumulativeLength[idx] = cumLen
			cumLen += len(self.text[idx])

		self.totalLength = cumLen

		self.preWrap = ' ' * 1
		self.postWrap = ''

		self.wtext: Dict[int, List[str]] = {}
		self.width: int = -1

		self.totalWrappedLines: int = -1
		self.cumulativeTotalWrappedLines: List[int] = []
		self.wrap(80)

	def wrap(self, width: int) -> None:
		if width == self.width:
			return
		self.width = width
		self.wtext = {}

		for idx in range(len(self.text)):
			self.__wrapLine(idx)
		self.totalWrappedLines = sum([len(self.wtext[i]) for i in self.wtext])
		self.cumulativeTotalWrappedLines = [0] * (len(self.text) + 1)
		for i in range(len(self.text)):
			subTotal = self.cumulativeTotalWrappedLines[i] + len(self.wtext[i])
			self.cumulativeTotalWrappedLines[i + 1] = subTotal

	def getLine(self, idx: int) -> List[str]:
		# TODO: should we handle this here?
		if self.text[idx] == '<hr />':
			return ['=' * (self.width)]

		if idx not in self.wtext:
			self.__wrapLine(idx)
		return self.wtext[idx]

	def __wrapLine(self, idx: int) -> None:
		line = self.text[idx]
		if isinstance(line, list):
			# TODO: equiPad should probably handle this
			self.wtext[idx] = util.wrapText(
				util.equiPad(line, self.width), self.width
			)
			return
		self.wtext[idx] = util.wrapText(
			self.preWrap + line + self.postWrap, self.width
		)


class Cursor:
	def __init__(self, cview: ChapterView):
		self.cview = cview
		self.chapter = self.cview.chapter
		userChapter = self.chapter.getUserFicChapter()
		self.line: int = userChapter.line or 0
		self.subLine: int = userChapter.subLine or 0

		# make sure the target line is still valid
		self.line = max(0, min(self.line, len(self.cview.text) - 1))

		self.maxSubLine: int = 0
		self.__calcMaxSubLine()

		# make sure we're focusing on a valid line (TODO)
		self.subLine = max(0, min(self.subLine, self.maxSubLine))

	def __calcMaxSubLine(self) -> None:
		cline = self.cview.getLine(self.line)
		self.maxSubLine = len(cline)

	def wrap(self, width: int) -> None:
		# may only be a vertical resize...
		if self.cview.width == width:
			return

		self.cview.wrap(width)
		self.__calcMaxSubLine()
		# make sure we're focusing on the same line (TODO)
		self.subLine = max(0, min(self.subLine, self.maxSubLine - 1))

	# movement returns true if cursor actually moved
	def down(self) -> bool:
		self.subLine += 1

		# we went down a sub line but stayed in the same line
		if self.subLine < self.maxSubLine:
			return True

		# we're at the last line and cannot move
		if self.line >= len(self.cview.text) - 1:
			self.subLine = self.maxSubLine - 1
			return False

		# we went down to the top of the next line
		self.line += 1
		self.__calcMaxSubLine()
		self.subLine = 0
		return True

	def up(self) -> bool:
		self.subLine -= 1

		# we went up a sub line but stayed in the same line
		if self.subLine >= 0:
			return True

		# we're at the first line and cannot move up
		if self.line <= 0:
			self.subLine = 0
			return False

		# we went up to the bottom of the previous line
		self.line -= 1
		self.__calcMaxSubLine()
		self.subLine = self.maxSubLine - 1
		return True

	def beginning(self) -> bool:
		self.line = 0
		self.__calcMaxSubLine()
		self.subLine = 0
		return True

	def end(self) -> bool:
		self.line = len(self.cview.text) - 1
		self.__calcMaxSubLine()
		self.subLine = self.maxSubLine - 1
		return True

	def pageUp(self) -> bool:
		if self.line == 0:
			return False
		self.line -= 1
		self.subLine = 0
		self.__calcMaxSubLine()
		return True

	def pageDown(self) -> bool:
		if self.line >= len(self.cview.text) - 1:
			return False
		self.line += 1
		self.subLine = 0
		self.__calcMaxSubLine()
		return True


class Story:
	def __init__(self, fic: Fic):
		self.fic = fic
		self.storyId = fic.localId
		self.chapters: Dict[int, ChapterView] = {}
		self.cursors: Dict[int, Cursor] = {}

	def __ensureChapter(self, chapterId: int) -> None:
		if chapterId in self.chapters:
			return
		self.chapters[chapterId] = ChapterView(self.fic.chapter(chapterId))

	def __ensureCursor(self, chapterId: int) -> None:
		if chapterId in self.cursors:
			return
		self.__ensureChapter(chapterId)
		self.cursors[chapterId] = Cursor(self.chapters[chapterId])

	def getChapter(self, chapterId: int) -> Tuple[ChapterView, Cursor]:
		self.__ensureChapter(chapterId)
		self.__ensureCursor(chapterId)
		chap, curs = self.chapters[chapterId], self.cursors[chapterId]
		if chapterId > 1:
			curs.line = max(curs.line, chap.headerLength - 1, 0)

		return self.chapters[chapterId], self.cursors[chapterId]


# TODO: widget type?
class StoryView(Widget):
	def __init__(self, parent: 'Hermes', fic: Fic):
		self.parent = parent
		self.zOrder = 1

		self.fic = fic
		self.storyId = self.fic.localId

		self.story = Story(self.fic)
		userFic = self.fic.getUserFic()
		self.chapterId = max(userFic.lastChapterViewed or 1, 1)
		self.cview, self.cursor = self.story.getChapter(self.chapterId)
		self.cursorNeedsSaved = False
		self.chapter = self.fic.chapter(self.chapterId)
		self.__touchChapter()

		self.width, self.height = 0, 0

		self.minViewed = -1
		self.maxViewed = -1

		self.highlightCurrentLine = True
		self.currentLineColorOptions = [4, 1, 2, 3, 5, 6]
		self.currentLineColorIdx = 0
		self.currentLineColor = (
			self.currentLineColorOptions[self.currentLineColorIdx]
		)
		self.currentLineAttr = 1

		self.targetWidth = 80
		self.maxWidth: Optional[int] = self.targetWidth
		self.defaultLeftMargin = 1
		self.leftMargin = 1
		self.leftOverhang = 2
		self.rightOverhang = 2

		self.lineMag = util.getNumberLength(len(self.cview.text))
		assert (self.fic.chapterCount is not None)
		self.chapMag = util.getNumberLength(self.fic.chapterCount)

		self.minWidth = 12
		self.minHeight = 3

		self.invertCursor = False

	# return true if need repaint
	def handleKey(self, key: int) -> bool:
		if key == ord('/'):
			return True

		if key == ord('q'):
			self.__saveCursor()
			self.parent.quit()
			return True

		if key == ord('u'):
			self.fic.checkForUpdates()
			return True

		if key == ord('o') or key == 27:  # escape
			self.__saveCursor()
			self.__touchChapter()
			self.parent.selectFic(None)
			return True

		if key == ord('c'):
			self.currentLineColorIdx += 1
			self.currentLineColorIdx %= len(self.currentLineColorOptions)
			self.currentLineColor = (
				self.currentLineColorOptions[self.currentLineColorIdx]
			)
			return True
		if key == ord('i'):
			self.invertCursor = not self.invertCursor
			return True
		if key == ord('y'):
			self.highlightCurrentLine = not self.highlightCurrentLine
			return True
		if key == ord('a'):
			self.currentLineAttr = (self.currentLineAttr + 1) % 2
			return True

		if key == ord('='):
			if self.maxWidth is None:
				self.maxWidth = self.targetWidth
			else:
				self.maxWidth = None
				self.leftMargin = self.defaultLeftMargin
			self.__rewrap()
			return True

		if key == ord('+'):
			self.targetWidth += 1
		if key == ord('-'):
			self.targetWidth = max(20, self.targetWidth - 1)

		if key == ord('-') or key == ord('+'):
			if self.maxWidth is None:
				return False
			self.maxWidth = self.targetWidth
			self.__rewrap()
			return True

		cursorMoved = False

		if key == curses.KEY_HOME:
			cursorMoved |= self.cursor.beginning()
		if key == curses.KEY_END:
			cursorMoved |= self.cursor.end()

		if key == curses.KEY_PPAGE or key == ord('K'):
			cursorMoved |= self.cursor.pageUp()
		if key == curses.KEY_NPAGE or key == ord('J') or key == ord(' '):
			cursorMoved |= self.cursor.pageDown()

		if key == ord('j') or key == curses.KEY_DOWN:
			cursorMoved |= self.cursor.down()
		if key == ord('k') or key == curses.KEY_UP:
			cursorMoved |= self.cursor.up()

		self.cursorNeedsSaved |= cursorMoved

		if key == ord('s'):
			userChapter = self.cview.chapter.getUserFicChapter()
			userChapter.readStatus = {
				FicStatus.ongoing: FicStatus.abandoned,
				FicStatus.abandoned: FicStatus.complete,
				FicStatus.complete: FicStatus.ongoing,
			}[FicStatus(userChapter.readStatus)]
			userChapter.update()
			return True

		if key == ord('m'):
			self.cview.chapter.getUserFicChapter().markRead()
			userFic = self.fic.getUserFic()
			userFic.updateLastRead(self.chapterId)
			if (
				userFic.lastChapterRead == self.fic.chapterCount
				and userFic.readStatus == FicStatus.ongoing
			):
				userFic.readStatus = FicStatus.complete
			userFic.upsert()

		if (key == ord('h') or key == curses.KEY_LEFT):
			if self.chapterId > 1:
				self.chapterId -= 1
				self.__flipToChapter()
				return True

		if (key == ord('l') or key == ord('m') or key == curses.KEY_RIGHT):
			assert (self.fic.chapterCount is not None)
			if self.chapterId < self.fic.chapterCount:
				self.chapterId += 1
				self.__flipToChapter()
				return True

		if key == ord('m'):
			return True

		return cursorMoved

	def __saveCursor(self) -> None:
		if self.cursorNeedsSaved:
			self.saveCursor()
			self.cursorNeedsSaved = False

	def __flipToChapter(self) -> None:
		self.__saveCursor()

		self.cview, self.cursor = self.story.getChapter(self.chapterId)
		self.lineMag = max(self.lineMag, util.getNumberLength(len(self.cview.text)))
		self.__rewrap()
		self.__touchChapter()

	def __touchChapter(self) -> None:
		self.chapter = self.fic.chapter(self.chapterId)
		self.fic.getUserFic().updateLastViewed(self.chapterId)

	def __rewrap(self) -> None:
		if self.width < self.minWidth:
			return

		overhang = self.leftOverhang + self.rightOverhang

		if self.maxWidth is None:
			self.cursor.wrap(self.width - self.leftMargin - overhang)
			return

		if self.width < self.maxWidth:
			self.leftMargin = 0
			self.cursor.wrap(self.width - overhang)
			return

		extra = self.width - self.maxWidth
		self.leftMargin = int(extra / 2)
		self.cursor.wrap(self.maxWidth - overhang)

	# assume needs repaint after this
	def handleResize(self, maxX: int, maxY: int) -> None:
		self.width, self.height = maxX, maxY
		self.__rewrap()

	# TODO: scr type?
	def repaint(self, stdscr: Any) -> None:
		if self.width < self.minWidth or self.height < self.minHeight:
			return

		rmid = 3  # int(self.height / 3)
		if self.height > 40:
			rmid = int(self.height / 3)
		if self.height > 60:
			rmid = int(self.height / 5)
		mid = rmid - self.cursor.subLine

		# left overhang prefix
		lop = (' ' * self.leftOverhang)
		# current line prefix and suffix
		clp = '>' + (' ' * (self.leftOverhang - 1))
		cls = (' ' * (self.rightOverhang - 1)) + '<'

		# draw down starting from mid
		logicalLine = self.cursor.line
		where = mid
		while where < self.height and logicalLine < len(self.cview.text):
			# draw text going down for current logical line
			lines = self.cview.getLine(logicalLine)
			for i in range(len(lines)):
				if where + i < 0:
					continue
				if where + i >= self.height:
					continue
				try:
					stdscr.addstr(where + i, self.leftMargin, lop + lines[i])
				except:
					util.logMessage(str((where + i, self.leftMargin, lop + lines[i])))
					raise

			# update next screen write position and logical line
			where += len(lines) + 1
			logicalLine += 1

		self.maxViewed = logicalLine

		# draw up starting from almost middish
		logicalLine = self.cursor.line - 1
		where = mid - 2
		while where >= 0 and logicalLine >= 0:
			# draw text going up for current logical line
			lines = self.cview.getLine(logicalLine)
			for i in range(len(lines)):
				if where - i < 0:
					continue
				if where - i >= self.height:
					continue
				stdscr.addstr(where - i, self.leftMargin, lop + lines[-1 - i])

			# update next screen write position and logical line
			where -= len(lines) + 1
			logicalLine -= 1

		self.minViewed = logicalLine + 1

		# draw current line with special formatting
		if self.highlightCurrentLine == True:
			lines = self.cview.getLine(self.cursor.line)

			attr = curses.color_pair(self.currentLineColor)
			attr |= curses.A_BOLD
			if self.invertCursor:
				attr |= curses.A_REVERSE
			else:
				if self.currentLineAttr == 0:
					pass
				else:
					attr |= curses.A_UNDERLINE
			stdscr.addstr(
				rmid, self.leftMargin, clp + lines[self.cursor.subLine] + cls, attr
			)

		# repaint ruler
		ruler = self.getRuler()
		try:
			stdscr.addstr(self.height - 1, 0, ruler, curses.color_pair(0))
		except curses.error as e:
			pass

	def saveCursor(self) -> None:
		userChapter = self.chapter.getUserFicChapter()
		userChapter.line = self.cursor.line
		userChapter.subLine = self.cursor.subLine
		userChapter.savePosition()

	def getRuler(self) -> str:
		totalLines = len(self.cview.text)
		perc = self.maxViewed * 100.0 / totalLines

		status = {
			FicStatus.complete: '(R)',
			FicStatus.abandoned: '[A]',
			FicStatus.ongoing: ''
		}

		assert (self.fic.chapterCount is not None)
		leftParts = [
			# chapter index
			'({: >{}d}/{:d})'.format(
				self.chapterId, self.chapMag, self.fic.chapterCount
			),
			# chapter status
			status[FicStatus(self.chapter.getUserFicChapter().readStatus)],
			# title
			'"{}"'.format(self.fic.title),
			# chapter title
			self.cview.chapter.title or '',
		]
		lRuler = ' '.join(leftParts)

		cumLen = self.cview.cumulativeLength[self.cursor.line]
		curText = self.cview.getLine(self.cursor.line)
		curLen = cumLen + sum([len(l) for l in curText[:self.cursor.subLine]])
		perc = 100.0 * curLen / self.cview.totalLength

		rightParts = [
			'C' if self.fic.ficStatus == FicStatus.complete else 'I',
			'~{}/{}'.format(
				1 + self.cursor.subLine
				+ self.cview.cumulativeTotalWrappedLines[self.cursor.line],
				self.cview.totalWrappedLines
			),
			# local paragraph and percentage
			'{: >{}d}/{: >{}d}'.format(
				self.cursor.line + 1, self.lineMag, totalLines, self.lineMag
			),
			'{:>3d}%'.format(int(perc))
		]
		if self.maxWidth is not None:
			if self.width >= self.maxWidth:
				rightParts = ['F({})'.format(self.maxWidth)] + rightParts
			else:
				rightParts = ['F[{}]'.format(self.width)] + rightParts

		rRuler = ' '.join(rightParts)

		if len(rRuler) >= self.width:
			return rRuler[0:self.width]

		rlen = len(lRuler + '  ' + rRuler)
		if rlen >= self.width:
			# too long, abbreviate left parts
			lRuler = lRuler[:self.width - len(rRuler) - 1]
		else:
			# not long enough, add in padding
			rRuler = '{:>{}}'.format(rRuler, self.width - len(lRuler) - 1)

		return lRuler + ' ' + rRuler
