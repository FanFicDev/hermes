from adapter.xenForoAdapter import *


class BulbagardenAdapter(XenForoAdapter):
    def __init__(self) -> None:
        super().__init__(
            "https://forums.bulbagarden.net/index.php?",
            "forums.bulbagarden.net",
            FicType.bulbagarden,
            "| Bulbagarden Forums",
            [],
            postContainer=["li", "article"],
        )
        self.defaultDelay = 30
