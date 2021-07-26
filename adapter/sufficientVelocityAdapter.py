from htypes import FicType
from adapter.xenForoAdapter import XenForoAdapter


class SufficientVelocityAdapter(XenForoAdapter):
	def __init__(self) -> None:
		super().__init__(
			'https://forums.sufficientvelocity.com/',
			'sufficientvelocity.com',
			FicType.sufficientvelocity,
			'| Sufficient Velocity', [
				('//sufficientvelocity.com', '//forums.sufficientvelocity.com'),
				(
					'directforums.sufficientvelocity.com/',
					'forums.sufficientvelocity.com/'
				), ('http://', 'https://')
			],
			postContainer=['li', 'article']
		)
