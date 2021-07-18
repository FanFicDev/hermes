from htypes import FicType
from adapter.adapter import ManualAdapter


class DummyAdapter(ManualAdapter):
	def __init__(self) -> None:
		super().__init__('dummy', 'dummyXYZ', FicType.dummy)
