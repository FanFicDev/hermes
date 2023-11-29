from typing import Optional
import re
import urllib
import urllib.parse

from adapter.adapter import Adapter, edumpContent
from htypes import FicId, FicType
import scrape
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util


class SugarQuillAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(
            True, "http://www.sugarquill.net", "sugarquill.net", FicType.sugarquill
        )
        self.baseStoryUrl = self.baseUrl + "/read.php"

    def constructUrl(self, lid: str, cid: Optional[int] = None) -> str:
        if cid is None:
            cid = 1
        return f"{self.baseStoryUrl}?storyid={lid}&chapno={cid}"

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        if not url.startswith(self.baseStoryUrl):
            return None

        leftover = url[len(self.baseStoryUrl) :]
        if not leftover.startswith("?"):
            return None
        leftover = leftover[1:]

        qs = urllib.parse.parse_qs(leftover)
        if "storyid" not in qs or len(qs["storyid"]) != 1:
            return None

        assert qs["storyid"][0].isnumeric()
        ficId = FicId(self.ftype, qs["storyid"][0])

        if "chapno" in qs and len(qs["chapno"]) == 1:
            ficId.chapterId = int(qs["chapno"][0])

        return ficId

    def create(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId)

        # scrape fresh info
        data = scrape.scrape(fic.url)

        edumpContent(data["raw"], "sugarquill")

        fic = self.parseInfoInto(fic, data["raw"])
        fic.upsert()

        return Fic.lookup((fic.id,))

    def extractContent(self, fic: Fic, html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html5lib")
        content = soup.findAll("div", {"class": "Section1"})
        if len(content) != 1:
            content = soup.findAll("td", {"class": "content_pane"})
        if len(content) != 1:
            raise Exception(f"unable to find content section: {fic.url}")

        content = content[0]

        return str(content)

    def buildUrl(self, chapter: "FicChapter") -> str:
        if len(chapter.url.strip()) > 0:
            return chapter.url
        return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

    def getCurrentInfo(self, fic: Fic) -> Fic:
        url = self.constructUrl(fic.localId)
        # scrape fresh info
        data = scrape.scrape(url)

        edumpContent("<!-- {} -->\n{}".format(url, data["raw"]), "sugarquill_ec")
        return self.parseInfoInto(fic, data["raw"])

    def parseInfoInto(self, fic: Fic, html: str) -> Fic:
        from bs4 import BeautifulSoup

        html = html.replace("\r\n", "\n")
        soup = BeautifulSoup(html, "html.parser")

        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")  # TODO: don't hard code?

        infoPane = soup.findAll("td", {"class": "info2_pane"})
        if len(infoPane) != 1:
            raise Exception(f"unable to find info2_pane: {fic.url}")
        infoPane = infoPane[0]

        authorHrefPrefix = "index.php?action=profile&id="
        authorLinks = infoPane.findAll("a")
        authorUrl = None
        for authorLink in authorLinks:
            if not authorLink.get("href").startswith(authorHrefPrefix):
                continue

            authorUrl = self.baseUrl + "/" + authorLink.get("href")
            author = authorLink.getText()
            authorLocalId = authorLink.get("href")[len(authorHrefPrefix) :]

            self.setAuthor(fic, author, authorUrl, authorLocalId)
            break
        else:
            raise Exception(f"unable to find author: {fic.url}")

        titleMatch = re.search(
            "<b>Story</b>:((.|\r|\n)*)<b>Chapter</b>:", str(infoPane), re.MULTILINE
        )
        if titleMatch is None:
            edumpContent(str(infoPane), "sugarquill_title")
            raise Exception("could not locate title")

        fic.title = titleMatch.group(1).replace("&nbsp;", " ").strip()

        chapterOptions = infoPane.findAll("option")
        chapterTitles = {}
        for chapterOption in chapterOptions:
            cid = int(chapterOption.get("value"))
            chapterTitles[cid] = chapterOption.getText().strip()
        fic.chapterCount = len(chapterOptions)

        fic.ageRating = "<unkown>"  # TODO
        fic.favoriteCount = 0
        fic.followCount = 0

        fic.ficStatus = FicStatus.ongoing  # TODO: no uniform way to detect?

        authorProfileHtml = scrape.scrape(authorUrl)["raw"]
        authorProfileHtml = authorProfileHtml.replace("\r", "")
        authorSoup = BeautifulSoup(authorProfileHtml, "html5lib")

        storyTables = authorSoup.findAll("table", {"width": "90%"})
        ourStoryTable = None
        for storyTable in storyTables:
            storyId = None
            for a in storyTable.findAll("a"):
                if not a.get("href").startswith("read.php?storyid="):
                    continue
                storyId = a.get("href")[len("read.php?storyid=") :]
                storyId = storyId[: storyId.find("&")]
                storyId = str(int(storyId))
            if storyId is None:
                continue
            if storyId != str(fic.localId):
                continue
            ourStoryTable = storyTable
        if ourStoryTable is None:
            raise Exception(f"unable to find story table: {fic.localId} {authorUrl}")

        trs = ourStoryTable.findAll("tr")
        if len(trs) != 3:
            raise Exception(
                f"ourStoryTable does not have 3 trs: {fic.localId} {authorUrl}"
            )

        fic.description = trs[1].find("td").getText().strip()

        reviewsMatch = re.search(
            "\( Reviews: <a[^>]*>(\\d+)</a> \)</td>", str(trs[0]), re.MULTILINE
        )
        if reviewsMatch is None:
            edumpContent(str(trs[0]), "sugarquill_reviews")
            raise Exception("could not locate reviews")

        fic.reviewCount = int(reviewsMatch.group(1).strip())

        updatedMatch = re.search("Last updated (\\d+/\\d+/\\d+)", str(trs[2]))
        if updatedMatch is None:
            edumpContent(str(trs[2]), "sugarquill_updated")
            raise Exception("could not locate last updated")

        fic.updated = OilTimestamp(
            util.parseDateAsUnix(updatedMatch.group(1), fic.fetched)
        )
        if fic.published is None:
            fic.published = fic.updated

        fic.wordCount = 0
        fic.upsert()

        for cid in range(fic.chapterCount):
            ch = fic.chapter(cid + 1)
            ch.localChapterId = str(cid + 1)
            ch.title = chapterTitles[cid + 1]
            ch.cache()
            ch.upsert()
            chtml = ch.html()
            if chtml is not None:
                fic.wordCount += len(chtml.split())

        fic.add(Fandom.define("Harry Potter"))
        # TODO: chars/relationship?

        return fic
