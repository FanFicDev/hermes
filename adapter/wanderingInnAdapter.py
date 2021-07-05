from typing import List

from htypes import FicType
import scrape

from adapter.wordpressAdapter import WordpressAdapter


class WanderingInnAdapter(WordpressAdapter):
    def __init__(self) -> None:
        # https://wanderinginn.com/table-of-contents/
        super().__init__(
            'https://wanderinginn.com',
            "<a href=['\"]https://wanderinginn[^'\"]*['\"]>\s*(<span style=\"float:right;\">|)\s*(Last|Previous|Next)\s+Chapter\s*(</span>|)\s*</a>",
            'The Wandering Inn', 'The Wandering Inn', 'M', 'pirate aba',
            'https://www.patreon.com/user?u=4240617', '''
An inn is a place to rest, a place to talk and share stories, or a place to find adventures, a starting ground for quests and legends.

In this world, at least. To Erin Solstice, an inn seems like a medieval relic from the past. But here she is, running from Goblins and trying to survive in a world full of monsters and magic. She’d be more excited about all of this if everything wasn’t trying to kill her.

But an inn is what she found, and so that’s what she becomes. An innkeeper who serves drinks to heroes and monsters–

Actually, mostly monsters. But it’s a living, right?

This is the story of the Wandering Inn.''', 'wanderinginn.com',
            FicType.wanderinginn)

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
