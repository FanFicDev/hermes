from adapter.xenForoAdapter import *


class FanficParadiseSFWAdapter(XenForoAdapter):
	def __init__(self) -> None:
		super().__init__(
			'https://www.fanficparadise.com/fpforum-sfw/index.php?',
			'fanficparadise.com/fpforum-sfw',
			FicType.fanficparadisesfw,
			'| Fanfic Paradise SFW', [],
			postContainer=['li', 'article']
		)
		self.defaultDelay = 30


class FanficParadiseNSFWAdapter(XenForoAdapter):
	def __init__(self) -> None:
		super().__init__(
			'https://www.fanficparadise.com/fpforum-nsfw/index.php?',
			'fanficparadise.com/fpforum-nsfw',
			FicType.fanficparadisensfw,
			'| Fanfic Paradise NSFW', [],
			postContainer=['li', 'article']
		)
		self.defaultDelay = 30
