from typing import List

from htypes import FicType
import scrape

from adapter.wordpressAdapter import WordpressAdapter


class ParahumansAdapter(WordpressAdapter):
    def __init__(self) -> None:
        # https://www.parahumans.net/table-of-contents/
        super().__init__(True,
                         'https://www.parahumans.net', 'parahumans.net',
                         FicType.parahumans)
        self.sub_patt = "<a href=['\"]https?://(www.)parahumans.net[^'\"]*['\"]>(Last|Previous|Next) Chapter</a>"
        self.title = 'Ward'
        self.fandom = 'Worm'
        self.ageRating = 'M'
        self.author = 'Wildbow'
        self.authorUrl = 'https://www.parahumans.net/support-wildbow'
        self.description = '''
The unwritten rules that govern the fights and outright wars between ‘capes’ have been amended: everyone gets their second chance.  It’s an uneasy thing to come to terms with when notorious supervillains and even monsters are playing at being hero.  The world ended two years ago, and as humanity straddles the old world and the new, there aren’t records, witnesses, or facilities to answer the villains’ past actions in the present.  One of many compromises, uneasy truces and deceptions that are starting to splinter as humanity rebuilds.

None feel the injustice of this new status quo or the lack of established footing more than the past residents of the parahuman asylums.  The facilities hosted parahumans and their victims, but the facilities are ruined or gone; one of many fragile ex-patients is left to find a place in a fractured world.  She’s perhaps the person least suited to have anything to do with this tenuous peace or to stand alongside these false heroes.  She’s put in a position to make the decision: will she compromise to help forge what they call, with dark sentiment, a second golden age?  Or will she stand tall as a gilded dark age dawns?'''

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
                if href == 'https://www.parahumans.net/2018/11/24/interlude-10-x' \
                        and len(chapterUrls) > 0 and chapterUrls[-1] == href:
                    continue
                if href == 'https://www.parahumans.net/2018/12/11/interlude-10-y' \
                        and len(chapterUrls) > 0 and chapterUrls[-1] == href:
                    continue
                if href == 'https://www.parahumans.net/2019/04/27/black-13-8' \
                        and len(chapterUrls) > 0 and chapterUrls[-1] == href:
                    href = 'https://www.parahumans.net/2019/04/30/black-13-x'
                if href in chapterUrls:
                    raise Exception(
                        f'duplicate chapter url: {href} {len(chapterUrls)}')
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
                if content == '(Tats)' \
                        and len(chapterTitles) > 0 and chapterTitles[-1] == '10.x':
                    chapterTitles[-1] = '10.x (Tats)'
                    continue
                if content == '(Boy in the shell)' \
                        and len(chapterTitles) > 0 and chapterTitles[-1] == '10.y':
                    chapterTitles[-1] = '10.y (Boy in the shell)'
                    continue
                chapterTitles += [content]
        return chapterTitles
