from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypeVar

if TYPE_CHECKING:
    from hermes import Hermes
import curses
import time

from htypes import FicId
from store import Fic, FicStatus, UserFic
import util
from view.htmlView import HtmlView
from view.widget import Widget

T = TypeVar("T", int, str)


class FicSelect(Widget):
    def __init__(self, parent: Optional["Hermes"], target: Optional[Fic] = None):
        self.parent = parent
        self.fics = Fic.list() if target is None else Fic.list({"id": target.id})
        self.list = self.fics
        self.idx = 0
        self.filter = ""
        self.width, self.height = 80, 24
        self.msg: Optional[Tuple[int, str]] = None
        self.__refilter(target)
        self._userFicCache: Dict[int, UserFic] = {}
        self._rebuildUserFicCache()

    def handleKey(self, key: int) -> bool:
        if key == 3:  # ctrl c
            if self.parent is not None:
                self.parent.quit()
            return True

        fic = None
        if len(self.list) > 0 and self.idx < len(self.list):
            fic = self.list[self.idx]

        if key == curses.KEY_DOWN:
            if self.idx < len(self.list) - 1:
                self.idx = (self.idx + 1) % len(self.list)
                return True
            return False
        if key == curses.KEY_UP:
            if self.idx == 0:
                return False
            self.idx = self.idx - 1
            return True
        if key == curses.KEY_HOME:
            self.idx = 0
            return True
        if key == curses.KEY_END:
            self.idx = len(self.list) - 1
            return True
        if key in {ord("\n"), ord("\r"), curses.KEY_ENTER, curses.KEY_RIGHT}:
            if len(self.list) == 0:
                ficId = FicId.parse(self.filter)
                fic = Fic.load(ficId)
                self.filter = ""
                self.fics = Fic.list()
                self.list = self.fics
                self.__refilter(fic)

                self.pushMessage(f'added fic "{fic.title}" ({fic.localId})')
            elif self.parent is not None:
                self.parent.selectFic(self.list[self.idx])
            return True

        if key == 4:  # ctrl d
            self.filter = ""
            self.list = self.fics
            self.__refilter(fic)
            return True

        # TODO: this is out of hand
        if (key >= ord(" ") and key <= ord("~")) and (
            (chr(key).isalnum())
            or ":/ .<>?&()=~".find(chr(key)) != -1
            or (len(self.filter) > 0 and key == ord("-"))
        ):
            self.appendToFilter(chr(key).lower())
            return True
        if key in {curses.KEY_BACKSPACE, 127} and len(self.filter) > 0:
            self.backspace()
            return True
        if key == curses.KEY_PPAGE:
            self.idx = max(0, self.idx - int(self.height / 3))
            return True
        if key == curses.KEY_NPAGE:
            self.idx = min(len(self.list) - 1, self.idx + int(self.height / 3))
            return True

        if fic is None:
            return True
        userFic = self.getUserFic(fic)

        if key == 21:  # ctrl u
            userFic.lastChapterViewed = 0
            userFic.update()
            self.pushMessage(f'marked "{fic.title}" no last chapter')
            return True
        if key == 1 and fic.chapterCount is not None:  # ctrl a
            userFic.readStatus = FicStatus.complete
            userFic.updateLastViewed(fic.chapterCount)
            userFic.updateLastRead(fic.chapterCount)
            for cid in range(1, fic.chapterCount + 1):
                chap = fic.chapter(cid).getUserFicChapter()
                if chap.readStatus == FicStatus.complete:
                    continue
                chap.readStatus = FicStatus.complete
                chap.update()
            self.pushMessage(f'marked "{fic.title}" all read')
            return True
        if key == ord("+"):
            if userFic.rating is None or userFic.rating < 0:
                userFic.rating = 0
            if userFic.rating < 9:
                userFic.rating += 1
                userFic.update()
                self.pushMessage(f'changed rating of "{fic.title}" => {userFic.rating}')
                return True
            return False
        if len(self.filter) == 0 and key == ord("-"):
            if userFic.rating is None:
                userFic.rating = 2
            if userFic.rating > 1:
                userFic.rating -= 1
                userFic.update()
                self.pushMessage(f'changed rating of "{fic.title}" => {userFic.rating}')
                return True
            return False

        if key == 6:  # ctrl f
            userFic.isFavorite = not userFic.isFavorite
            userFic.update()
            self.pushMessage(f'changed favorite status of "{fic.title}"')
            return True
        if key == 9:  # ctrl i
            fic.checkForUpdates()
            self.pushMessage(f'checked "{fic.title}" for updates')
            return True
        if key == 23:  # ctrl w
            fic.ficStatus = {
                FicStatus.ongoing: FicStatus.abandoned,
                FicStatus.abandoned: FicStatus.complete,
                FicStatus.complete: FicStatus.ongoing,
            }[FicStatus(fic.ficStatus)]
            fic.upsert()
            return True
        return False

    def getUserFic(self, fic: Fic) -> UserFic:
        if fic.id not in self._userFicCache:
            self._userFicCache[fic.id] = fic.getUserFic()
        return self._userFicCache[fic.id]

    def _rebuildUserFicCache(self) -> None:
        self._userFicCache = {uf.ficId: uf for uf in UserFic.select({"userId": 1})}

    def refresh(self) -> None:
        self.fics = Fic.list()
        self._rebuildUserFicCache()
        target = None
        if self.idx < len(self.list):
            target = self.list[self.idx]
        self.__refilter(target)
        self.pushMessage("refreshed fic list")

    def pushMessage(self, m: str) -> None:
        self.msg = (int(time.time()) + 5, m)

    def appendToFilter(self, c: str) -> None:
        self.filter += c
        fic = None
        if self.idx < len(self.list):
            fic = self.list[self.idx]
        self.__refilter(fic)

    def fcmp(self, rel: str, val: T, arg: T) -> bool:
        if rel == "=":
            return val == arg
        if rel == "<":
            return val < arg
        if rel == ">":
            return val > arg
        if rel == "~":
            return util.subsequenceMatch(str(val).lower(), str(arg).lower())
        if rel == ".":
            return str(val).lower().find(str(arg).lower()) > -1
        raise Exception(f"invalid relation: {rel}")

    def __refilter(self, target: Optional[Fic] = None, force: bool = False) -> None:
        self.__doRefilter(force)
        tidx = None
        if target is not None:
            for i in range(0, len(self.list)):
                if self.list[i].id == target.id:
                    tidx = i
                    break
        if tidx is not None:
            self.idx = tidx
        else:
            self.idx = max(0, min(self.idx, len(self.list) - 1))

    def __doRefilter(self, force: bool) -> None:
        if len(self.filter) < 1:
            return
        ficId = FicId.tryParse(self.filter)
        if ficId is not None:
            self.idx = 0
            self.list = []
            if ficId.ambiguous == False:
                fic = Fic.tryLoad(ficId)
                if fic is None:
                    fic = Fic.load(ficId)
                    self.fics = Fic.list()
                self.list = [fic]
            else:
                fic = Fic.tryLoad(ficId)
                if fic is not None:
                    self.list = [fic]
            return

        plain: List[str] = []
        tags: List[str] = []
        tagStarts = ["is:", "i:", ":"]
        for w in self.filter.split():
            isTag = False
            for tagStart in tagStarts:
                if w.startswith(tagStart):
                    tags += [w[len(tagStart) :]]
                    isTag = True
                    break
            if not isTag:
                plain += [w]

        # TODO: simplify fcmp tags
        favRel = None
        ratRel = None
        isNew = None
        isComplete = None
        authorRel = None
        fandomRel = None
        descRel = None
        titleRel = None
        for tag in tags:
            if len(tag) == 0:
                continue
            arg: str = ""
            rel: Optional[str] = None
            for prel in ["=", "<", ">", "~", "."]:
                if tag.find(prel) != -1:
                    ps = tag.split(prel)
                    if len(ps) != 2:
                        continue
                    tag = ps[0]
                    rel = prel
                    arg = ps[1]
                    break

            if "favorite".startswith(tag):
                if rel is not None and arg.isnumeric():
                    favRel = (rel, int(arg))
                else:
                    favRel = (">", 0)
            elif "rated".startswith(tag):
                if rel is not None and arg.isnumeric():
                    ratRel = (rel, int(arg))
                else:
                    ratRel = (">", 0)
            elif "new".startswith(tag):
                isNew = ("=", "new")
            elif "author".startswith(tag):
                if rel is not None:
                    authorRel = (rel, arg)
            elif "fandom".startswith(tag):
                if rel is not None:
                    fandomRel = (rel, arg)
            elif "complete".startswith(tag):
                isComplete = ("=", "complete")
            elif "description".startswith(tag):
                if rel is not None:
                    descRel = (rel, arg)
            elif "title".startswith(tag):
                if rel is not None:
                    titleRel = (rel, arg)

        self.pushMessage(
            "f:{}, r:{}, n:{}, c:{}, a:{}, f2:{} p:{}".format(
                favRel, ratRel, isNew, isComplete, authorRel, fandomRel, plain
            )
        )

        pfilter = " ".join(plain).lower()

        nfics: List[Fic] = []
        completelyRefilter = force or (self.filter[-1] == " " or self.filter[-1] == ":")

        # TODO FIXME bleh
        userFics = {uf.ficId: uf for uf in UserFic.select({"userId": 1})}

        for fic in self.fics if completelyRefilter else self.list:
            if fic.id not in userFics:
                userFics[fic.id] = UserFic.default((1, fic.id))
            userFic = userFics[fic.id]
            if favRel is not None or ratRel is not None or isNew:
                if favRel is not None:
                    if not self.fcmp(favRel[0], userFic.isFavorite, favRel[1]):
                        continue
                if ratRel is not None:
                    if not self.fcmp(ratRel[0], userFic.rating or -1, ratRel[1]):
                        continue
                if isNew is not None:
                    if userFic.lastChapterViewed != 0:
                        continue
            if descRel is not None:
                if not self.fcmp(descRel[0], fic.description or "", descRel[1]):
                    continue
            if titleRel is not None:
                if not self.fcmp(titleRel[0], fic.title or "", titleRel[1]):
                    continue
            if isComplete is not None and fic.ficStatus != FicStatus.complete:
                continue
            if authorRel is not None:
                if not self.fcmp(authorRel[0], fic.getAuthorName(), authorRel[1]):
                    continue
            if fandomRel is not None:
                ficFandoms = [fandom.name for fandom in fic.fandoms()]
                matchesFandom = False
                for fandom in ficFandoms:
                    if self.fcmp(fandomRel[0], fandom, fandomRel[1]):
                        matchesFandom = True
                        break
                if not matchesFandom:
                    continue

            ftext = f"{fic.localId} {fic.title} {fic.getAuthorName()} {fic.id}".lower()
            if util.subsequenceMatch(ftext, pfilter):
                nfics += [fic]
        self.list = nfics

    def backspace(self) -> None:
        fic = None
        if self.idx < len(self.list):
            fic = self.list[self.idx]
        self.filter = self.filter[:-1]
        self.list = self.fics
        self.__refilter(fic, True)

    def handleResize(self, maxX: int, maxY: int) -> None:
        self.width = maxX
        self.height = maxY

    def getHeader(self, idx: int, width: int) -> str:
        fic = self.list[idx]
        userFic = self.getUserFic(fic)
        onC = ""
        if (userFic.lastChapterViewed or 0) > 0 and (
            userFic.readStatus == FicStatus.ongoing
            or (userFic.lastChapterViewed or 0) < (fic.chapterCount or -1)
        ):
            onC = f"({userFic.lastChapterViewed}/{fic.chapterCount})"
        if width - 5 - len(onC) <= 0:
            onC = ""

        ficStatusIndicator = " "
        if fic.ficStatus == FicStatus.complete:
            ficStatusIndicator = "C"
        elif fic.ficStatus == FicStatus.abandoned:
            ficStatusIndicator = "A"

        title = fic.title or "[MISSING TITLE]"
        return "{:<{}}{} {}{}{}{}".format(
            util.filterUnicode(title[: width - 6 - len(onC)]),
            width - 5 - len(onC),
            onC,
            str(userFic.rating) if userFic.rating and userFic.rating >= 0 else " ",
            "*" if userFic.isFavorite else " ",
            "R" if userFic.readStatus == FicStatus.complete else " ",
            ficStatusIndicator,
        )

    def getAttr(self, idx: int) -> Any:
        fic = self.list[idx]
        userFic = self.getUserFic(fic)
        if userFic.isFavorite:
            return curses.color_pair(2)
        # TODO: actively reading?
        # return curses.color_pair(5)
        if userFic.readStatus == FicStatus.abandoned:
            return curses.color_pair(1)
        # TODO: import status?
        # return curses.color_pair(4)
        return curses.color_pair(0)

    def draw(self, y: int, x: int, text: str, attr: Any = None) -> bool:
        if y >= self.height or y < 0:
            return False
        if attr is None:
            self.scr.addstr(y, x, text)
        else:
            self.scr.addstr(y, x, text, attr)
        return True

    def repaint(self, stdscr: Any) -> None:
        self.scr = stdscr
        if self.width <= 10:
            return
        if len(self.list) < 1:
            self.drawFilter()
            return
        hmid = int(self.height / 3)
        if self.height > 60:
            hmid = int(self.height / 5)
        lm = int((self.width - 75) / 2) if self.width > 80 else 2
        tWidth = min(76, self.width - 4)

        for i in range(1, hmid + 1):
            if (self.idx - i) < 0:
                continue
            self.draw(
                hmid - i - 1,
                lm,
                self.getHeader(self.idx - i, tWidth),
                self.getAttr(self.idx - i),
            )

        fic = self.list[self.idx]
        lastUrl = fic.url or ""
        self.draw(hmid - 1, lm, "=" * tWidth)
        self.draw(hmid + 1, lm, "{:>{}}".format(lastUrl[:tWidth], tWidth))

        desc = HtmlView(fic.description or "{missing description}").text
        wdesc: List[str] = []
        for descLine in desc:
            if descLine == "<hr />":
                continue
            wdesc += util.wrapText(" " + descLine, tWidth)
        off = 1
        for i in range(min(5, len(wdesc))):
            if i == 4:
                wdesc[i] = wdesc[i][: tWidth - 3] + "..."
            self.draw(hmid + i + off + 1, lm, wdesc[i])

        self.draw(
            hmid + 7,
            lm,
            util.equiPad(
                [
                    f"chapters: {fic.chapterCount}",
                    f"{fic.getAuthorName()}",
                    f"words: {util.formatNumber(fic.wordCount or -1)}",
                ],
                tWidth,
            ),
        )
        updatedStr = fic.getUpdatedDateString()
        publishedStr = fic.getPublishedDateString()
        self.draw(
            hmid + 8,
            lm,
            util.equiPad(
                [f"published: {publishedStr}", str(fic.id), f"updated: {updatedStr}"],
                tWidth,
            ),
        )
        fandoms = [f.name for f in fic.fandoms()]
        if len(fandoms) == 0:
            self.draw(hmid + 9, lm, util.equiPad(["", "No Fandoms", ""], tWidth))
        elif len(fandoms) == 1:
            self.draw(hmid + 9, lm, util.equiPad(["", fandoms[0], ""], tWidth))
        elif len(fandoms) == 2:
            self.draw(
                hmid + 9, lm, util.equiPad(["", fandoms[0], fandoms[1], ""], tWidth)
            )
        else:
            self.draw(hmid + 9, lm, util.equiPad(fandoms, tWidth))
        self.draw(hmid + 10, lm, "=" * tWidth)
        off += 10 - 1

        for i in range(1, self.height - hmid - off):
            if (self.idx + i) >= len(self.list):
                continue
            self.draw(
                hmid + i + off,
                lm,
                self.getHeader(self.idx + i, tWidth),
                self.getAttr(self.idx + i),
            )

        cursor = f">  {self.getHeader(self.idx, tWidth - 1)} <"

        attr = self.getAttr(self.idx)
        attr = attr if attr is not None else curses.color_pair(1)
        attr |= curses.A_UNDERLINE
        self.draw(hmid, lm - 2, cursor, attr)

        self.drawMessage()
        self.drawFilter()

    def drawMessage(self) -> None:
        if self.msg is None:
            return
        expires = self.msg[0]
        if expires < int(time.time()):
            self.msg = None
            return
        text = "  {:<{}}".format(self.msg[1], self.width - 2)
        self.draw(0, 0, text, curses.color_pair(4))

    def drawFilter(self) -> None:
        stext = f"({self.idx + 1:>3}/{len(self.list):>3})"
        ltext = "> " + self.filter

        self.draw(
            self.height - 1,
            0,
            util.equiPad(["", stext], self.width - 1),
            curses.color_pair(4),
        )

        if len(stext + ltext) >= self.width - 2:
            left = self.width - 2 - len(stext) - 3
            ltext = ">~" + self.filter[len(self.filter) - left :]

        self.draw(self.height - 1, 0, ltext, curses.color_pair(4))
