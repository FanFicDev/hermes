from typing import Dict, List, Optional, Set
import datetime
import re
import time
import urllib

from adapter.adapter import Adapter, edumpContent
from adapter.regex_matcher import RegexMatcher
from htypes import FicId, FicType
import scrape
from store import Fandom, Fic, FicChapter, FicStatus, Language, OilTimestamp
import util
from view import HtmlView


class AdultFanfictionMeta:
    def __init__(self) -> None:
        self.title: Optional[str] = None
        self.url: Optional[str] = None
        self.author: Optional[str] = None
        self.authorId: Optional[str] = None
        self.authorUrl: Optional[str] = None
        self.published: Optional[int] = None
        self.updated: Optional[int] = None
        self.reviewCount = -1
        self.views = -1
        self.description: Optional[str] = None
        self.ficStatus = FicStatus.ongoing
        self.chapterCount: int = -1
        self.tags: Set[str] = set()
        self.fandoms: List[str] = []
        self.localId: Optional[str] = None
        self.archive: Optional[str] = None
        self.storyNo: Optional[str] = None
        self.located: Optional[str] = None
        self.chars: List[str] = []

    def isNewerThan(self, rhs: "AdultFanfictionMeta") -> bool:
        assert self.updated is not None and rhs.updated is not None
        if self.updated > rhs.updated or self.chapterCount > rhs.chapterCount:
            return True
        if self.views > rhs.views or self.reviewCount > rhs.reviewCount:
            return True
        return False

    def setTags(self, tags: str) -> None:
        desc = HtmlView(tags).text
        res: str = ""
        for dline in desc:
            w = util.wrapText(dline, 78)
            for line in w:
                if line.strip() == "<hr />":
                    continue
                res += line
        res = res.strip()
        res = res.replace("*Content Tags :* ", "")
        res = util.filterUnicode(res)
        self.tags = set(res.strip().split())

    def info(self) -> None:
        chapterInfo = f"[{self.chapterCount:>2} chapters]"
        # TODO: look up more info if it's already been added?
        # if fic.lastChapterRead == fic.chapterCount:
        # chapterInfo = '[completely read, {:>2} chapters]'.format(fic.chapterCount)
        # elif fic.lastChapterViewed > 0:
        # chapterInfo = '[on chapter {:>2} of {:>2}]'.format(
        # fic.lastChapterViewed, fic.chapterCount)

        twidth = 80
        einfo = f"({self.localId:>8})"
        rhead = "".join(["C" if self.ficStatus == FicStatus.complete else "I"])

        title = self.title or "[MISSING TITLE]"
        title = title[: twidth - len(rhead) - 3]  # abbreviate

        print("{:<{}} {}".format('"' + title + '"', twidth - len(rhead) - 1, rhead))

        print(
            util.equiPad(
                [
                    f"{self.author}",
                    chapterInfo,
                ],
                twidth,
            )
        )

        if len(self.fandoms) > 0:
            print(f"    fandoms: {self.fandoms}")
        if len(self.tags) > 0:
            print(f"    tags: {self.tags}")
        if len(self.chars) > 0:
            print(f"    chars: {self.chars}")
        print(f"      loc: {self.located}")

        desc = HtmlView(self.description or "{no description}").text
        for dline in desc:
            w = util.wrapText(dline, 78)
            for line in w:
                if line.strip() == "<hr />":
                    continue
                print(f"  {line}")
            print("")

        assert self.updated is not None and self.published is not None
        updated = datetime.date.fromtimestamp(int(self.updated))
        updatedStr = updated.strftime("%m/%d/%Y")
        published = datetime.date.fromtimestamp(int(self.published))
        publishedStr = published.strftime("%m/%d/%Y")
        print(
            util.equiPad(
                [f"published: {publishedStr}", f"updated: {updatedStr}"], twidth
            )
        )

        print(f"  {self.url}")
        print("{:>{}}".format(einfo, twidth))
        print("")


class AdultFanfictionAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(
            True,
            "http://adult-fanfiction.org",
            "adult-fanfiction.org",
            FicType.adultfanfiction,
        )
        self.baseStoryUrl = "http://{}.adult-fanfiction.org/story.php?no={}"

    def constructUrl(self, storyId: str, chapterId: Optional[int] = None) -> str:
        archive = storyId.split("/")[0]
        storyNo = storyId.split("/")[1]
        url = self.baseStoryUrl.format(archive, storyNo)
        if chapterId is not None:
            url += f"&chapter={chapterId}"
        return url

    def buildUrl(self, chapter: "FicChapter") -> str:
        if chapter.fic is None:
            chapter.fic = Fic.lookup((chapter.ficId,))
        return self.constructUrl(chapter.fic.localId, chapter.chapterId)

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        parts = url.split("/")
        httpOrHttps = parts[0] == "https:" or parts[0] == "http:"
        if len(parts) < 4:
            return None
        if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
            return None
        if not parts[3].startswith("story.php?"):
            return None

        leftover = parts[3].split("?")[-1]

        qs = urllib.parse.parse_qs(leftover)
        if "no" not in qs or len(qs["no"]) != 1:
            return None

        storyNumber = int(qs["no"][0])
        archive = parts[2].split(".")[0]
        lid = f"{archive}/{storyNumber}"

        ficId = FicId(self.ftype, lid)

        if "chapter" in qs and len(qs["chapter"]) == 1:
            ficId.chapterId = int(qs["chapter"][0])

        return ficId

    def create(self, fic: Fic) -> Fic:
        fic.url = self.constructUrl(fic.localId, 1)

        # scrape fresh info
        data = scrape.softScrape(fic.url)
        if data is None:
            raise Exception("unable to scrape? FIXME")

        fic = self.parseInfoInto(fic, data)
        fic.upsert()

        chapter = fic.chapter(1)
        chapter.setHtml(data)
        chapter.localChapterId = str(1)
        chapter.url = self.constructUrl(fic.localId, 1)
        chapter.upsert()

        return Fic.lookup((fic.id,))

    def extractContent(self, fic: Fic, html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html5lib")
        tables = soup.findAll("table", {"width": "100%"})
        if len(tables) != 5:
            edumpContent(html, "aff")
            raise Exception(f"table count mismatch: {len(tables)}")
        ficTable = tables[2]
        trs = ficTable.findAll("tr")

        return str(trs[5])

    def getCurrentInfo(self, fic: Fic) -> Fic:
        # scrape fresh info
        data = scrape.scrape(self.constructUrl(fic.localId, 1))["raw"]

        return self.parseInfoInto(fic, data)

    def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
        from bs4 import BeautifulSoup

        archive = fic.localId.split("/")[0]
        storyNo = fic.localId.split("/")[1]

        soup = BeautifulSoup(wwwHtml, "html5lib")

        titleH2 = soup.find("a", {"href": f"/story.php?no={storyNo}"})
        fic.title = str(titleH2.getText())

        membersUrl = "http://members.adult-fanfiction.org/profile.php?no="
        memberLink = soup.find(
            lambda t: (
                t.name == "a"
                and t.has_attr("href")
                and t.get("href") is not None
                and (t.get("href").startswith(membersUrl))
            )
        )

        author = memberLink.getText()
        authorId = memberLink.get("href")[len(membersUrl) :]
        authorUrl = memberLink.get("href")
        self.setAuthor(fic, author, authorUrl, authorId)

        # TODO
        fic.ficStatus = FicStatus.ongoing

        fic.fetched = OilTimestamp.now()
        fic.languageId = Language.getId("English")  # TODO: don't hard code?

        fic.url = self.constructUrl(fic.localId, 1)

        # TODO: description is on search page
        if fic.description is None:
            fic.description = "TODO: on the search page?"

        # default optional fields
        fic.reviewCount = 0
        fic.favoriteCount = 0
        fic.followCount = 0

        fic.ageRating = "M"

        # TODO
        if fic.published is None:
            fic.published = OilTimestamp.now()
        if fic.updated is None:
            fic.updated = fic.published

        chapterDropdown = soup.find("div", {"class": "dropdown-content"})
        chapterLinks = chapterDropdown.findAll("a")
        oldChapterCount = fic.chapterCount
        fic.chapterCount = len(chapterLinks)

        if fic.wordCount is None:
            fic.wordCount = 0
        fic.upsert()

        wordCount = 0
        for cid in range(1, fic.chapterCount + 1):
            chapterContent = scrape.softScrape(self.constructUrl(fic.localId, cid))
            chapter = fic.chapter(cid)
            if chapterContent is not None:
                chapter.setHtml(chapterContent)
            chapter.localChapterId = str(cid)
            chapter.url = self.constructUrl(fic.localId, cid)

            chapter.title = chapterLinks[cid - 1].getText().strip()
            if chapter.title is not None:
                chapter.title = util.cleanChapterTitle(chapter.title, cid)

            chapter.upsert()
            if chapterContent is not None:
                wordCount += len(chapterContent.split())

        fic.wordCount = wordCount

        if oldChapterCount is not None and oldChapterCount < fic.chapterCount:
            fic.updated = OilTimestamp.now()  # TODO
        fic.upsert()

        storyUrl = self.constructUrl(fic.localId, chapterId=None)

        # more metadata from search page
        searchUrl = (
            "http://{}.adult-fanfiction.org/search.php?"
            + "auth={}&title={}&summary=&tags=&cats=0&search=Search"
        )
        searchUrl = searchUrl.format(archive, author, fic.title.replace(" ", "+"))
        data = scrape.scrape(searchUrl)["raw"]

        metas = self.extractSearchMetadata(data)

        # fallback to pure author search
        if storyUrl not in metas:
            searchUrl = (
                "http://{}.adult-fanfiction.org/search.php?"
                + "auth={}&title=&summary=&tags=&cats=0&search=Search"
            )
            searchUrl = searchUrl.format(archive, author)
            data = scrape.scrape(searchUrl)["raw"]
            metas = self.extractSearchMetadata(data)

        if storyUrl not in metas:
            raise Exception("cannot find search metadata")

        meta = metas[storyUrl]

        assert meta.published is not None and meta.updated is not None
        fic.published = OilTimestamp(meta.published)
        fic.updated = OilTimestamp(meta.updated)

        fic.reviewCount = meta.reviewCount
        fic.favoriteCount = meta.views  # TODO

        fic.ficStatus = meta.ficStatus

        assert meta.description is not None
        fic.description = meta.description
        assert fic.description is not None
        if len(meta.tags) > 0:
            fic.description += "\n<hr />\nContent Tags: " + " ".join(meta.tags)

        for fan in meta.fandoms:
            fic.add(Fandom.define(fan))

        return fic

    def extractSearchMetadata(
        self, html: str, metas: Optional[Dict[str, AdultFanfictionMeta]] = None
    ) -> Dict[str, AdultFanfictionMeta]:
        from bs4 import BeautifulSoup

        if metas is None:
            metas = {}
        archiveFandomMap = {
            "naruto": "Naruto",
            "hp": "Harry Potter",
            "xmen": "X-Men",
        }
        locatedFandomMap = [
            ("Mass Effect", "Mass Effect"),
            ("Metroid", "Metroid"),
            ("Pokemon", "Pokemon"),
            ("Sonic", "Sonic"),
            ("Witcher 3: Wild Hunt", "Witcher"),
        ]
        chars = [
            'Harry', 'Hermione', 'Snape', 'Draco', 'Sirius', 'Remus', 'Lucius', 'Ron',
            'Voldemort', 'Ginny', 'Charlie', 'Lily', 'Scorpius', 'James', 'George',
            'Fred', 'Narcissa', 'Blaise', 'Bill', 'Luna', 'Albus', 'Severus',
            'Fenrir', 'Tonks', 'Rose', 'Neville', 'Cho', 'Cedric', 'Tom', 'Seamus',
            'Pansy', 'Bellatrix', 'Viktor', 'Percy', 'Dudley', 'McGonagall',
            'Lavendar', 'Dumbledore', 'Naruto', 'Sasuke', 'Kakashi', 'Iruka',
            'Sakura', 'Itachi', 'Gaara', 'Shikamaru', 'Neji', 'Rock Lee', 'Hinata',
            'Ino', 'Shino', 'Danzo'
        ]  # fmt: skip

        spaceSqeeezeRe = re.compile("\s+")

        searchSoup = BeautifulSoup(html, "html5lib")
        resultTables = searchSoup.findAll("table", {"width": "90%"})
        for resultTable in resultTables:
            meta = AdultFanfictionMeta()

            links = resultTable.findAll("a")
            titleLink = links[0]
            meta.title = titleLink.getText()
            meta.url = titleLink.get("href")

            authorLink = links[1]
            meta.author = authorLink.getText().strip()
            meta.authorUrl = authorLink.get("href").strip()
            assert meta.authorUrl is not None
            meta.authorId = meta.authorUrl.split("=")[-1]

            trs = resultTable.findAll("tr")

            publishedText = trs[0].getText()
            RegexMatcher(
                publishedText,
                {
                    "published": ("Published\s+:\s+(.+)", str),
                },
            ).matchAll(meta)
            assert meta.published is not None
            meta.published = util.parseDateAsUnix(meta.published, int(time.time()))

            extendedMetadata = trs[1].getText()
            util.logMessage(extendedMetadata, "tmp_e_meta_aff.log")
            # TODO: dragon prints are actually views, not followCount/favoriteCount
            RegexMatcher(
                extendedMetadata,
                {
                    "chapterCount": ("Chapters\s*:\s*(\d+)", int),
                    "updated": ("Updated\s+:\s+(.+?)-:-", str),
                    "reviewCount?": ("Reviews\s+:\s+(\d+)", int),
                    "views?": ("Dragon prints\s+:\s+(\d+)", int),
                    "located?": ("Located\s*:\s*(.*)", str),
                },
            ).matchAll(meta)
            assert meta.updated is not None
            meta.updated = util.parseDateAsUnix(meta.updated, int(time.time()))

            meta.description = str(trs[2])
            meta.description = util.filterUnicode(meta.description)
            meta.description = spaceSqeeezeRe.sub(" ", meta.description)

            meta.setTags(str(trs[3]))

            if "COMPLETE" in meta.tags or "Complete." in meta.tags:
                meta.ficStatus = FicStatus.complete

            assert meta.url is not None
            ficId = FicId.tryParseUrl(meta.url)
            assert ficId is not None
            meta.localId = ficId.localId
            meta.archive = meta.localId.split("/")[0]
            meta.storyNo = meta.localId.split("/")[1]
            if meta.archive.lower() in archiveFandomMap:
                meta.fandoms += [archiveFandomMap[meta.archive.lower()]]

            meta.located = meta.located or ""
            loclow = meta.located.lower()

            for locFan in locatedFandomMap:
                if loclow.endswith(locFan[0].lower()):
                    meta.fandoms += [locFan[1]]

            for c1 in chars:
                for c2 in chars:
                    if loclow.endswith(f"{c1}/{c2}".lower()):
                        meta.chars += [c1, c2]

            # TODO: try parse category, get chars
            # meta.info()

            if meta.url not in metas or meta.isNewerThan(metas[meta.url]):
                metas[meta.url] = meta

        return metas
