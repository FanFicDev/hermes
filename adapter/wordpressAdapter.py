import re
from typing import List, Optional, Union
import dateutil.parser
import urllib

from htypes import FicType, FicId
from store import OilTimestamp, Language, Fic, FicChapter, Fandom, FicStatus
import util
import scrape

from adapter.adapter import Adapter


class WordpressAdapter(Adapter):
    def __init__(self,
                 baseUrl: str,
                 sub_patt: str,
                 title: str,
                 fandom: str,
                 ageRating: str,
                 author: str,
                 authorUrl: str,
                 description: str,
                 urlFragments: Union[str, List[str]] = [],
                 ftype: FicType = FicType.broken) -> None:
        super().__init__(True, baseUrl, urlFragments, ftype)
        self.sub_patt = sub_patt
        self.title = title
        self.fandom = fandom
        self.ageRating = ageRating
        self.author = author
        self.authorUrl = authorUrl
        self.description = description
        self.tocUrl = '{}/table-of-contents'.format(self.baseUrl)

    def canonizeUrl(self, url: str) -> str:
        url = urllib.parse.urljoin(self.baseUrl, url)
        url = scrape.canonizeUrl(url)
        prefixMap = [('http://', 'https://'),
                     ('https://{}'.format(self.urlFragments[0]),
                      'https://www.{}'.format(self.urlFragments[0]))]
        for pm in prefixMap:
            if url.startswith(pm[0]):
                url = pm[1] + url[len(pm[0]):]
        if not url.endswith('/'):
            url += '/'
        return url

    def getChapterPublishDate(self, url: str) -> OilTimestamp:
        from bs4 import BeautifulSoup
        url = self.canonizeUrl(url)
        data = scrape.softScrape(url)
        soup = BeautifulSoup(data, 'html5lib')
        publishTimes = soup.findAll('time',
                                    {'class': ['entry-date', 'published']})
        if len(publishTimes) != 1:
            raise Exception('cannot find publish time for {}'.format(url))
        uts = util.dtToUnix(
            dateutil.parser.parse(publishTimes[0].get('datetime')))
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

        # parahumans is id 1
        # TODO: change FicType.parahumans to wordpress?
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
        return re.sub(self.sub_patt, '', content)

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
        return Fic.lookup((fic.id, ))

    def parseInfoInto(self, fic: Fic, html: str) -> Fic:
        html = html.replace('\r\n', '\n')

        # wooh hardcoding
        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")

        fic.title = self.title
        fic.ageRating = self.ageRating

        self.setAuthor(fic, self.author, self.authorUrl, str(1))

        # taken from https://www.parahumans.net/about/
        fic.description = self.description

        chapterUrls = self.getChapterUrls(html)
        oldChapterCount = fic.chapterCount
        fic.chapterCount = len(chapterUrls)

        # TODO?
        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        if fic.ficStatus is None or fic.ficStatus == FicStatus.broken:
            fic.ficStatus = FicStatus.ongoing

        fic.published = self.getChapterPublishDate(chapterUrls[0])
        fic.updated = self.getChapterPublishDate(chapterUrls[-1])

        titles = self.getChapterTitles()

        if oldChapterCount is None or fic.chapterCount > oldChapterCount:
            fic.wordCount = 0
        fic.wordCount = 0
        if fic.wordCount == 0:
            fic.upsert()
            # save urls first...
            for cid in range(1, fic.chapterCount + 1):
                c = fic.chapter(cid)
                c.localChapterId = str(cid)
                c.url = chapterUrls[cid - 1]
                c.upsert()

            # then attempt to set title and content
            for cid in range(1, fic.chapterCount + 1):
                if cid <= len(titles):
                    c.title = titles[cid - 1]
                elif c.title is None:
                    c.title = ''
                c.cache()
                chtml = c.html()
                c.upsert()
                if chtml is not None:
                    fic.wordCount += len(chtml.split())

        fic.add(Fandom.define(self.fandom))
        # TODO: chars/relationship?

        return fic
