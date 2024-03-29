from adapter.xenForoAdapter import XenForoAdapter
from htypes import FicType


class QuestionableQuestingAdapter(XenForoAdapter):
    def __init__(self) -> None:
        super().__init__(
            "https://forum.questionablequesting.com/",
            "questionablequesting.com",
            FicType.questionablequesting,
            "| Questionable Questing",
            [
                ("//questionablequesting.com", "//forum.questionablequesting.com"),
                ("http://", "https://"),
            ],
        )
        self.defaultDelay = 30
        self.postsPerPage = 30
