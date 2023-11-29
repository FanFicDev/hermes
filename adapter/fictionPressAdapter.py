from typing import List, Optional
import re
import time

from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher
from htypes import FicId, FicType
import scrape
import skitter
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util

fictionPressCategories = {
    "fiction",
}

fictionPressGenres = {
    "General",
    "Romance",
    "Fantasy",
    "Young Adult",
    "Horror",
    "Supernatural",
    "Humor",
    "Sci-Fi",
    "Action",
    "Essay",
    "Manga",
    "Historical",
    "Mystery",
    "Biography",
    "Thriller",
    "Spiritual",
    "Mythology",
    "Play",
    "Fable",
    "Kids",
    "Western",
}


class FictionPressAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(
            True,
            "https://www.fictionpress.com",
            "fictionpress.com",
            FicType.fictionpress,
        )

    def constructUrl(
        self, storyId: str, chapterId: Optional[int] = None, title: Optional[str] = None
    ) -> str:
        if chapterId is None:
            return f"{self.baseUrl}/s/{storyId}"
        if title is None:
            return f"{self.baseUrl}/s/{storyId}/{chapterId}"
        return f"{self.baseUrl}/s/{storyId}/{chapterId}/{util.urlTitle(title)}"

    def buildUrl(self, chapter: "FicChapter") -> str:
        if chapter.fic is None:
            chapter.fic = Fic.lookup((chapter.ficId,))
        return self.constructUrl(
            chapter.fic.localId, chapter.chapterId, chapter.fic.title
        )

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        if url.find("?") >= 0:
            url = url.split("?")[0]
        parts = url.split("/")
        httpOrHttps = parts[0] == "https:" or parts[0] == "http:"
        if len(parts) < 5:
            return None
        if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
            return None
        if parts[3] != "s" and parts[3] != "r":
            return None
        if (
            len(parts) < 5
            or len(parts[4].strip()) < 1
            or not parts[4].strip().isnumeric()
        ):
            return None

        storyId = int(parts[4])
        chapterId = None
        ambi = True
        if (
            len(parts) >= 6
            and parts[3] == "s"
            and len(parts[5].strip()) > 0
            and parts[5].strip().isnumeric()
        ):
            chapterId = int(parts[5].strip())
            ambi = False
        # upstream supports a chapter id after the story slug too, but it does not
        # normally generate such urls -- only use it as a fallback
        if (
            ambi
            and len(parts) >= 7
            and parts[3] == "s"
            and len(parts[6].strip()) > 0
            and parts[6].strip().isnumeric()
        ):
            chapterId = int(parts[6].strip())
            ambi = False
        return FicId(self.ftype, str(storyId), chapterId, ambi)

    def create(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId, 1)

        # scrape fresh info
        data = self.scrape(fic.url)

        fic = self.parseInfoInto(fic, data["raw"])
        fic.upsert()

        chapter = fic.chapter(1)
        chapter.setHtml(data["raw"])
        chapter.upsert()

        return Fic.lookup((fic.id,))

    def extractContent(self, fic: Fic, html: str) -> str:
        lines = html.replace("\r", "\n").split("\n")
        parts: List[str] = []
        inStory = False
        for line in lines:
            if line.find("id='storytext'") != -1:
                inStory = True
            if inStory:
                if (
                    line.find("SELECT id=chap_select") != -1
                    or line.lower().find("<script") != -1
                ):
                    inStory = False
                    break
                parts += [line]
        return " ".join(parts)

    def getCurrentInfo(self, fic: Fic) -> Fic:
        # scrape fresh info
        data = self.scrape(self.constructUrl(fic.localId, 1))

        return self.parseInfoInto(fic, data["raw"])

    def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
        from bs4 import BeautifulSoup

        deletedFicText = "Story Not FoundUnable to locate story. Code 1."
        soup = BeautifulSoup(wwwHtml, "html5lib")
        profile_top = soup.find(id="profile_top")
        # story might've been deleted
        if profile_top is None:
            gui_warnings = soup.find_all("span", {"class": "gui_warning"})
            for gui_warning in gui_warnings:
                if gui_warning.get_text() == deletedFicText:
                    fic.ficStatus = FicStatus.abandoned
                    fic.upsert()
                    return fic

        text = profile_top.get_text()
        pt_str = str(profile_top)

        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")  # TODO: don't hard code?

        for b in profile_top.find_all("b"):
            b_class = b.get("class")
            if len(b_class) == 1 and b_class[0] == "xcontrast_txt":
                fic.title = b.get_text()
                break
        else:
            raise Exception(f"error: unable to find title:\n{pt_str}\n")

        fic.url = self.constructUrl(fic.localId, 1, fic.title)

        for div in profile_top.find_all("div"):
            div_class = div.get("class")
            if (
                div.get("style") == "margin-top:2px"
                and len(div_class) == 1
                and div_class[0] == "xcontrast_txt"
            ):
                fic.description = div.get_text()
                break
        else:
            raise Exception(f"error: unable to find description:\n{pt_str}\n")

        # default optional fields
        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        matcher = RegexMatcher(
            text,
            {
                "ageRating": ("Rated:\s+Fiction\s*(\S+)", str),
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

        match = re.search("Status:\s+(\S+)", text)
        if match is None:
            fic.ficStatus = FicStatus.ongoing
        else:
            status = match.group(1)
            if status == "Complete":
                fic.ficStatus = FicStatus.complete
            else:
                raise Exception(f"unknown status: {status}")

        for a in profile_top.find_all("a"):
            a_href = a.get("href")
            if a_href.startswith("/u/"):
                author = a.get_text()
                authorUrl = self.baseUrl + a_href
                authorId = a_href.split("/")[2]
                self.setAuthor(fic, author, authorUrl, authorId)
                break
        else:
            raise Exception(f"unable to find author:\n{text}")

        preStoryLinks = soup.find(id="pre_story_links")
        preStoryLinksLinks = preStoryLinks.find_all("a")
        for a in preStoryLinksLinks:
            href = a.get("href")
            hrefParts = href.split("/")

            # if it's a top level category
            if (
                len(hrefParts) == 3
                and len(hrefParts[0]) == 0
                and len(hrefParts[2]) == 0
            ):
                cat = hrefParts[1]
                if cat in fictionPressCategories:
                    continue  # skip categories
                raise Exception(f"unknown category: {cat}")

            # if it's a regular genre in some category
            if (
                len(hrefParts) == 4
                and len(hrefParts[0]) == 0
                and len(hrefParts[3]) == 0
            ):
                # ensure category is in our map
                if hrefParts[1] not in fictionPressCategories:
                    raise Exception(f"unknown category: {hrefParts[1]}")

                # ensure it's in our whitelist
                if hrefParts[2] not in fictionPressGenres:
                    util.logMessage(
                        f"FictionPressAdapter: unknown genre {hrefParts[2]}"
                    )
                    continue

                fic.add(Fandom.define(hrefParts[2]))
                continue

            util.logMessage(f"FictionPressAdapter: unknown genre {fic.id}: {href}")
            continue

        fic.upsert()

        chapterTitles = []
        if fic.chapterCount > 1:
            chapterSelect = soup.find(id="chap_select")
            chapterOptions = []
            if chapterSelect is not None:
                chapterOptions = chapterSelect.findAll("option")
            chapterTitles = [co.getText().strip() for co in chapterOptions]

        for cid in range(fic.chapterCount):
            ch = fic.chapter(cid + 1)
            ch.localChapterId = str(cid + 1)
            if len(chapterTitles) > cid:
                ch.title = util.cleanChapterTitle(chapterTitles[cid], cid + 1)
            elif fic.chapterCount == 1 and cid == 0:
                ch.title = fic.title
            ch.upsert()

        return fic

    def scrape(self, url: str) -> scrape.ScrapeMeta:
        return skitter.scrape(url)

    def softScrape(self, chapter: FicChapter) -> str:
        fic = chapter.getFic()

        curl = self.constructUrl(fic.localId, chapter.chapterId, None)
        # util.logMessage(f'FictionPressAdapter.scrape: {curl}')
        url = scrape.getLastUrlLike(curl)
        delay: float = 5
        if url is None:
            url = curl

        data = str(skitter.softScrape(url)["raw"])

        if data is None:
            raise Exception("unable to scrape? FIXME")
        if (
            data.lower().find("chapter not found.") != -1
            and data.lower().find("id='storytext'") == -1
        ):
            ts = scrape.getMostRecentScrapeTime(url)
            if ts is None:
                raise Exception("no most recent scrape time? FIXME")
            # if we last scraped more than half an hour ago rescrape
            if int(time.time()) - ts > (60 * 30):
                url = self.constructUrl(fic.localId, chapter.chapterId, None)
                data = self.scrape(url)["raw"]
        if data is None:
            raise Exception("unable to scrape? FIXME")

        if (
            data.lower().find("chapter not found.") != -1
            and data.lower().find("id='storytext'") == -1
        ):
            raise Exception(f"unable to find chapter content {url}")

        return data
