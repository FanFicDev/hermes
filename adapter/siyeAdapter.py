from typing import Optional
import re
import time
import urllib

from adapter.adapter import Adapter, edumpContent
from htypes import FicId, FicType
import scrape
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util


class SiyeAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(True, "https://www.siye.co.uk", "siye.co.uk", FicType.siye)
        self.baseStoryUrl = "https://www.siye.co.uk/viewstory.php"
        self.alternateBaseUrl = "https://www.siye.co.uk/siye"

    def constructUrl(self, lid: str, cid: Optional[int] = None) -> str:
        if cid is None:
            return f"{self.baseStoryUrl}?sid={lid}"
        return f"{self.baseStoryUrl}?sid={lid}&chapter={cid}"

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        url = url.replace("&textsize=0", "")
        url = url.replace("http://", "https://")
        url = url.replace("https://siye", "https://www.siye")
        if url.startswith(self.alternateBaseUrl):
            url = self.baseUrl + url[len(self.alternateBaseUrl) :]
        if not url.startswith(self.baseStoryUrl):
            return None

        leftover = url[len(self.baseStoryUrl) :]
        if not leftover.startswith("?"):
            return None
        leftover = leftover[1:]

        qs = urllib.parse.parse_qs(leftover)
        if "sid" not in qs or len(qs["sid"]) != 1:
            return None

        ficId = FicId(self.ftype, str(int(qs["sid"][0])))

        if "chapter" in qs and len(qs["chapter"]) == 1:
            ficId.chapterId = int(qs["chapter"][0])

        return ficId

    def create(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId)

        # scrape fresh info
        data = scrape.scrape(fic.url)

        edumpContent(data["raw"], "siye")

        fic = self.parseInfoInto(fic, data["raw"])
        fic.upsert()

        return Fic.lookup((fic.id,))

    def extractContent(self, fic: Fic, html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html5lib")
        notes = soup.find(id="notes")

        w95tables = soup.findAll("table", {"width": "95%"})
        if len(w95tables) != 3:
            raise Exception(f"wrong number of w95 tables: {len(w95tables)}")

        contentTable = w95tables[1]

        if notes is not None:
            return str(notes) + str(contentTable)
        return str(contentTable)

    def buildUrl(self, chapter: "FicChapter") -> str:
        if len(chapter.url.strip()) > 0:
            return chapter.url
        return self.constructUrl(chapter.getFic().localId, chapter.chapterId)

    def getCurrentInfo(self, fic: Fic) -> Fic:
        url = self.constructUrl(fic.localId)
        # scrape fresh info
        data = scrape.scrape(url)

        edumpContent("<!-- {} -->\n{}".format(url, data["raw"]), "siye_ec")
        return self.parseInfoInto(fic, data["raw"])

    def parseInfoInto(self, fic: Fic, html: str) -> Fic:
        from bs4 import BeautifulSoup

        html = html.replace("\r\n", "\n")
        soup = BeautifulSoup(html, "html.parser")

        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")  # TODO: don't hard code?

        w95tables = soup.findAll("table", {"width": "95%"})
        if len(w95tables) != 3:
            raise Exception(f"wrong number of w95 tables: {len(w95tables)}")

        ficInfoTable = w95tables[0]
        ficTitleH3 = ficInfoTable.find("h3")
        fic.title = ficTitleH3.get_text().strip()

        authorUrlMatch = re.search('"viewuser.php\?uid=(\d+)">([^<]*)<', html)
        if authorUrlMatch is None:
            raise Exception("could not locate author url")

        author = authorUrlMatch.group(2)
        authorId = authorUrlMatch.group(1)
        authorUrl = self.baseUrl + "/viewuser.php?uid=" + authorId

        self.setAuthor(fic, author, authorUrl, authorId)

        # TODO: this may miss multiline summaries :(
        summaryMatch = re.search(
            "<b>Summary:</b>((.|\r|\n)*)<b>Hitcount: </b>", html, re.MULTILINE
        )
        if summaryMatch is None:
            edumpContent(html, "siye_summary")
            raise Exception("could not locate summary")
        # alternatively: fic.description = "{no summary}" ?

        fic.description = summaryMatch.group(1).strip()

        fic.ageRating = "<unkown>"

        ageRatingMatch = re.search("<b>Rating:</b>(.*)<br>", html)
        if ageRatingMatch is not None:
            fic.ageRating = ageRatingMatch.group(1).strip()

        maxChapter = 0
        baseChapterHref = f"viewstory.php?sid={fic.localId}&chapter="
        singleChapterHref = f"viewstory.php?sid={fic.localId}&chapter=Array"
        isSingleChapterFic = False
        allAs = soup.find_all("a")
        for a in allAs:
            href = a.get("href")
            if href is None:
                continue
            if not href.startswith(baseChapterHref):
                continue
            if href.startswith(singleChapterHref):
                isSingleChapterFic = True
                maxChapter = max(1, maxChapter)
                continue
            cid = int(href[len(baseChapterHref) :])
            maxChapter = max(cid, maxChapter)

        fic.chapterCount = maxChapter

        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        fic.ficStatus = FicStatus.ongoing
        if html.find("Story is Complete"):
            fic.ficStatus = FicStatus.complete

        updatedOnPattern = re.compile("updated on (\d+).(\d+).(\d+)")
        minUpdate = util.parseDateAsUnix(int(time.time()), fic.fetched)
        maxUpdate = util.parseDateAsUnix("1970/01/01", fic.fetched)
        for year, month, day in re.findall(updatedOnPattern, html):
            date = f"{year}/{month}/{day}"
            dt = util.parseDateAsUnix(date, fic.fetched)

            minUpdate = min(minUpdate, dt)
            maxUpdate = max(maxUpdate, dt)

        if fic.published is None or fic.published.toUTS() > minUpdate:
            fic.published = OilTimestamp(minUpdate)
        if fic.updated is None or fic.updated.toUTS() < maxUpdate:
            fic.updated = OilTimestamp(maxUpdate)
        if fic.updated < fic.published:
            fic.updated = fic.published

        fic.wordCount = 0
        wordsPattern = re.compile("(\d+) words")
        for words in re.findall(wordsPattern, html):
            fic.wordCount += int(words)

        if fic.wordCount == 0 and isSingleChapterFic:
            try:
                fic.upsert()
                ch1 = fic.chapter(1)
                ch1.cache()
                chtml = ch1.html()
                if chtml is not None:
                    fic.wordCount = len(chtml.split())
            except:
                pass

        fic.add(Fandom.define("Harry Potter"))
        # TODO: chars/relationship?

        return fic
