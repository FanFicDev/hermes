import os
import re
import math
import random
import datetime
import dateutil.parser
import time
import struct
import zlib
from typing import List, Optional, Union
from schema import OilTimestamp

defaultLogFile = 'hermes.log'
defaultLogDir = './'
rippleCharset = 'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz'
urlIdCharset = 'abcdefghijklmnopqrstuvwxyz23456789'


def unslurp(text: str, fname: str, path: str = defaultLogDir) -> None:
	if not os.path.isdir(path):
		os.makedirs(path)
	fname = os.path.join(path, fname)
	with open(fname, 'w') as f:
		f.write(text)


def getNumberLength(num: int) -> int:
	return int(math.ceil(math.log(num) / math.log(10)))


def formatNumber(num: int) -> str:
	b = '{}'.format(num)
	b = '{:>{}}'.format(b, int((len(b) + 2) / 3) * 3)
	n = ''
	for i in range(int(len(b) / 3)):
		n += b[i * 3:(i + 1) * 3] + ','
	return n[:-1].lstrip()


def urlTitle(title: str) -> str:
	ut = ''
	for char in title:
		if char.isalnum():
			ut += char
		elif len(ut) == 0 or ut[-1] != '-':
			ut += '-'
	return ut.rstrip('-')


def randomString(length: int = 2, charset: Optional[str] = None) -> str:
	charset = rippleCharset if charset is None else charset
	res = ''
	for i in range(length):
		res += random.choice(charset)
	return res


def subsequenceMatch(seq: str, needle: str) -> bool:
	nl, sl = len(needle), len(seq)
	if nl > sl:
		return False
	if nl == sl:
		return needle == seq
	if nl == 0:
		return True
	if nl == 1:
		return seq.find(needle) != -1
	nextStart = seq.find(needle[0])
	if nextStart == -1:
		return False
	return subsequenceMatch(seq[nextStart + 1:], needle[1:])


def dtToUnix(dt: datetime.datetime) -> int:
	return int(dt.strftime('%s'))


_writtenMonths = [
	# full
	'January',
	'February',
	'March',
	'April',
	'May',
	'June',
	'July',
	'August',
	'September',
	'October',
	'November',
	'December',
	# abbreviated
	'Jan',
	'Feb',
	'Mar',
	'Apr',
	'May',
	'Jun',
	'Jul',
	'Aug',
	'Sep',
	'Oct',
	'Nov',
	'Dec'
]


def isWrittenDate(val: str) -> bool:
	for wm in _writtenMonths:
		if val.find(wm) >= 0:
			return True
	return False


def parseDateAsUnix(
	updated: Union[OilTimestamp, str, int],
	fetched: Union[OilTimestamp, int],
	defaultYear: Optional[int] = None
) -> int:
	if isinstance(updated, OilTimestamp):
		return updated.toUTS()
	if isinstance(fetched, OilTimestamp):
		fetched = fetched.toUTS()

	currentYear = datetime.datetime.now().year
	if defaultYear is not None:
		currentYear = defaultYear

	if isinstance(updated, int):
		return updated
	if isinstance(updated, str):
		updated = updated.strip()

	if re.match('^\d+$', updated):
		return int(updated)

	if updated.endswith('ago'):
		updated = updated[:-len('ago')]
	updated = updated.strip()

	if re.match('^\d+m$', updated):
		return fetched - (60 * int(updated[:-1]))
	if re.match('^\d+h$', updated):
		return fetched - (60 * 60 * int(updated[:-1]))
	if re.match('^just', updated):
		return fetched

	slashedParts = updated.split('/')
	if len(slashedParts) == 2:
		fdate = ('{}/{}/{}'.format(currentYear, slashedParts[0], slashedParts[1]))
		dt = (dateutil.parser.parse(fdate))
		uts = dtToUnix(dt)
		return uts
	if len(slashedParts) == 3:
		dt = dateutil.parser.parse(updated)
		uts = dtToUnix(dt)
		return uts

	dashedParts = updated.split('-')
	if len(dashedParts) == 3:
		dt = dateutil.parser.parse(updated)
		uts = dtToUnix(dt)
		return uts

	dottedParts = updated.split('.')
	if (
		len(dottedParts) == 3 and dottedParts[0].isnumeric()
		and dottedParts[1].isnumeric() and dottedParts[2].isnumeric()
	):
		dt = dateutil.parser.parse(updated)
		uts = dtToUnix(dt)
		return uts

	if isWrittenDate(updated):
		dt = dateutil.parser.parse(updated)
		uts = dtToUnix(dt)
		return uts

	logMessage('error parsing date: {}'.format(updated))
	raise Exception('error parsing date: {}'.format(updated))


def logMessage(
	msg: str, fname: Optional[str] = None, logDir: Optional[str] = None
) -> None:
	if fname is None:
		fname = defaultLogFile
	if logDir is None:
		logDir = defaultLogDir
	if not msg.endswith('\n'):
		msg += '\n'
	lname = os.path.join(logDir, fname)
	with open(lname, 'a+') as f:
		f.write(str(int(time.time())) + '|' + msg)
	# TODO this is a hacky workaround for shared log files
	try:
		os.chmod(lname, 0o666)  # rw-rw-rw-
	except:
		pass


# generic word wrapping algorithm
# TODO should we be using the textwrap module instead? >_>
def wrapText(text: str, width: int) -> List[str]:
	if len(text) == 0:
		return [' ' * width]

	lines: List[str] = []
	while len(text) > width:
		# find nearest space to break on
		if len(lines) > 0:
			text = text.strip()
		col = text.rfind(' ', 0, width - 1)  # reserve space for hyphenated words
		col = max(col, text.rfind('-', 0, width - 1))

		# if it's the first line and we find the indent, don't count it
		# TODO: other size indents
		if len(lines) == 0 and col == 0:
			col = -1

		# ran off start => very long word, hyphenate
		if col == -1:
			col = width - 1
			lines += [text[0:col] + '-']
			text = text[col:]
			continue

		# append up to word break into lines
		if col < len(text) and text[col] == '-':
			lines += ['{line:{width}}'.format(line=text[0:col + 1], width=width)]
		else:
			lines += ['{line:{width}}'.format(line=text[0:col], width=width)]

		# remove processed text sans space
		text = text[col + 1:]

	if len(lines) > 0:
		text = text.strip()

	# if there's anything left, it's a line by itself
	if len(text) > 0:
		lines += ['{line:{width}}'.format(line=text, width=width)]

	return lines


spaceSqeeezeRe = None
ellipseSqueezeRe = None
ellipseSpaceRe = None


# convert unicode to ascii for display
def filterUnicode(line: str) -> str:
	global spaceSqeeezeRe, ellipseSqueezeRe, ellipseSpaceRe
	if spaceSqeeezeRe is None:
		spaceSqeeezeRe = re.compile('\s{2,}')
	if ellipseSqueezeRe is None:
		ellipseSqueezeRe = re.compile('(…\s*){2,}')
	if ellipseSpaceRe is None:
		punctuation = '"”?\\.\'\\)_*'
		ellipseSpaceRe = re.compile('…([^ {}])'.format(punctuation))

	# remove some unicode characters
	# ['“', '”'] ['‘', '’'] "…"
	for d in ['–', '—', '-', '­', '―']:
		line = line.replace(d, '-')
	for rm in ['■']:
		line = line.replace(rm, '')
	for apo in ['ʼ', 'ʻ']:
		line = line.replace(apo, "'")
	for dq in ['❝', '❞']:
		line = line.replace(dq, '"')

	# move bold/italic past dots for ellipses squeeze
	#line = re.sub('([_*]+)(\.+)', '\\2\\1')

	# convert ellipses to unicode ellipses
	line = line.replace('...', '…')
	line = line.replace('. . .', '…')

	# squeeze extra ellipses
	line = ellipseSqueezeRe.sub('…', line)

	# remove extra space before punctuation
	line = line.replace(' …', '…')
	line = line.replace(' ,', ',')

	# squeeze strings of repeat spaces
	line = spaceSqeeezeRe.sub(' ', line)

	# make sure ellipses are followed by a space or punctuation
	line = ellipseSpaceRe.sub('… \\1', line)

	return line


def filterEmptyTags(line: str) -> str:
	# remove empty open/close italics and bolds
	line = line.replace('_ _', ' ')
	line = line.replace('__', '')
	line = line.replace('* *', ' ')
	line = line.replace('**', '')
	line = line.replace('*"*', '"')

	return line


# layout a list of strings so each piece is equidistant from the others
def equiPad(strs: List[str], width: int) -> str:
	totalWidth = sum([len(s) for s in strs])
	if totalWidth >= width:
		return ''.join(strs)
	if len(strs) == 1:
		return '{:<{}}'.format(strs[0], width)
	# TODO: when not divisible...
	padded = (' ' * int((width - totalWidth) / (len(strs) - 1))).join(strs)
	return '{:{}}'.format(padded, width)  # ensure right length for non-divisble


def cleanChapterTitle(title: str, cid: int) -> str:
	title = title.strip()
	prefixes = [
		'{}-'.format(cid),
		'{}.'.format(cid),
		'chapter {}'.format(cid),
		'chapter {}'.format(cid + 1),
		'chapter {}'.format(cid - 1),
		':',
		'-',
	]
	foundAny = True
	while foundAny:
		foundAny = False
		for pref in prefixes:
			if title.lower().startswith(pref):
				foundAny = True
				title = title[len(pref):].strip()
	return title


def compress(s: bytes) -> bytes:
	return len(s).to_bytes(4, byteorder='big') + zlib.compress(s, level=9)


def decompress(b: bytes) -> bytes:
	elen = int.from_bytes(b[:4], byteorder='big')
	res = zlib.decompress(b[4:])
	if len(res) != elen:
		raise Exception(f'expected {elen} but got {len(res)} bytes')
	return res


def decodeCloudFlareEmail(email: str) -> str:
	octets = [int(email[i:i + 2], 16) for i in range(0, len(email), 2)]
	key, ebytes = octets[0], octets[1:]
	return ''.join([chr(o ^ key) for o in ebytes])
