from typing import Any


class Widget:
	def handleKey(self, key: int) -> bool:
		pass

	def refresh(self) -> None:
		pass

	def handleResize(self, maxX: int, maxY: int) -> None:
		pass

	def repaint(self, stdscr: Any) -> None:
		pass
