from typing import List, Any, Dict, Union, Tuple, Optional, cast
import traceback
from enum import IntEnum
from flask import Flask, Response, request, make_response
import werkzeug.wrappers
from werkzeug.exceptions import NotFound

from store import Fic, FicChapter
from htypes import FicId
import util
import scrape
from view import HtmlView
from lite import JSONable

BasicFlaskResponse = Union[Response, werkzeug.wrappers.Response, str, JSONable]
FlaskResponse = Union[BasicFlaskResponse, Tuple[BasicFlaskResponse, int]]

import adapter

adapter.registerAdapters()

app = Flask(__name__)
app.url_map.strict_slashes = False


def cleanHtml(html: str) -> str:
	view = HtmlView(html, markdown=False)
	html = ''.join(['<p>{}</p>'.format(l) for l in view.text])
	return html


class Err(IntEnum):
	# general
	success = 0
	not_found = 404

	# lookup results
	no_query = -10
	bad_query = -11
	bad_ficId = -12

	# fic results
	urlId_not_found = -20
	cid_not_found = -21

	# cache results
	failed_to_cache_cid = -30

	def msg(self) -> str:
		return {
			Err.success: 'ok',
			Err.not_found: 'not found',
			Err.no_query: 'no query',
			Err.bad_query: 'unable to parse query',
			Err.bad_ficId: 'unable to load fic',
			Err.urlId_not_found: 'urlId not found',
			Err.cid_not_found: 'cid not found',
			Err.failed_to_cache_cid: 'unable to cache cid',
		}[self]

	def get(self, extra: Optional[JSONable] = None) -> JSONable:
		base = {'err': int(self), 'msg': self.msg()}
		if extra is not None:
			base.update(extra)
		return base

	@staticmethod
	def ok(extra: Optional[JSONable] = None) -> JSONable:
		return Err.success.get(extra)


def get_request_source() -> Tuple[bool, str, Optional[str]]:
	automated = (request.args.get('automated', None) == 'true')
	return (automated, request.url_root, request.remote_addr)


@app.errorhandler(404)
def page_not_found(e: Exception) -> FlaskResponse:
	return make_response(Err.not_found.get(), 404)


@app.get('/')
@app.get('/v0/')
@app.get('/v0/status')
def index() -> FlaskResponse:
	return Err.ok(
		{
			'license': 'agpl-3.0',
			'source': 'https://github.com/FanFicDev/hermes'
		}
	)


@app.get('/v0/fic/<urlId>/')
def v0_fic(urlId: str) -> Any:
	fics = Fic.select({'urlId': urlId})
	if len(fics) != 1:
		return Err.urlId_not_found.get()
	return Err.ok(fics[0].toJSONable())


@app.get('/v0/fic/<urlId>/all')
def v0_fic_all(urlId: str) -> Any:
	fics = Fic.select({'urlId': urlId})
	if len(fics) != 1:
		return Err.urlId_not_found.get()
	fic = fics[0]
	if fic.chapterCount is None:
		app.logger.error(f'err: fic has no chapter count: {fic.id}')
		return Err.urlId_not_found.get()
	ficChapters = {
		fc.chapterId: fc
		for fc in FicChapter.select({'ficId': fic.id})
	}
	chapters = {}
	for cid in range(1, fic.chapterCount + 1):
		if cid not in ficChapters:
			return Err.cid_not_found.get({'arg': f'{fic.id}/{cid}'})
		chapter = ficChapters[cid]
		cres = chapter.toJSONable()
		try:
			content = cres['content']
			if content is not None:
				content = util.decompress(content)
				content = scrape.decodeRequest(content, f'{fic.id}/{cid}')
				content = cleanHtml(content)
				if content != cleanHtml(content):
					app.logger.warn(
						f'v0_fic_all: {fic.id}/{cid} did not round-trip through cleanHtml'
					)
			cres['content'] = content
			chapters[cid] = cres
		except:
			pass

	res = fic.toJSONable()
	return Err.ok({'info': res, 'chapters': chapters})


@app.get('/v0/lookup')
def v0_lookup() -> Any:
	q = request.args.get('q', '').strip()
	if len(q.strip()) < 1:
		return Err.no_query.get({'arg': q})

	app.logger.info(f'v0_lookup: query: {q}')
	ficId = FicId.tryParse(q)
	if ficId is None:
		return Err.bad_query.get({'arg': q})

	app.logger.info(f'v0_lookup: ficId: {ficId.__dict__}')
	try:
		fic = Fic.load(ficId)
		return v0_fic(fic.urlId)
	except:
		app.logger.error(
			f'v0_lookup: something went wrong in load: {traceback.format_exc()}'
		)
		pass
	return Err.bad_ficId.get({'arg': ficId.__dict__})


@app.get('/v0/cache/<urlId>')
def v0_cache(urlId: str) -> Any:
	fics = Fic.select({'urlId': urlId})
	if len(fics) != 1:
		return Err.urlId_not_found.get()
	fic = fics[0]
	if fic.chapterCount is None:
		app.logger.error(f'err: fic has no chapter count: {fic.id}')
		return Err.urlId_not_found.get()
	for cid in range(1, fic.chapterCount + 1):
		try:
			chapter = fic.chapter(cid)
			chapter.cache()
		except Exception as e:
			return Err.failed_to_cache_cid.get({'arg': f'{fic.id}/{cid}'})

	return Err.ok(fic.toJSONable())


@app.get('/v0/remote')
def v0_remote() -> FlaskResponse:
	return get_request_source()[2]


if __name__ == '__main__':
	app.run(debug=True)
