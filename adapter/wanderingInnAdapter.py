import re
from typing import List, Optional
import dateutil.parser

from htypes import FicType, FicId
from store import OilTimestamp, Language, Fic, FicChapter, Fandom, FicStatus
import util
import scrape

from adapter.adapter import Adapter


class WanderingInnAdapter(Adapter):
    def __init__(self) -> None:
        # https://wanderinginn.com/table-of-contents/
        super().__init__(True,
                         'https://wanderinginn.com', 'wanderinginn.com',
                         FicType.wanderinginn)
        self.tocUrl = '{}/table-of-contents'.format(self.baseUrl)

    def canonizeUrl(self, url: str) -> str:
        url = scrape.canonizeUrl(url)
        prefixMap = [('http://', 'https://'),
                     ('https://{}'.format(self.urlFragments[0]), 'https://www.{}'.format(self.urlFragments[0]))]
        for pm in prefixMap:
            if url.startswith(pm[0]):
                url = pm[1] + url[len(pm[0]):]
        return url

    def getChapterUrls(self, data: str = None) -> List[str]:
        from bs4 import BeautifulSoup  # type: ignore
        if data is None:
            data = scrape.softScrape(self.tocUrl)
        soup = BeautifulSoup(data, 'html5lib')
        entryContents = soup.findAll('div', {'class': 'entry-content'})
        chapterUrls: List[str] = []

        for entryContent in entryContents:
            aTags = entryContent.findAll('a')
            for aTag in aTags:
                href = self.canonizeUrl(aTag.get('href'))
                chapterUrls += [href]
        return chapterUrls

    def getChapterTitles(self, data: str = None) -> List[str]:
        from bs4 import BeautifulSoup
        if data is None:
            data = scrape.softScrape(self.tocUrl)
        soup = BeautifulSoup(data, 'html5lib')
        entryContents = soup.findAll('div', {'class': 'entry-content'})
        chapterTitles: List[str] = []
        for entryContent in entryContents:
            aTags = entryContent.findAll('a')
            for aTag in aTags:
                content = aTag.get_text().strip()
                chapterTitles += [content]
        return chapterTitles

    def getChapterPublishDate(self, url: str) -> OilTimestamp:
        from bs4 import BeautifulSoup
        url = self.canonizeUrl(url)
        data = scrape.softScrape(url)
        soup = BeautifulSoup(data, 'html5lib')
        publishTimes = soup.findAll(
            'time', {'class': ['entry-date', 'published']})
        if len(publishTimes) != 1:
            raise Exception('cannot find publish time for {}'.format(url))
        uts = util.dtToUnix(dateutil.parser.parse(
            publishTimes[0].get('datetime')))
        return OilTimestamp(uts)

    def constructUrl(self, lid: str, cid: int = None) -> str:
        if cid is None:
            return self.baseUrl
        chapterUrls = self.getChapterUrls()
        return chapterUrls[cid - 1]

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        url = self.canonizeUrl(url)

        # if the url matches a chapter url, return it
        chapterUrls = self.getChapterUrls()
        if url in chapterUrls:
            return FicId(self.ftype, str(1), chapterUrls.index(url), False)

        # wanderinginn is id 1
        return FicId(self.ftype, str(1), ambiguous=False)

    def create(self, fic: Fic) -> Fic:
        return self.getCurrentInfo(fic)

    def extractContent(self, fic: Fic, html: str) -> str:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html5lib')
        entryContents = soup.findAll('div', {'class': 'entry-content'})
        if len(entryContents) != 1:
            raise Exception('cannot find entry-content')
        entryContent = entryContents[0]

        shareDivs = entryContent.find_all('div', {'class', 'sharedaddy'})
        for shareDiv in shareDivs:
            shareDiv.extract()

        for audio in entryContent.find_all('audio'):
            audio.extract()

        content = str(entryContent)
        patt = "<a href=['\"]https://wanderinginn[^'\"]*['\"]>\s*(<span style=\"float:right;\">|)\s*(Last|Previous|Next)\s+Chapter\s*(</span>|)\s*</a>"

        return re.sub(patt, '', content)

    def buildUrl(self, chapter: FicChapter) -> str:
        if len(chapter.url.strip()) > 0:
            return chapter.url
        return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

    def getCurrentInfo(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId)
        url = self.tocUrl
        data = scrape.scrape(url)

        fic = self.parseInfoInto(fic, data['raw'])
        fic.upsert()
        return Fic.lookup((fic.id,))

    def parseInfoInto(self, fic: Fic, html: str) -> Fic:
        html = html.replace('\r\n', '\n')

        # wooh hardcoding
        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")

        fic.title = 'The Wandering Inn'
        fic.ageRating = 'M'

        self.setAuthor(fic,
                       'pirate aba ', 'https://www.patreon.com/user?u=4240617', str(1))

        # taken from https://wanderinginn.com/
        fic.description = '''
An inn is a place to rest, a place to talk and share stories, or a place to find adventures, a starting ground for quests and legends.

In this world, at least. To Erin Solstice, an inn seems like a medieval relic from the past. But here she is, running from Goblins and trying to survive in a world full of monsters and magic. She’d be more excited about all of this if everything wasn’t trying to kill her.

But an inn is what she found, and so that’s what she becomes. An innkeeper who serves drinks to heroes and monsters–

Actually, mostly monsters. But it’s a living, right?

This is the story of the Wandering Inn.'''

        chapterUrls = self.getChapterUrls(html)
        fic.chapterCount = len(chapterUrls)
        oldChapterCount = fic.chapterCount

        # TODO?
        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        if fic.ficStatus is None:
            fic.ficStatus = FicStatus.ongoing  # type: ignore

        fic.published = self.getChapterPublishDate(chapterUrls[0])
        fic.updated = self.getChapterPublishDate(chapterUrls[-1])

        titles = self.getChapterTitles()

        if oldChapterCount is None or fic.chapterCount > oldChapterCount:
            fic.wordCount = 0
        fic.wordCount = 0
        if fic.wordCount == 0:
            fic.upsert()
            for cid in range(1, fic.chapterCount + 1):
                c = fic.chapter(cid)
                c.localChapterId = str(cid)
                c.url = chapterUrls[cid - 1]
                if cid <= len(titles):
                    c.title = titles[cid - 1]
                elif c.title is None:
                    c.title = ''
                c.cache()
                chtml = c.html()
                c.upsert()
                if chtml is not None:
                    fic.wordCount += len(chtml.split())

        fic.add(Fandom.define('The Wandering Inn'))
        # TODO: chars/relationship?

        return fic
