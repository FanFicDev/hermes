from typing import Optional

from adapter.adapter import Adapter, edumpContent
from htypes import FicId, FicType
from store import Fic, FicChapter


class FictionAlleyAdapter(Adapter):
    def __init__(self) -> None:
        super().__init__(
            False,
            "http://www.fictionalley.org/",
            "fictionalley.org",
            FicType.fictionalley,
        )

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        if not url.startswith(self.baseUrl):
            return None

        # by default, we simply try to look up the url in existing chapters or fics
        chaps = FicChapter.select({"url": url})
        if len(chaps) == 1:
            fic = Fic.get((chaps[0].ficId,))
            if fic is not None:
                ftype = FicType(fic.sourceId)
                return FicId(ftype, fic.localId, chaps[0].chapterId, False)

        fics = Fic.select({"url": url})
        if len(fics) == 1:
            ftype = FicType(fics[0].sourceId)
            return FicId(ftype, fics[0].localId)

        leftover = url[len(self.baseUrl) :]
        if not leftover.endswith(".html"):
            return None

        ps = leftover.split("/")
        if len(ps) != 3 or ps[0] != "authors":
            return None

        author = ps[1]
        storyId = ps[2]
        suffixes = ["01a.html", ".html"]
        for suffix in suffixes:
            if storyId.endswith(suffix):
                storyId = storyId[: -len(suffix)]

        # note: seems to be safe to lowercase these
        _lid = (author + "/" + storyId).lower()
        # print(lid)
        # make lid author/story ?

        # TODO: we need some sort of local lid mapping...
        raise NotImplementedError()

    def extractContent(self, fic: Fic, html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        normalDiv = soup.find("div", {"name": "Normal"})
        if normalDiv is None:
            edumpContent(html, "fa_ec")
            raise Exception("unable to find normalDiv, e-dumped")

        return str(normalDiv)

    # TODO: may need to go to author page for some info?
