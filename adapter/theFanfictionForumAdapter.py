from adapter.xenForoAdapter import *


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
