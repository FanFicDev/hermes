import time
from typing import Optional

from htypes import FicType, FicId
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter, \
		Fandom, Character
import util
import scrape

from adapter.adapter import Adapter, edumpContent

# [ any of these ], [ map to all of these ]
ao3FandomsMap = [
		[ [ '1989 - Taylor Swift' ], [ '1989 - Taylor Swift' ] ],
		[ [ 'Addams Family - All Media Types' ], [ 'Addams Family' ] ],
		[ [ 'Alphas (TV)' ], [ 'Alphas' ] ],
		[ [ 'Animorphs - Katherine A. Applegate' ], [ 'Animorphs' ] ],
		[ [ 'Anne of Green Gables - L. M. Montgomery' ], [ 'Anne of Green Gables' ] ],
		[ [ 'Ao no Exorcist | Blue Exorcist' ], [ 'Ao no Exorcist' ] ],
		[ [ 'Artemis Fowl - Eoin Colfer' ], [ 'Artemis Fowl' ] ],
		[ [ 'Arthurian Mythology' ], [ 'Arthurian Mythology' ] ],
		[ [ 'A Series of Unfortunate Events - Lemony Snicket' ], [ 'A Series of Unfortunate Events' ] ],
		[ [ 'Astro Boy (2009)' ], [ 'Astro Boy' ] ],
		[ [ 'captain america civil war', 'civil war - Fandom' ], [ 'Avengers' ] ],
		[ [ 'Batman - All Media Types', 'Batman: The Animated Series', 'Batman (Comics)', 'Batman - Fandom' ], [ 'Batman' ] ],
		[ [ 'Beauty and the Beast (2017)' ], [ 'Beauty and the Beast' ] ],
		[ [ 'Bishoujo Senshi Sailor Moon | Pretty Guardian Sailor Moon', 'Sailor Moon - All Media Types' ], [ 'Sailor Moon' ] ],
		[ [ 'Black Panther (2018)' ], [ 'Black Panther' ] ],
		[ [ 'Boruto: Naruto Next Generations' ], [ 'Boruto' ] ],
		[ [ 'British Royalty RPF' ], [ 'British Royalty RPF' ] ],
		[ [ 'Brooklyn Nine-Nine (TV)' ], [ 'Brooklyn Nine-Nine' ] ],
		[ [ 'Buffy the Vampire Slayer', 'Buffy the Vampire Slayer (TV)' ], [ 'Buffy the Vampire Slayer' ] ],
		[ [ 'Buzz Lightyear of Star Command' ], [ 'Buzz Lightyear of Star Command' ] ],
		[ [ 'Cardcaptor Sakura' ], [ 'Cardcaptor Sakura' ] ],
		[ [ 'Cinderella (Fairy Tale)' ], [ 'Cinderella' ] ],
		[ [ 'Coronation Street' ], [ 'Coronation Street' ] ],
		[ [ 'Criminal Minds', 'Criminal Minds (US TV)' ], [ 'Criminal Minds' ] ],
		[ [ 'Criminal Minds/Harry Potter' ], [ 'Criminal Minds', 'Harry Potter' ] ],
		[ [ 'Dangan Ronpa - All Media Types' ], [ 'Danganronpa' ] ],
		[ [ 'Dark-Hunter Series - Sherrilyn Kenyon' ], [ 'Dark-Hunter' ] ],
		[ [ 'Darkwing Duck (Cartoon)' ], [ 'Darkwing Duck' ] ],
		[ [ 'Deadpool (Movieverse)', 'Deadpool - All Media Types' ], [ 'Deadpool' ] ],
		[ [ 'Dead Space' ], [ 'Dead Space' ] ],
		[ [ 'Death in Paradise' ], [ 'Death in Paradise' ] ],
		[ [ 'Digimon Savers | Digimon Data Squad' ], [ 'Digimon Data Squad' ] ],
		[ [ 'Doki Doki Literature Club! (Visual Novel)' ], [ 'Doki Doki Literature Club' ] ],
		[ [ 'Dragonball Z' ], [ 'Dragon Ball Z' ] ],
		[ [ 'Draka Series - S. M. Stirling', 'Draka Series - S.M. Stirling' ], [ 'Draka Series' ] ],
		[ [ 'Drake & Josh' ], [ 'Drake & Josh' ] ],
		[ [ 'Dragon Age (Video Games)' ], [ 'Dragon Age' ] ],
		[ [ 'Dreaming of Sunshine - Silver Queen' ], [ 'Dreaming of Sunshine - Silver Queen' ] ],
		[ [ 'DuckTales (Cartoon 2017)' ], [ 'DuckTales' ] ],
		[ [ 'Elder Scrolls V: Skyrim' ], [ 'Skyrim' ] ],
		[ [ 'Eureka', 'Eureka (TV)' ], [ 'Eureka' ] ],
		[ [ 'Fallout (Video Games)' ], [ 'Fallout' ] ],
		[ [ "Fantastic Four: World's Greatest Heroes", 'Fantastic Four', 'Fantastic Four (Comicverse)' ], [ 'Fantastic Four' ] ],
		[ [ 'Fire Emblem: The Sacred Stones', 'Fire Emblem: Fuuin no Tsurugi | Fire Emblem: Binding Blade', 'Fire Emblem: Kakusei | Fire Emblem: Awakening', 'Fire Emblem: Rekka no Ken | Fire Emblem: Blazing Sword', 'Fire Emblem: If | Fire Emblem: Fates', 'Fire Emblem: Rekka no Ken' ], [ 'Fire Emblem' ] ],
		[ [ "Friendship is Magic - Fandom" ], [ 'My Little Pony: Friendship is Magic' ] ],
		[ [ 'Gilmore Girls' ], [ 'Gilmore Girls' ] ],
		[ [ 'Glee' ], [ 'Glee' ] ],
		[ [ 'Goblin Slayer (Manga)' ], [ 'Goblin Slayer' ] ],
		[ [ 'Hamlet - Shakespeare' ], [ 'Hamlet' ] ],
		[ [ 'Hamilton - Miranda' ], [ 'Hamilton' ] ],
		[ [ 'Hawaii Five-0 (2010)' ], [ 'Hawaii Five-0' ] ],
		[ [ 'Highschool DxD (Anime)' ], [ 'Highschool DxD' ] ],
		[ [ 'Hikaru no Go' ], [ 'Hikaru no Go' ] ],
		[ [ 'His Dark Materials - Philip Pullman' ], [ 'His Dark Materials' ] ],
		[ [ 'Historical RPF' ], [ 'Historical RPF' ] ],
		[ [ 'Honor Harrington Series - David Weber' ], [ 'Honor Harrington' ] ],
		[ [ 'The Hunger Games (Movies)', 'Hunger Games Trilogy - Suzanne Collins', 'Hunger Games Series - All Media Types' ], [ 'The Hunger Games' ] ],
		[ [ 'Into the Woods - Sondheim/Lapine', 'Into the Woods (2014)' ], [ 'Into the Woods' ] ],
		[ [ 'Iron Fist (TV)', 'Iron Fist (Comic)' ], [ 'Iron Fist' ] ],
		[ [ 'Jackie Chan Adventures' ], [ 'Jackie Chan Adventures' ] ],
		[ [ 'Justice League & Justice League Unlimited (Cartoons)', 'Justice League (2017)', 'Justice League' ], [ 'Justice League' ] ],
		[ [ 'Jurassic World (2015)' ], [ 'Jurassic World' ] ],
		[ [ 'Katawa Shoujo' ], [ 'Katawa Shoujo' ] ],
		[ [ 'Kill la Kill (Anime & Manga)' ], [ 'Kill la Kill' ] ],
		[ [ 'The Legend of Zelda: The Ocarina of Time' ], [ 'Legend of Zelda' ] ],
		[ [ 'The Librarian (Movies)' ], [ 'The Librarian' ] ],
		[ [ 'The Librarians (TV 2014)' ], [ 'The Librarian', 'The Librarians' ] ],
		[ [ 'Lizzie Bennet Diaries' ], [ 'Lizzie Bennet Diaries' ] ],
		[ [ 'Luna Varga', '魔獣戦士ルナ・ヴァルガー | Majuu Senshi Luna Varga | Demon Warrior Luna Varga (Anime)' ], [ 'Luna Varga' ] ],
		[ [ 'Magic School Bus' ], [ 'Magic School Bus' ] ],
		[ [ 'Mahou Shoujo Lyrical Nanoha | Magical Girl Lyrical Nanoha' ], [ 'Magical Girl Lyrical Nanoha' ] ],
		[ [ 'Matilda - Roald Dahl' ], [ 'Matilda' ] ],
		[ [ 'Marvel Cinematic Universe', 'Marvel', 'Marvel (Comics)', 'Marvel (Movies)' ], [ 'Marvel' ] ],
		[ [ 'Maximum Ride - James Patterson' ], [ 'Maximum Ride' ] ],
		[ [ 'MCGUIRE Seanan - Works' ], [ 'Seanan McGuire' ] ],
		[ [ "McLeod's Daughters" ], [ "McLeod's Daughters" ] ],
		[ [ 'Memoir - Fandom' ], [ 'Memoir' ] ],
		[ [ 'Minecraft (Video Game)' ], [ 'Minecraft' ] ],
		[ [ 'Miraculous Ladybug' ], [ 'Miraculous Ladybug' ] ],
		[ [ 'my immortal (fanfic)', '(My) Immortal: The Web Series' ], [ 'my immortal' ] ],
		[ [ 'My Little Pony' ], [ 'My Little Pony' ] ],
		[ [ 'Nowhere But Here - Katie McGarry' ], [ 'Nowhere But Here' ] ],
		[ [ '大神 | Okami (Video Games)' ], [ 'Okami' ] ],
		[ [ 'On the Jellicoe Road - Melina Marchetta' ], [ 'On the Jellicoe Road' ] ],
		[ [ 'ワンパンマン | One-Punch Man' ], [ 'One Punch Man' ] ],
		[ [ 'Othello - Shakespeare' ], [ 'Othello' ] ],
		[ [ 'Pact - Fandom' ], [ 'Pact' ] ],
		[ [ 'Paper Towns - John Green' ], [ 'Paper Towns' ] ],
		[ [ 'Pathfinder (Roleplaying Game)' ], [ 'Pathfinder' ] ],
		[ [ 'The Phoenix City Chronicles' ], [ 'Phoenix City Chronicles' ] ],
		[ [ 'PKNA - Paperinik New Adventures' ], [ 'PKNA - Paperinik New Adventures' ] ],
		[ [ 'Percy Jackson and the Olympians & Related Fandoms - All Media Types', 'Percy Jackson and the Olympians - Rick Riordan' ], [ 'Percy Jackson and the Olympians' ] ],
		[ [ 'Pirates of the Caribbean (Movies)' ], [ 'Pirates of the Caribbean' ] ],
		[ [ 'Pocket Monsters: Diamond & Pearl & Platinum | Pokemon Diamond Pearl Platinum Versions', 'Pocket Monsters: Ultra Sun & Ultra Moon | Pokemon Ultra Sun & Ultra Moon Versions', 'Pocket Monsters: Sun & Moon | Pokemon Sun & Moon Versions', 'very minor pokemon', 'pocket monsters | pokemon (anime)', 'pocket monsters | pokemon - all media types', 'Pocket Monsters | Pokemon (Main Video Game Series)', 'Pokemon'], [ 'Pokemon' ] ],
		[ [ 'プリキュア | PreCure | Pretty Cure Series' ], [ 'Pretty Cure' ] ],
		[ [ 'The Punisher (TV 2017)' ], [ 'Punisher' ] ],
		[ [ 'Ranma 1/2' ], [ 'Ranma' ] ],
		[ [ 'RCN Series - David Drake' ], [ 'RCN Series', 'Lt. Leary' ] ],
		[ [ 'RWBY' ], [ 'RWBY' ] ],
		[ [ 'Sanctuary (TV)' ], [ 'Sanctuary' ] ],
		[ [ 'Sense8 (TV)' ], [ 'Sense8' ] ],
		[ [ 'Shingeki no Kyojin | Attack on Titan' ], [ 'Attack on Titan' ] ],
		[ [ 'Shugo Chara!' ], [ 'Shugo Chara!' ] ],
		[ [ 'Sleeping Beauty (Fairy Tale)' ], [ 'Sleeping Beauty' ] ],
		[ [ 'Sly Cooper (Video Games)' ], [ 'Sly Cooper' ] ],
		[ [ 'Schneewittchen | Snow White (Fairy Tale)' ], [ 'Snow White' ] ],
		[ [ 'Starfinder (Roleplaying Game)' ], [ 'Starfinder' ] ],
		[ [ 'Star Trek: The Next Generation', 'Star Trek: Alternate Original Series (Movies)', 'Star Trek (2009)' ], [ 'Star Trek' ] ],
		[ [ 'Star Wars Original Trilogy', 'Star Wars Sequel Trilogy' ], [ 'Star Wars' ] ],
		[ [ 'Stranger Things (TV 2016)' ], [ 'Stranger Things' ] ],
		[ [ 'Suicide Squad (2016)' ], [ 'Suicide Squad' ] ],
		[ [ 'Super Friends' ], [ 'Super Friends' ] ],
		[ [ 'Super Smash Brothers' ], [ 'Super Smash Brothers' ] ],
		[ [ 'Team Fortress 2' ], [ 'Team Fortress 2' ] ],
		[ [ 'Terminator Genisys (2015)' ], [ 'Terminator' ] ],
		[ [ 'Terra Nova (TV)' ], [ 'Terra Nova' ] ],
		[ [ 'The Aquabats! Super Show!' ], [ 'The Aquabats! Super Show!' ] ],
		[ [ 'The Beatles' ], [ 'The Beatles' ] ],
		[ [ 'The Defenders (Comic)' ], [ 'The Defenders' ] ],
		[ [ 'The Heroes of Olympus - Rick Riordan' ], [ 'The Heroes of Olympus' ] ],
		[ [ 'The Hobbit - All Media Types' ], [ 'The Hobbit' ] ],
		[ [ 'The Incredibles (2004)' ], [ 'The Incredibles' ] ],
		[ [ 'The Three Caballeros (1944)' ], [ 'The Three Caballeros' ] ],
		[ [ "The Player's Haven Adventures" ], [ "The Player's Haven Adventures" ] ],
		[ [ 'The Originals (TV)' ], [ 'The Originals' ] ],
		[ [ 'Vampire Diaries (TV)', 'The Vampire Diaries (TV)' ], [ 'Vampire Diaries' ] ],
		[ [ 'Hulk (2003)', 'The Incredible Hulk - All Media Types', 'The Incredible Hulk (2008)' ], [ 'Hulk' ] ],
		[ [ 'Thor (Comics)' ], [ 'Thor' ] ],
		[ [ 'Tomb Raider & Related Fandoms' ], [ 'Tomb Raider' ] ],
		[ [ 'Top wo Nerae 2! Diebuster' ], [ 'GunBuster 2' ] ],
		[ [ 'Total Drama' ], [ 'Total Drama' ] ],
		[ [ 'Toy Story (Movies)' ], [ 'Toy Story' ] ],
		[ [ 'Transformers (Bay Movies)' ], [ 'Transformers' ] ],
		[ [ 'Twig - Wildbow' ], [ 'Twig' ] ],
		[ [ 'The Umbrella Academy (TV)' ], [ 'The Umbrella Academy' ] ],
		[ [ 'Undertale (Video Game)' ], [ 'Undertale' ] ],
		[ [ 'Rockman.EXE | Mega Man Battle Network' ], [ 'Mega Man Battle Network' ] ],
		[ [ 'RoboCop (2014)' ], [ 'RoboCop' ] ],
		[ [ 'Venom (Comics)' ], [ 'Venom' ] ],
		[ [ 'Warehouse 13' ], [ 'Warehouse 13' ] ],
		[ [ 'We Know the Devil (Visual Novel)' ], [ 'We Know the Devil' ] ],
		[ [ 'We Will Rock You - Elton/May/Taylor' ], [ 'We Will Rock You' ] ],
		[ [ 'Winx Club' ], [ 'Winx Club' ] ],
		[ [ 'W.I.T.C.H.' ], [ 'W.I.T.C.H.' ] ],
		[ [ 'Wonder Woman (2017)', 'Wonder Woman - All Media Types' ], [ 'Wonder Woman' ] ],
		[ [ 'Worm (Web Novel)' ], [ 'Worm' ] ],
		[ [ 'Young Justice', 'Young Justice (cartoon)' ], [ 'Young Justice' ] ],
		[ [ 'Yu-Gi-Oh!' ], [ 'Yu-Gi-Oh!' ] ],
		[ [ "Yu-Gi-Oh! 5D's" ], [ "Yu-Gi-Oh! 5D's" ] ],
		[ [ "私がモテないのはどう考えてもお前らが悪い! | Watamote - No Matter How I Look At It It's You Guys' Fault I'm Unpopular!" ], [ 'WataMote' ] ],
		[ [ '逆転裁判 | Gyakuten Saiban | Ace Attorney' ], [ 'Ace Attorney' ] ],
	]

class Ao3Adapter(Adapter):
	def __init__(self) -> None:
		super().__init__(True,
				'https://archiveofourown.org/works/', 'archiveofourown.org',
				FicType.ao3, 'ao3')
		self.collectionUrl = 'https://archiveofourown.org/collections/'

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		mapPrefixes = ['http://www.', 'http://', 'https://www.']
		hasPrefix = True
		while hasPrefix:
			hasPrefix = False
			for pref in mapPrefixes:
				if url.startswith(pref):
					hasPrefix = True
					url = 'https://' + url[len(pref):]

		endsToStrip = [
				'#main', '#work_endnotes', '#bookmark-form',
				'?view_adult=true',
				'?view_full_work=true', '?viewfullwork=true',
				'?show_comments=true',
			]
		for send in endsToStrip:
			if url.endswith(send):
				url = url[:-len(send)]
		if url.find('#') >= 0:
			url = url[:url.find('#')]
		if url.find('?') >= 0:
			url = url[:url.find('?')]

		# TODO: this should probably return a FicId pointing to this chapter and
		# not just this fic in general...
		if url.find('/chapters/') >= 0 and url.find('/works/') < 0:
			meta = scrape.softScrapeWithMeta(url, delay=10)
			if meta is None or meta['raw'] is None or meta['status'] != 200:
				raise Exception('unable to lookup chapter: {}'.format(url))
			from bs4 import BeautifulSoup # type: ignore
			soup = BeautifulSoup(meta['raw'], 'html5lib')
			for a in soup.find_all('a'):
				if a.get_text() == 'Entire Work':
					return self.tryParseUrl(self.baseUrl + a.get('href')[len('/works/'):])
			else:
				raise Exception('unable to lookup chapters entire work: {}'.format(url))

		if url.startswith(self.collectionUrl) and url.find('/works/') != -1:
			url = self.baseUrl + url[url.find('/works/') + len('/works/'):]
		if not url.startswith(self.baseUrl):
			return None

		pieces = url[len(self.baseUrl):].split('/')
		lid = pieces[0]
		if len(lid) < 1 or not lid.isnumeric():
			return None

		ficId = FicId(FicType.ao3, lid)
		fic = Fic.tryLoad(ficId)
		if fic is None:
			return ficId

		if len(pieces) >= 3 and pieces[1] == 'chapters' and pieces[2].isnumeric():
			localChapterId = pieces[2]
			mchaps = FicChapter.select({'ficId': fic.id, 'localChapterId': localChapterId})
			if len(mchaps) == 1:
				ficId.chapterId = mchaps[0].chapterId
				ficId.ambiguous = False

		return ficId

	def create(self, fic: Fic) -> Fic:
		fic.url = self.baseUrl + str(fic.localId)

		# scrape fresh info
		url = fic.url.split('?')[0] + '?view_adult=true'
		data = scrape.scrape(url)

		edumpContent(data['raw'], 'ao3')

		fic = self.parseInfoInto(fic, data['raw'])
		fic.upsert()

		chapter = fic.chapter(1)
		chapter.setHtml(data['raw'])
		chapter.upsert()

		return Fic.lookup((fic.id,))

	def extractContent(self, fic: Fic, html: str) -> str:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html.parser')
		chapters = soup.find(id='chapters')
		if chapters is None:
			edumpContent(html, 'ao3_ec')
			raise Exception('unable to find chapters, e-dumped')
		# delete 'Notes' and 'Chapter Text' headings
		for heading in chapters.find_all('h3', {'class': 'heading'}):
			heading.extract()

		return str(chapters)

	def buildUrl(self, chapter: 'FicChapter') -> str:
		if len(chapter.url.strip()) == 0:
			if chapter.chapterId == 1:
				return self.baseUrl + str(chapter.getFic().localId) + '?view_adult=true'
			raise NotImplementedError()
		return chapter.url

	def getCurrentInfo(self, fic: Fic) -> Fic:
		fic.url = self.baseUrl + str(fic.localId)
		url = fic.url.split('?')[0] + '?view_adult=true'
		# scrape fresh info
		data = scrape.scrape(url)

		return self.parseInfoInto(fic, data['raw'])

	def parseInfoInto(self, fic: Fic, html: str) -> Fic:
		from bs4 import BeautifulSoup
		soup = BeautifulSoup(html, 'html.parser')

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English") # TODO: don't hard code?

		titleHeadings = soup.findAll('h2', {'class': 'title heading'})
		if len(titleHeadings) != 1:
			raise Exception('unable to find ao3 title {}'.format(fic.url))
		fic.title = titleHeadings[0].get_text().strip()

		summaryModules = soup.findAll('div', {'class': 'summary module'})
		if len(summaryModules) != 1:
			prefaceGroups = soup.findAll('div', {'class': 'preface group'})
			if len(prefaceGroups) == 1:
				summaryModules = prefaceGroups[0].findAll('div', \
						{'class': 'summary module'})

		if len(summaryModules) == 1:
			summaryBq = summaryModules[0].find('blockquote')
			fic.description = summaryBq.decode_contents(formatter='html').strip()
		elif fic.description is None:
			fic.description = "{no summary}"
			# raise Exception('unable to find ao3 summary {}'.format(fic.localId))

		fic.ageRating = '<unkown>'

		# TODO: error handling
		cText = ' '.join(soup.find('dd', {'class': 'chapters'}).contents).strip()
		ps = cText.split('/')
		completedChapters = int(ps[0])
		totalChapters = None if ps[1] == '?' else int(ps[1])
		fic.chapterCount = completedChapters

		wText = ' '.join(soup.find('dd', {'class': 'words'}).contents).strip()
		fic.wordCount = int(wText)

		fic.reviewCount = 0

		fic.favoriteCount = 0
		kDefinition = soup.find('dd', {'class': 'kudos'})
		if kDefinition is not None:
			kText = ' '.join(kDefinition.contents).strip()
			fic.favoriteCount = int(kText)

		fic.followCount = 0

		pText = ' '.join(soup.find('dd', {'class': 'published'}).contents).strip()
		publishedUts = util.parseDateAsUnix(pText, fic.fetched)
		fic.published = OilTimestamp(publishedUts)

		if fic.updated is None:
			fic.updated = fic.published
		if fic.updated is not None:
			updatedUts = util.parseDateAsUnix(fic.updated, fic.fetched)
			fic.updated = OilTimestamp(updatedUts)

		fic.ficStatus = FicStatus.ongoing  # TODO chapter/chapters?

		if totalChapters is None or completedChapters < totalChapters:
			fic.ficStatus = FicStatus.ongoing

		statusDt = soup.find('dt', {'class': 'status'})
		if statusDt is not None:
			if statusDt.contents[0] == 'Completed:':
				fic.ficStatus = FicStatus.complete
				cText = ' '.join(soup.find('dd', {'class': 'status'}).contents).strip()
				updatedUts = util.parseDateAsUnix(cText, fic.fetched)
				fic.updated = OilTimestamp(updatedUts)
			elif statusDt.contents[0] == 'Updated:':
				fic.ficStatus = FicStatus.ongoing
				uText = ' '.join(soup.find('dd', {'class': 'status'}).contents).strip()
				updatedUts = util.parseDateAsUnix(uText, fic.fetched)
				fic.updated = OilTimestamp(updatedUts)
			else:
				raise Exception('unkown status: {}'.format(statusDt.contents[0]))

		byline = soup.find('h3', {'class': 'byline heading'})
		authorLink = byline.find('a')
		if authorLink is None \
				and (fic.author is not None and len(fic.author) > 0): # type: ignore
			pass # updated author to anon, don't make changes
		elif authorLink is None \
				and (fic.author is None or len(fic.author) < 1): # type: ignore
			# first loaded after it was already set to anonymous
			authorUrl = ''
			author = 'Anonymous'
			authorId = 'Anonymous'
			self.setAuthor(fic, author, authorUrl, authorId)
		else:
			authorUrl = byline.find('a').get('href')
			author = ' '.join(byline.find('a').contents)
			authorId = author # map pseudo to real?
			self.setAuthor(fic, author, authorUrl, authorId)

		if fic.chapterCount > 1:
			fic.upsert()
			localChapterIdSelect = soup.find(id='selected_id').findAll('option')
			# note: ao3 sometimes says there are less chapters than there really
			# are, possibly due to caching on their end. We just ensure there's _at
			# least_ chapterCount chapters, then fetch whatever the dropdown tells
			# us to
			if len(localChapterIdSelect) > fic.chapterCount:
				fic.chapterCount = len(localChapterIdSelect)
				fic.upsert()
			if len(localChapterIdSelect) != fic.chapterCount:
				raise Exception('mismatching localChapterId count?')

			for cid in range(1, fic.chapterCount + 1):
				chap = fic.chapter(cid)
				chap.url = '{}{}/chapters/{}?view_adult=true'.format(self.baseUrl,
						fic.localId, localChapterIdSelect[cid - 1].get('value'))
				chap.localChapterId = localChapterIdSelect[cid - 1].get('value')
				chap.title = localChapterIdSelect[cid - 1].getText().strip()
				if chap.title is not None:
					chap.title = util.cleanChapterTitle(chap.title, cid)
				chap.upsert()

		fandomDd = soup.find('dd', {'class': 'fandom tags'})
		if fandomDd is not None:
			fandomTags = fandomDd.findAll('a', {'class': 'tag'})
			for ft in fandomTags:
				originalF = ft.contents[0].strip()
				f = originalF.lower()
				if (f.startswith("harry potter ") and f.endswith("rowling")) \
						or f == 'harry potter - fandom' \
						or f == 'fantastic beasts and where to find them (movies)' \
						or f == 'harry potter next generation - fandom':
					fic.add(Fandom.define('Harry Potter'))
				elif f == 'sherlock - fandom' or f == 'sherlock (tv)' \
						or f == 'sherlock holmes & related fandoms' \
						or f == 'sherlock holmes - arthur conan doyle' \
						or f == 'sherlock holmes (downey films)':
					fic.add(Fandom.define('Sherlock Holmes'))
				elif f == 'furry (fandom)' or f == 'harry - fandom':
					continue # skip
				elif f == 'fleurmione - fandom':
					continue # skip
				elif f == 'skyfall (2012) - fandom':
					fic.add(Fandom.define('James Bond'))
				elif f == 'orphan black (tv)':
					fic.add(Fandom.define('Orphan Black'))
				elif f == 'naruto' or f == 'naruto shippuden' \
						or f == 'naruto shippuuden - fandom':
					fic.add(Fandom.define('Naruto'))
				elif f == 'naruto/harry potter':
					fic.add(Fandom.define('Naruto'))
					fic.add(Fandom.define('Harry Potter'))
				elif f == 'bleach':
					fic.add(Fandom.define('Bleach'))
				elif f == 'iron man (movies)' or f == 'iron man - all media types' \
						or f == 'iron man (comic)' or f == 'iron man - fandom' \
						or f == 'iron man (comics)':
					fic.add(Fandom.define('Iron Man'))
				elif f == 'the avengers (marvel) - all media types' \
						or f == 'the avengers (marvel movies)' \
						or f == 'the avengers - ambiguous fandom' \
						or f == 'the avengers (2012)' \
						or f == 'the avengers' \
						or f == 'avengers (marvel) - all media types' \
						or f == 'marvel avengers movies universe' \
						or f == 'avengers':
					fic.add(Fandom.define('Avengers'))
				elif f == 'marvel 616':
					fic.add(Fandom.define('Marvel'))
					fic.add(Fandom.define('Marvel 616'))
				elif f == 'thor (movies)' or f == 'thor - all media types':
					fic.add(Fandom.define('Thor'))
				elif f == 'captain america (movies)' \
						or f == 'captain america - all media types' \
						or f == 'captain america (comics)':
					fic.add(Fandom.define('Captain America'))
				elif f == 'avatar: the last airbender' \
						or f == 'avatar: legend of korra' \
						or f == 'avatar the last airbender - fandom':
					fic.add(Fandom.define('Avatar'))
				elif f == 'original work':
					fic.add(Fandom.define('Original Work'))
				elif f == 'stargate atlantis':
					fic.add(Fandom.define('Stargate Atlantis'))
				elif f == 'stargate sg-1':
					fic.add(Fandom.define('Stargate SG-1'))
				elif f == 'stargate - all series':
					fic.add(Fandom.define('Stargate Atlantis'))
					fic.add(Fandom.define('Stargate SG-1'))
				elif f == 'agents of s.h.i.e.l.d. (tv)':
					fic.add(Fandom.define('Avengers'))
				elif f == 'supernatural':
					fic.add(Fandom.define('Supernatural'))
				elif f == 'teen wolf (tv)':
					fic.add(Fandom.define('Teen Wolf'))
				elif f == 'grimm (tv)':
					fic.add(Fandom.define('Grimm'))
				elif f == 'the amazing spider-man (movies - webb)' \
						or f == 'spider-man - all media types' \
						or f == 'spider-man: homecoming (2017)':
					fic.add(Fandom.define('Spiderman'))
				elif f == 'x-men - all media types' or f == 'x-men (movieverse)' \
						or f == 'x-men (comicverse)':
					fic.add(Fandom.define('X-Men'))
				elif f == 'lord of the rings - j. r. r. tolkien' \
						or f == 'the lord of the rings - j. r. r. tolkien':
					fic.add(Fandom.define('Lord of the Rings'))
				elif f == 'crisis core: final fantasy vii' \
						or f == 'compilation of final fantasy vii' \
						or f == 'final fantasy vii':
					fic.add(Fandom.define('Final Fantasy VII'))
					fic.add(Fandom.define('Final Fantasy'))
				elif f == 'sen to chihiro no kamikakushi | spirited away':
					fic.add(Fandom.define('Spirited Away'))
				elif f == 'howl no ugoku shiro | howl\'s moving castle':
					fic.add(Fandom.define('Howl\'s Moving Castle'))
				elif f == 'rise of the guardians (2012)':
					fic.add(Fandom.define('Rise of the Guardians'))
				elif f == 'doctor who' \
						or f == 'doctor who (2005)' \
						or f == 'doctor who & related fandoms':
					fic.add(Fandom.define('Doctor Who'))
				elif f == 'daredevil (tv)' \
						or f == 'daredevil (comics)':
					fic.add(Fandom.define('DareDevil'))
				elif f == 'labyrinth (1986)':
					fic.add(Fandom.define('Labyrinth'))
				elif f == 'gravity falls':
					fic.add(Fandom.define('Gravity Falls'))
				elif f == 'once upon a time (tv)':
					fic.add(Fandom.define('Once Upon a Time'))
				elif f == 'doctor strange (comics)':
					fic.add(Fandom.define('Doctor Strange'))
				elif f == 'the sentinel':
					fic.add(Fandom.define('The Sentinel'))
				elif f == 'teen titans (animated series)':
					fic.add(Fandom.define('Teen Titans'))
				elif f == 'dcu' or f == 'dcu animated' \
						or f == 'dcu (comics)' or f == 'dc extended universe' \
						or f == 'dc animated universe':
					fic.add(Fandom.define('DC'))
				elif f == 'vampire hunter d':
					fic.add(Fandom.define('Vampire Hunter D'))
				elif f == 'homestuck':
					fic.add(Fandom.define('Homestuck'))
				elif f == 'one piece':
					fic.add(Fandom.define('One Piece'))
				elif f == 'batman (movies - nolan)':
					fic.add(Fandom.define('Batman'))
				elif f == 'die hard (movies)':
					fic.add(Fandom.define('Die Hard'))
				elif f == 'discworld - terry pratchett':
					fic.add(Fandom.define('Discworld'))
				elif f == 'gossip girl':
					fic.add(Fandom.define('Gossip Girl'))
				elif f == 'a song of ice and fire - george r. r. martin' \
						or f == 'a song of ice and fire & related fandoms':
					fic.add(Fandom.define('A Song of Ice and Fire'))
				elif f == 'supergirl (tv 2015)':
					fic.add(Fandom.define('Supergirl'))
				elif f == 'merlin (tv)':
					fic.add(Fandom.define('Merlin'))
				elif f == 'star trek':
					fic.add(Fandom.define('Star Trek'))
				elif f == 'steven universe (cartoon)':
					fic.add(Fandom.define('Steven Universe'))
				elif f == 'hellsing':
					fic.add(Fandom.define('Hellsing'))
				elif f == 'the breaker':
					fic.add(Fandom.define('The Breaker'))
				elif f == 'smallville':
					fic.add(Fandom.define('Smallville'))
				elif f == '베리타스 | veritas (manhwa)':
					fic.add(Fandom.define('Veritas (manhwa)'))
				elif f == 'guardians of childhood - william joyce':
					fic.add(Fandom.define('Guardians of Childhood'))
				elif f == 'person of interest (tv)':
					fic.add(Fandom.define('Person of Interest'))
				elif f == 'james bond (craig movies)':
					fic.add(Fandom.define('James Bond'))
				elif f == 'the bourne legacy (2012)':
					fic.add(Fandom.define('Jason Bourne'))
				elif f == 'numb3rs':
					fic.add(Fandom.define('Numb3rs'))
				elif f == 'temeraire - naomi novik':
					fic.add(Fandom.define('Temeraire'))
				elif f == 'twilight series - stephenie meyer':
					fic.add(Fandom.define('Twilight'))
				elif f == 'dungeons and dragons - fandom':
					fic.add(Fandom.define('Dungeons and Dragons'))
				elif f == 'american horror story' \
						or f == 'american horror story: cult':
					fic.add(Fandom.define('American Horror Story'))
				elif f == 'worm (web serial novel)' \
						or f == 'worm - wildbow' \
						or f == 'parahumans series - wildbow' \
						or f == 'worm (web serial) | wildbow' \
						or f == 'worm - fandom' \
						or f == 'parahumans - fandom' \
						or f == 'worm (parahumans)' \
						or f == 'worm (web serial)' \
						or f == 'worm | parahumans' \
						or f == 'worm (web novel)':
					fic.add(Fandom.define('Worm'))
				elif f == 'toaru kagaku no railgun | a certain scientific railgun':
					fic.add(Fandom.define('A Certain Scientific Railgun'))
				elif f == 'toaru majutsu no index | a certain magical index':
					fic.add(Fandom.define('A Certain Magical Index'))
				elif f == 'cthulhu mythos - h. p. lovecraft':
					fic.add(Fandom.define('Cthulhu'))
				elif f == 'transformers - all media types':
					fic.add(Fandom.define('Transformers'))
				elif f == 'destiny (video game)':
					fic.add(Fandom.define('Destiny'))
				elif f == 'fandom - fandom' or f == 'meta - fandom':
					pass # >_>
				elif f == 'house m.d.':
					fic.add(Fandom.define('House, M.D.'))
				elif f == 'the hobbit (jackson movies)':
					fic.add(Fandom.define('The Hobbit'))
				elif f == 'doctor strange (2016)':
					fic.add(Fandom.define('Doctor Strange'))
				elif f == 'arrow (tv 2012)':
					fic.add(Fandom.define('Arrow'))
				elif f == 'the flash (tv 2014)':
					fic.add(Fandom.define('Flash'))
				elif f == 'senki zesshou symphogear':
					fic.add(Fandom.define('Symphogear'))
				elif f == 'fullmetal alchemist: brotherhood & manga' \
						or f == 'fullmetal alchemist - all media types' \
						or f == 'fullmetal alchemist (anime 2003)':
					fic.add(Fandom.define('Fullmetal Alchemist'))
				elif f == 'star wars - all media types' \
						or f == 'star wars episode vii: the force awakens (2015)' \
						or f == 'star wars prequel trilogy':
					fic.add(Fandom.define('Star Wars'))
				elif f == 'guardians of the galaxy (2014)' \
						or f == 'guardians of the galaxy - all media types' \
						or f == 'guardians of the galaxy (movies)':
					fic.add(Fandom.define('Guardians of the Galaxy'))
				elif f == 'ant man (2015)' or f == 'ant-man (movies)':
					fic.add(Fandom.define('Ant Man'))
				elif f == 'the defenders (marvel tv)':
					fic.add(Fandom.define('The Defenders'))
				elif f == 'elementary (tv)':
					fic.add(Fandom.define('Elementary'))
				elif f == 'good omens - neil gaiman & terry pratchett':
					fic.add(Fandom.define('Good Omens'))
				elif f == 'danny phantom':
					fic.add(Fandom.define('Danny Phantom'))
				elif f == 'katekyou hitman reborn!':
					fic.add(Fandom.define('Katekyo Hitman Reborn!'))
				elif f == 'welcome to night vale':
					fic.add(Fandom.define('Welcome to Night Vale'))
				elif f == 'ncis':
					fic.add(Fandom.define('NCIS'))
				elif f == 'torchwood':
					fic.add(Fandom.define('Torchwood'))
				elif f == 'magic: the gathering':
					fic.add(Fandom.define('Magic: The Gathering'))
				elif f == 'overwatch (video game)':
					fic.add(Fandom.define('Overwatch'))
				elif f == 'detroit: become human (video game)':
					fic.add(Fandom.define('Detroit: Become Human'))
				elif f == 'greek and roman mythology':
					pass
				elif f == 'life is strange (video game)':
					fic.add(Fandom.define('life is strange (video game)'))
				elif f == 'akatsuki no yona | yona of the dawn':
					fic.add(Fandom.define('Yona of the Dawn'))
				elif f == '僕のヒーローアカデミア | boku no hero academia | my hero academia':
					fic.add(Fandom.define('My Hero Academia'))
				elif f == 'voltron: legendary defender':
					fic.add(Fandom.define('Voltron'))
				elif f == 'selfie (tv)':
					fic.add(Fandom.define('Selfie'))
				elif f == 'suits (tv)':
					fic.add(Fandom.define('Suits'))
				elif f == 'fruits basket':
					fic.add(Fandom.define('Fruits Basket'))
				elif f == 'hetalia: axis powers':
					fic.add(Fandom.define('Hetalia: Axis Powers'))
				elif f == 'carmilla (web series)':
					fic.add(Fandom.define('Carmilla'))
				elif f == 'the dresden files - jim butcher':
					fic.add(Fandom.define('Dresden Files'))
				elif f == 'girl genius':
					fic.add(Fandom.define('Girl Genius'))
				elif f == 'unspecified fandom':
					pass # TODO?
				elif f == 'nightwing (comics)':
					fic.add(Fandom.define('Nightwing'))
				elif f == 'books of the raksura - martha wells':
					fic.add(Fandom.define('Books of the Raksura'))
				elif f == 'fall of ile-rien - martha wells':
					fic.add(Fandom.define('Fall of Ile-Rien'))
				elif f == 'vorkosigan saga - lois mcmaster bujold':
					fic.add(Fandom.define('Vorkosigan Saga'))
				elif f == 'highlander: the series' \
						or f == 'highlander - all media types':
					fic.add(Fandom.define('Highlander'))
				elif f == 'yoroiden samurai troopers | ronin warriors':
					fic.add(Fandom.define('Ronin Warriors'))
				elif f == 'hockey rpf':
					fic.add(Fandom.define('Hockey RPF'))
				elif f == 'pacific rim (2013)':
					fic.add(Fandom.define('Pacific Rim'))
				elif f == 'enchanted forest chronicles - patricia wrede':
					fic.add(Fandom.define('Enchanted Forest Chronicles'))
				elif f == 'tortall - tamora pierce':
					fic.add(Fandom.define('Tortall'))
				elif f == 'protector of the small - tamora pierce':
					fic.add(Fandom.define('Protector of the Small'))
				elif f == 'leverage':
					fic.add(Fandom.define('Leverage'))
				elif f == 'valdemar series - mercedes lackey':
					fic.add(Fandom.define('Valdemar Series'))
				elif f == 'b.p.r.d.' \
						or f == 'bureau for paranormal research and defense':
					fic.add(Fandom.define('B.P.R.D.'))
				elif f == 'hellboy (comic)':
					fic.add(Fandom.define('Hellboy'))
				elif f == 'sga/avatar':
					fic.add(Fandom.define('Stargate Atlantis'))
					fic.add(Fandom.define('Avatar'))
				elif f == 'annihilation (2018 garland)':
					fic.add(Fandom.define('Annihilation'))
				elif f == 'craft sequence - max gladstone':
					fic.add(Fandom.define('Craft Sequence'))
				elif f == 'the good place (tv)':
					fic.add(Fandom.define('The Good Place'))
				elif f == 'jessica jones (tv)':
					fic.add(Fandom.define('Jessica Jones'))
				elif f == 'mad max series (movies)':
					fic.add(Fandom.define('Mad Max'))
				elif f == 'american gods (tv)':
					fic.add(Fandom.define('American Gods'))
				elif f == 'terminator: the sarah connor chronicles':
					fic.add(Fandom.define('Terminator: The Sarah Connor Chronicles'))
					fic.add(Fandom.define('Terminator'))
				elif f == 'wolf 359 (radio)':
					fic.add(Fandom.define('Wolf 359'))
				elif f == 'shadowrun: dragonfall':
					fic.add(Fandom.define('Shadowrun'))
				elif f == 'ars paradoxica (podcast)':
					fic.add(Fandom.define('Ars Paradoxica'))
				elif f == 'love is strange - fandom':
					fic.add(Fandom.define('Love is Strange'))
				elif f == 'dune - all media types':
					fic.add(Fandom.define('Dune'))
				elif f == 'dragon age: origins':
					fic.add(Fandom.define('Dragon Age: Origins'))
				elif f == 'game of thrones (tv)':
					fic.add(Fandom.define('Game of Thrones'))
				elif f == 'chronicles of amber - roger zelazny':
					fic.add(Fandom.define('Chronicles of Amber'))
				elif f == 'the southern reach trilogy - jeff vandermeer':
					fic.add(Fandom.define('The Southern Reach Trilogy'))
				elif f == 'continuum (tv)':
					fic.add(Fandom.define('Continuum'))
				elif f == 'mage: the ascension':
					fic.add(Fandom.define('Mage: The Ascension'))
				elif f == 'the good wife (tv)' or f == 'good wife (tv)':
					fic.add(Fandom.define('The Good Wife'))
				elif f == 'alliance-union - c. j. cherryh':
					fic.add(Fandom.define('Alliance-Union'))
				elif f == 'indexing - seanan mcguire':
					fic.add(Fandom.define('Indexing'))
				elif f == 'ultraviolet (tv)':
					fic.add(Fandom.define('Ultraviolet'))
				elif f == 'veronica mars (tv)':
					fic.add(Fandom.define('Veronica Mars'))
				elif f == 'secret circle (tv)':
					fic.add(Fandom.define('Secret Circle'))
				elif f == 'mahou shoujo madoka magika | puella magi madoka magica':
					fic.add(Fandom.define('Madoka Magica'))
				elif f == 'agent carter (tv)':
					fic.add(Fandom.define('Agent Carter'))
				elif f == 'dracula & related fandoms':
					fic.add(Fandom.define('Dracula'))
				elif f == 'dragon ball':
					fic.add(Fandom.define('Dragon Ball'))
				elif f == 'mass effect - all media types':
					fic.add(Fandom.define('Mass Effect'))
				elif f == 'firefly' or f == 'serenity (2005)':
					fic.add(Fandom.define('Firefly'))
				else:
					anyHere = False
					global ao3FandomsMap
					for fm in ao3FandomsMap:
						here = False
						for uf in fm[0]:
							if f == uf.lower().strip():
								here = True
								break
						if not here:
							continue
						anyHere = True
						for mf in fm[1]:
							fic.add(Fandom.define(mf))
					if not anyHere:
						util.logMessage(f'ao3|unknown fandom|{fic.url}|{originalF}')
						#raise Exception('unknown fandom: {} "{}"'.format(fic.url, originalF))

		ourDoms = fic.fandoms()
		# we have a canonical fandom, try to find our characters
		if len(ourDoms) == 1:
			relationshipDd = soup.find('dd', {'class': 'relationship tags'})
			if relationshipDd is not None:
				relationshipTags = relationshipDd.findAll('a', {'class': 'tag'})
				for rt in relationshipTags:
					r = rt.contents[0]
					chars = r.split('/')
					if len(chars) > 8: # TODO: sometimes more?
						raise Exception('unable to parse relationship: {}'.format(r))
					for char in chars:
						fic.add(Character.defineInFandom(ourDoms[0], char, self.ftype))

		return fic

