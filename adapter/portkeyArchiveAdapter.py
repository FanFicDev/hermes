from typing import Optional

from adapter.adapter import ManualAdapter
from htypes import FicId, FicType


class PortkeyArchiveAdapter(ManualAdapter):
    def __init__(self) -> None:
        super().__init__(
            "http://www.portkey-archive.org/story",
            "portkey-archive.org",
            FicType.portkeyarchive,
        )

    def tryParseUrl(self, url: str) -> Optional[FicId]:
        parts = url.split("/")
        httpOrHttps = parts[0] == "https:" or parts[0] == "http:"
        if len(parts) < 4:
            return None
        if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
            return None
        if parts[3] != "story":
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
