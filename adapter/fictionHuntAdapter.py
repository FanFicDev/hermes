from typing import List, Optional
import re

from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher
from htypes import FicId, FicType
import scrape
from store import Fic, FicChapter, FicStatus, Language, OilTimestamp
import util


class FictionHuntAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(
            True, "http://fictionhunt.com", "fictionhunt.com", FicType.fictionhunt
        )

    def constructUrl(self, storyId: str, chapterId: Optional[int] = None) -> str:
        if chapterId is None:
            return f"{self.baseUrl}/read/{storyId}"
        # note: does not support titles
        return f"{self.baseUrl}/read/{storyId}/{chapterId}"

    def buildUrl(self, chapter: "FicChapter") -> str:
        if chapter.fic is None:
            chapter.fic = Fic.lookup((chapter.ficId,))
        return self.constructUrl(chapter.fic.localId, chapter.chapterId)

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        parts = url.split("/")
        httpOrHttps = parts[0] == "https:" or parts[0] == "http:"
        if len(parts) < 5:
            return None
        if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
            return None
        if parts[3] != "read":
            return None
        if (
            len(parts) < 5
            or len(parts[4].strip()) < 1
            or not parts[4].strip().isnumeric()
        ):
            return None

        storyId = int(parts[4])
        chapterId = None
        ambi = len(parts) < 6
        if not ambi and len(parts[5].strip()) > 0:
            chapterId = int(parts[5])
        return FicId(self.ftype, str(storyId), chapterId, ambi)

    def create(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId, 1)

        # scrape fresh info
        data = scrape.scrape(fic.url)

        fic = self.parseInfoInto(fic, data["raw"])
        fic.insert()

        chapter = fic.chapter(1)
        chapter.setHtml(data["raw"])
        chapter.upsert()

        return Fic.lookup((fic.id,))

    def extractContent(self, fic: Fic, html: str) -> str:
        lines = html.replace("\r", "\n").split("\n")
        parts: List[str] = []
        inStory = False
        for line in lines:
            if line.find('class="text') != -1:
                inStory = True
            if inStory:
                if (
                    line.find('<div class="pagerHolder') != -1
                    or line.lower().find("<script") != -1
                ):
                    inStory = False
                    break
                parts += [line]
        return " ".join(parts)

    def getCurrentInfo(self, fic: Fic) -> Fic:
        # scrape fresh info
        data = scrape.scrape(self.constructUrl(fic.localId, 1))

        return self.parseInfoInto(fic, data["raw"])

    def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(wwwHtml, "html.parser")
        divDetails = soup.find_all("div", {"class": "details"})
        if len(divDetails) != 1:
            raise Exception("error: unable to find details\n")
        else:
            divDetails = divDetails[0]

        text = divDetails.get_text()
        pt_str = str(divDetails)

        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")  # TODO: don't hard code?

        divTitle = soup.find_all("div", {"class": "title"})
        if len(divTitle) == 1:
            fic.title = divTitle[0].get_text().strip()
        else:
            raise Exception(f"error: unable to find title:\n{pt_str}\n")

        fic.url = self.constructUrl(fic.localId, 1)

        # TODO: this may not exist on fictionhunt?
        fic.description = f"archive of {fic.title} from fictionhunt TODO"

        # default optional fields
        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        matcher = RegexMatcher(
            text,
            {
                "ageRating": ("Rated:\s+(\S+)", str),
                "chapterCount?": ("Chapters:\s+(\d+)", int),
                "wordCount": ("Words:\s+(\S+)", int),
                "reviewCount?": ("Reviews:\s+(\S+)", int),
                "favoriteCount?": ("Favs:\s+(\S+)", int),
                "followCount?": ("Follows:\s+(\S+)", int),
                "updated?": ("Updated:\s+(\S+)", str),
                "published": ("Published:\s+(\S+)", str),
            },
        )
        matcher.matchAll(fic)

        if fic.published is not None:
            publishedUts = util.parseDateAsUnix(fic.published, fic.fetched)
            fic.published = OilTimestamp(publishedUts)

        if fic.updated is None:
            fic.updated = fic.published
        elif fic.updated is not None:
            updatedUts = util.parseDateAsUnix(fic.updated, fic.fetched)
            fic.updated = OilTimestamp(updatedUts)

        if fic.chapterCount is None:
            fic.chapterCount = 1

        match = re.search("- Complete -", text)
        if match is None:
            fic.ficStatus = FicStatus.ongoing
        else:
            fic.ficStatus = FicStatus.complete

        for a in divDetails.find_all("a"):
            a_href = a.get("href")
            if a_href.find("fanfiction.net/u/") != -1:
                author = a.get_text()
                authorUrl = a_href
                authorId = a_href.split("/")[-1]
                self.setAuthor(fic, author, authorUrl, authorId)
                break
        else:
            raise Exception(f"unable to find author:\n{text}")

        # TODO: hardcode Harry Potter fanfic?

        return fic
