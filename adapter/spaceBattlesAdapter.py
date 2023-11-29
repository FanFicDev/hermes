from adapter.xenForoAdapter import XenForoAdapter
from htypes import FicType


class SpaceBattlesAdapter(XenForoAdapter):
	def __init__(self) -> None:
		super().__init__(
			'https://forums.spacebattles.com/',
			'spacebattles.com',
			FicType.spacebattles,
			'| SpaceBattles Forums', [
				('//spacebattles.com', '//forums.spacebattles.com'),
				('http://', 'https://')
			],
			postContainer=['li', 'article']
		)
