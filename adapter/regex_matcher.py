import re
from typing import Dict, Optional, Tuple, Any


# used to extract values from text given regex and types
class RegexMatcher:
	def __init__(self, text: str, patterns: Dict[str, Tuple[str, type]]):
		self.text = text
		self.patterns = patterns

	def matchAll(self, target: Any) -> None:
		for which in self.patterns:
			self.match(which, target)

	def match(self, which: str, target: Any) -> None:
		val = self.get(which)
		if val is None:
			return
		ttype = self.patterns[which][1]
		aname = which.rstrip('?')
		if ttype == int:
			ival = int(val.replace(',', ''))
			target.__setattr__(aname, ival)
		elif ttype == str:
			target.__setattr__(aname, val)
		elif ttype != str:
			raise Exception('unknown type: {}'.format(ttype.__name__))

	def get(self, which: str) -> Optional[str]:
		match = re.search(self.patterns[which][0], self.text)
		if match is not None:
			return match.group(1)

		if which.endswith('?'):
			return None
		else:
			raise Exception(
				'error: cannot find {} ({}) in {}'.format(
					which, self.patterns[which], self.text
				)
			)
