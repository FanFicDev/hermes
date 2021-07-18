#!/usr/bin/env python3
import os
import sys
import json
import time
from store import Fic, FicChapter, Fandom, Character, Genre, Tag, Status
from htypes import FicType
import util
import lite
import adapter


# return dependency order of DAG represented by obj
def walk(obj):
	rev = {}
	fforward = {}
	for f in obj:
		if obj[f] is not None:
			rev[obj[f]] = f
		fforward[f] = obj[f]
		if obj[f] not in fforward:
			fforward[obj[f]] = None

	order = {}
	levels = {}
	for f in fforward:
		if fforward[f] is not None:
			continue

		order[f] = 0
		n = f
		while n in rev:
			if rev[n] in order:
				raise Exception('not DAG')
			order[rev[n]] = order[n] + 1
			if order[n] not in levels:
				levels[order[n]] = []
			levels[order[n]] += [rev[n]]
			n = rev[n]

	levels[len(levels)] = [f for f in obj if obj[f] is None]

	return levels


# deflate and inflate take objects and renames fields.
# for deflate, if defaults is set any member matching the default is deleted
# for deflate, all None members are deleted
# for inflate, all fields are set to their corresponding default (if any)
def renameFields(obj, rename):
	levels = walk(rename)
	for level in range(len(levels)):
		for f in levels[level]:
			v = obj.pop(f, None)
			if rename[f] is not None:
				obj[rename[f]] = v
	return obj


def deflateObject(obj, rename, defaults=None):
	obj = renameFields(obj, rename)
	if defaults is not None:
		for f in defaults:
			if obj[f] == defaults[f]:
				obj.pop(f, None)
	emptyFields = [f for f in obj if obj[f] is None]
	for f in emptyFields:
		obj.pop(f, None)
	return obj


def inflateObject(obj, rename, defaults=None):
	obj = renameFields(obj, rename)
	if defaults is not None:
		for f in defaults:
			obj[f] = defaults[f]
	return obj


def importDB(data):
	for fandom in data['fandoms']:
		Fandom.define(fandom)
	for character in data['characters']:
		Character.define(Fandom.define(character['fandom']), character['name'])
	for genre in data['genres']:
		Genre.define(genre)
	for tag in data['tags']:
		Tag.define(tag)

	ficKeys = [key for key in data['fics']]
	ficKeys.sort()
	for key in ficKeys:
		here = data['fics'][key]
		importFic(here)


ficImportRename = {
	'chapters': None,
	'genres': None,
	'tags': None,
	'fandoms': None,
	'characters': None,
}


def importFic(fdata):
	global ficImportRename
	ofic = inflateObject(fdata.copy(), ficImportRename)

	fic = Fic.new()
	for field in ofic:
		print('setting "{}" to "{}"'.format(field, ofic[field]))
		fic.__dict__[field] = ofic[field]

	fic.published = util.parseDateAsUnix(fic.published, int(time.time()))
	fic.updated = util.parseDateAsUnix(fic.updated, int(time.time()))
	print('setting "{}" to "{}"'.format('published', fic.published))
	print('setting "{}" to "{}"'.format('updated', fic.updated))

	print('adding "{}" ({}/{})'.format(fic.title, fic.type, fic.localId))

	fic.insert()

	for fandom in fdata['fandoms']:
		print('  adding fandom "{}"'.format(fandom))
		fic.add(Fandom.define(fandom))
	for character in fdata['characters']:
		print(
			'  adding character "{}" from fandom "{}"'.format(
				character['name'], character['fandom']
			)
		)
		fic.add(
			Character.define(Fandom.define(character['fandom']), character['name'])
		)
	for genre in fdata['genres']:
		print('  adding genre "{}"'.format(genre))
		fic.add(Genre.define(genre))
	for tag in fdata['tags']:
		print('  adding tag "{}"'.format(tag))
		fic.add(Tag.define(tag))

	cids = [int(cid) for cid in fdata['chapters']]
	cids.sort()
	for cid in cids:
		print('  adding chapter {}'.format(cid))
		ochap = fdata['chapters'][str(cid)]
		chapter = FicChapter.new()
		chapter.fic = fic
		chapter.ficId = fic.id
		chapter.chapterId = cid
		for field in ochap:
			chapter.__dict__[field] = ochap[field]
		contentPath = './content/{}/{}/{}/content.html'.format(
			fic.type, fic.localId, cid
		)
		if os.path.isfile(contentPath):
			html = None
			with open(contentPath, 'r') as f:
				html = f.read()
			print('    has content: {}'.format(len(html)))
			chapter.setHtml(html)
		chapter.insert()


def dumpDB():
	data = {}

	fandomMap = {f.id: f for f in Fandom.select()}
	characterMap = {c.id: c for c in Character.select()}
	genreMap = {g.id: g for g in Genre.select()}
	tagMap = {t.id: t for t in Tag.select()}

	data['fandoms'] = [fandomMap[k].name for k in fandomMap]
	data['characters'] = [
		{
			'name': characterMap[k].name,
			'fandom': fandomMap[characterMap[k].fandom_id].name
		} for k in characterMap
	]
	data['genres'] = [genreMap[k].name for k in genreMap]
	data['tags'] = [tagMap[k].name for k in tagMap]

	data['fics'] = {}

	frename = {'id': None, 'chapters': 'chapterCount'}
	crename = {
		'id': None,
		'ficId': None,
		'cid': None,
		'raw': None,
		'fic': None,
		'lastLine': None
	}
	cdefaults = {
		'line': 0,
		'subLine': 0,
		'notes': None,
		'status': Status.ongoing,
		'fetched': None,
		'url': None
	}

	fics = Fic.select()
	for fic in fics:
		k = '{}/{}'.format(fic.type, fic.localId)
		o = fic.__dict__.copy()
		o = deflateObject(o, frename)

		o['fandoms'] = [f.name for f in fic.fandoms()]
		o['characters'] = [
			{
				'name': c.name,
				'fandom': fandomMap[c.fandom_id].name
			} for c in fic.characters()
		]
		o['tags'] = [t.name for t in fic.tags()]
		o['genres'] = [g.name for g in fic.genres()]

		co = {}
		ficChapters = FicChapter.select({'ficId': fic.id})
		for chapter in ficChapters:
			here = chapter.__dict__.copy()
			ffNetUrl = 'https://www.fanfiction.net/s/{}/{}/{}'.format(
				fic.localId, chapter.chapterId, util.urlTitle(fic.title)
			)
			cdefaults['url'] = ffNetUrl
			cdefaults['lastModified'] = here['fetched']
			here = deflateObject(here, crename, cdefaults)

			co[chapter.chapterId] = here
			if chapter.raw is None:
				continue

			contentPath = './content/{}/{}/{}/'.format(
				fic.type, fic.localId, chapter.chapterId
			)
			if not os.path.isdir(contentPath):
				os.makedirs(contentPath)
			with open(contentPath + 'content.html', 'w') as f:
				f.write(chapter.content())

		o['chapters'] = co

		data['fics'][k] = o

	return data


def populateKMTemplate(url, chapterUrls):
	kmRename = {'id': None}
	kmDefaults = {
		'fandoms': [],
		'characters': [],
		'tags': [],
		'genres': [],
		'authorUrl': 'dummy',
		'author': 'dummy',
		'authorId': 1,
		'ageRating': 'M',
		'language': 'English',
		'favorites': 0,
		'follows': 0,
		'reviews': 0,
		'url': url,
		'lastUrl': url,
		'type': FicType.dummy,
		'lid': -1,
		'ficStatus': Status.complete,
		'wordCount': -1,
		'description': 'FILL IN MY DESCRIPTION',
		'title': 'FILL IN MY TITLE',
		'published': 'FILL IN MY PUBLISHED DATE',
		'updated': 'FILL IN MY UPDATED DATE',
		'added': int(time.time()),
		'fetched': int(time.time())
	}

	fic = Fic.new().__dict__
	fic = inflateObject(fic, kmRename, kmDefaults)

	fic['chapters'] = {}
	fic['chapterCount'] = len(chapterUrls)

	for cid in range(1, len(chapterUrls) + 1):
		fic['chapters'][cid] = {
			'lastModified': int(time.time()),
			'status': Status.ongoing,
			'fetched': int(time.time()),
			'url': chapterUrls[cid - 1],
		}

	return fic


def populateFATemplate(author, storyAbbreviation, chapterCount):
	url = 'http://www.fictionalley.org/authors/{}/{}.html'.format(
		author, storyAbbreviation
	)
	lastUrl = url[:-5] + '01.html'
	if chapterCount == 1:
		lastUrl = url[:-5] + '01a.html'
	lid = 1

	faRename = {'id': None}
	faDefaults = {
		'fandoms': ['Harry Potter'],
		'characters': [],
		'tags': [],
		'genres': [],
		'authorUrl': 'http://www.fictionalley.org/authors/{}'.format(author),
		'author': author,
		'authorId': author,
		'ageRating': 'PG',
		'language': 'English',
		'favorites': 0,
		'follows': 0,
		'reviews': 0,
		'url': url,
		'lastUrl': lastUrl,
		'type': FicType.fictionalley,
		'lid': lid,
		'ficStatus': Status.complete,
		'wordCount': -1,
		'description': 'FILL IN MY DESCRIPTION',
		'title': 'FILL IN MY TITLE',
		'published': 'FILL IN MY PUBLISHED DATE',
		'updated': 'FILL IN MY UPDATED DATE',
		'added': int(time.time()),
		'fetched': int(time.time())
	}

	fic = Fic.new().__dict__
	fic = inflateObject(fic, faRename, faDefaults)

	fic['chapters'] = {}
	fic['chapterCount'] = chapterCount

	for cid in range(1, chapterCount + 1):
		chapterUrl = url[:-5] + '{:02}.html'.format(cid)
		if chapterCount == 1:
			chapterUrl = url[:-5] + '01a.html'
		fic['chapters'][cid] = {
			'lastModified': int(time.time()),
			'status': Status.ongoing,
			'fetched': int(time.time()),
			'url': chapterUrl
		}
		contentDir = './content/{}/{}/{}'.format(FicType.fictionalley, lid, cid)
		if not os.path.isdir(contentDir):
			os.makedirs(contentDir)

	return fic


def populateManualTemplate(url, chapterUrls, author):
	existingManual = Fic.select({'type': FicType.manual})
	lid = len(existingManual) + 1

	manRename = {'id': None}
	manDefaults = {
		'fandoms': [],
		'characters': [],
		'tags': [],
		'genres': [],
		'authorUrl': url,
		'author': author,
		'authorId': author,
		'ageRating': 'M',
		'language': 'English',
		'favorites': 0,
		'follows': 0,
		'reviews': 0,
		'url': url,
		'lastUrl': url,
		'type': FicType.manual,
		'lid': lid,
		'ficStatus': Status.complete,
		'wordCount': -1,
		'description': 'FILL IN MY DESCRIPTION',
		'title': 'FILL IN MY TITLE',
		'published': 'FILL IN MY PUBLISHED DATE',
		'updated': 'FILL IN MY UPDATED DATE',
		'added': int(time.time()),
		'fetched': int(time.time())
	}

	fic = Fic.new().__dict__
	fic = inflateObject(fic, manRename, manDefaults)

	fic['chapters'] = {}
	fic['chapterCount'] = len(chapterUrls)

	for cid in range(1, len(chapterUrls) + 1):
		fic['chapters'][cid] = {
			'lastModified': int(time.time()),
			'status': Status.ongoing,
			'fetched': int(time.time()),
			'url': chapterUrls[cid - 1],
		}

	return fic


if __name__ == '__main__':
	adapter.registerAdapters()

	cmds = ['export', 'import', 'template', 'single']
	cmd = None
	if len(sys.argv) > 1:
		for c in cmds:
			if sys.argv[1] == c:
				cmd = c
				break

	if len(sys.argv) != 3 or cmd is None:
		for i in range(len(cmds)):
			print('usage: jdb {} <file>'.format(cmds[i]))
		sys.exit(0)

	lite.autocommit = False

	if sys.argv[1] == 'import':
		with open(sys.argv[2], 'r') as f:
			data = json.load(f)
			importDB(data)
			lite.shutdown()

	if sys.argv[1] == 'export':
		data = dumpDB()
		with open(sys.argv[2], 'w') as f:
			f.write(json.dumps(data))

	if sys.argv[1] == 'template':
		url = 'http://home.exetel.com.au/jaina/Unforgivable/Unforgivable.html'
		churl = 'http://home.exetel.com.au/jaina/Unforgivable/Unforgivable{}.html'
		chapterUrls = []
		for i in range(1, 46):
			chapterUrls += [churl.format(str(i).zfill(2))]

		#fic = populateFATemplate('delicfcd', 'SITBB', 1)

		#url = 'http://www.fanfiction.net/s/4641003/1/'
		#chapterUrls = []
		#chapterCount = 17
		#for i in range(1, chapterCount + 1):
		#chapterUrls += [url + str(i)]
		#with open('./worm/olinks', 'r') as f:
		#	chapterUrls = f.read().split('\n')
		#if len(chapterUrls[-1].strip()) == 0:
		#chapterUrls = chapterUrls[:-1]
		author = 'jaina'
		fic = populateManualTemplate(url, chapterUrls, author)

		with open(sys.argv[2], 'w') as f:
			f.write(json.dumps(fic, sort_keys=True, indent=4) + '\n')

	if sys.argv[1] == 'single':
		with open(sys.argv[2], 'r') as f:
			data = json.load(f)
			importFic(data)
			lite.shutdown()
