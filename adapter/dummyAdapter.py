from adapter.adapter import ManualAdapter
from htypes import FicType


class DummyAdapter(ManualAdapter):
    def __init__(self) -> None:
        super().__init__("dummy", "dummyXYZ", FicType.dummy)
