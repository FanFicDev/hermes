from adapter.xenForoAdapter import XenForoAdapter
from htypes import FicType


class TheFanfictionForumAdapter(XenForoAdapter):
    def __init__(self) -> None:
        super().__init__(
            "https://thefanfictionforum.net/xenforo/index.php?",
            "thefanfictionforum.net",
            FicType.thefanfictionforum,
            "| The Fanfiction Forum",
            [],
            postContainer=["li", "article"],
        )
        self.defaultDelay = 30
