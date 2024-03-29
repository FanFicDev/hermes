from adapter.wordpressAdapter import WordpressAdapter
from htypes import FicType


class WanderingInnAdapter(WordpressAdapter):
    def __init__(self) -> None:
        # https://wanderinginn.com/table-of-contents/
        super().__init__(
            "https://wanderinginn.com",
            "wanderinginn.com",
            FicType.wanderinginn,
            "The Wandering Inn",
            "The Wandering Inn",
            "M",
            "pirate aba",
            "https://www.patreon.com/user?u=4240617",
            """
An inn is a place to rest, a place to talk and share stories, or a place to find adventures, a starting ground for quests and legends.

In this world, at least. To Erin Solstice, an inn seems like a medieval relic from the past. But here she is, running from Goblins and trying to survive in a world full of monsters and magic. She’d be more excited about all of this if everything wasn’t trying to kill her.

But an inn is what she found, and so that’s what she becomes. An innkeeper who serves drinks to heroes and monsters–

Actually, mostly monsters. But it’s a living, right?

This is the story of the Wandering Inn.""",
            (
                '<a href=[\'"]https://wanderinginn[^\'"]*[\'"]>\s*(<span style="float:right;">|)\s*(Last|Previous|Next)\s+Chapter\s*(</span>|)\s*</a>',
                "",
            ),
        )
