from typing import Optional

from adapter.wordpressAdapter import WordpressAdapter
from htypes import FicType
from store import FicChapter


class ParahumansAdapter(WordpressAdapter):
	def __init__(self) -> None:
		# https://www.parahumans.net/table-of-contents/
		super().__init__(
			'https://www.parahumans.net', 'parahumans.net', FicType.parahumans,
			'Ward', 'Worm', 'M', 'Wildbow',
			'https://www.parahumans.net/support-wildbow', '''
The unwritten rules that govern the fights and outright wars between ‘capes’ have been amended: everyone gets their second chance.  It’s an uneasy thing to come to terms with when notorious supervillains and even monsters are playing at being hero.  The world ended two years ago, and as humanity straddles the old world and the new, there aren’t records, witnesses, or facilities to answer the villains’ past actions in the present.  One of many compromises, uneasy truces and deceptions that are starting to splinter as humanity rebuilds.

None feel the injustice of this new status quo or the lack of established footing more than the past residents of the parahuman asylums.  The facilities hosted parahumans and their victims, but the facilities are ruined or gone; one of many fragile ex-patients is left to find a place in a fractured world.  She’s perhaps the person least suited to have anything to do with this tenuous peace or to stand alongside these false heroes.  She’s put in a position to make the decision: will she compromise to help forge what they call, with dark sentiment, a second golden age?  Or will she stand tall as a gilded dark age dawns?''',
			(
				"""<a href=['\"](https?://(www.)parahumans.net[^'\"]*|[^\'" >]+)['\"]>(Last|Previous|Next) Chapter</a>""",
				''
			)
		)

		self.urlFixups = {
			self.canonizeUrl('/2018/11/24/interlude-10-x'):
				None,
			self.canonizeUrl('/2018/12/11/interlude-10-y'):
				None,
			self.canonizeUrl('/2019/04/27/black-13-8'):
				self.canonizeUrl('/2019/04/30/black-13-x'),
		}

		self.titleFixups = {
			'(Tats)': ('10.x', '10.x (Tats)'),
			'(Boy in the shell)': ('10.y', '10.y (Boy in the shell)'),
		}

	def softScrape(self, chapter: FicChapter) -> Optional[str]:
		import scrape
		html = scrape.softScrape(chapter.url)
		if html is None:
			return html
		# TODO well this is a nightmare...
		if html.find('You are being redirected') < 0:
			return html

		import re
		match = re.search("window.location = ['\"]([^'\"]*)['\"];", html)
		if match is None or match.group(1) is None:
			return html

		if chapter.url == match.group(1):
			raise Exception('redirect loop')

		chapter.url = match.group(1)
		chapter.upsert()
		return self.softScrape(chapter)
