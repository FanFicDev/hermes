from typing import TYPE_CHECKING, List

from skitter_client import SkitterClient
from weaver_client import WeaverClient

if TYPE_CHECKING:
	import requests

skitterClients: List[SkitterClient] = [
	WeaverClient(
		baseUrl='https://primary/weaver/',
		apiKey='primaryApiKey',
		uname='weaver_api',
		upass='primaryPass'
	),
	SkitterClient(
		baseUrl='https://secondary/skitter/',
		apiKey='secondaryApiKey',
		uname='skitter_api',
		upass='secondaryPass'
	),
]


def getDefaultCookies() -> 'requests.cookies.RequestsCookieJar':
	import requests
	cookies = requests.cookies.RequestsCookieJar()

	# pretend we're an adult for fictionalley
	cookies.set(
		'fauser', 'wizard', domain='www.fictionalley.org', path='/authors'
	)

	# fake adult acceptance on livejournal
	cookies.set('adult_explicit', '1', domain='.livejournal.com', path='/')

	# accept ao3 tos
	cookies.set(
		'accepted_tos', '20180523', domain='archiveofourown.org', path='/'
	)

	return cookies
