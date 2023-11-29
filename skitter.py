import contextlib

import priv
import scrape as sc
import util
from weaver_client import WeaverClient


def scrape(url: str, staleOnly: bool = False, fallback: bool = False) -> sc.ScrapeMeta:
    if sc._staleOnly:
        util.logMessage(f"skitter.scrape: HERMES_STALE only {url}")
        return sc.scrape(url)

    if staleOnly:
        util.logMessage(f"skitter.scrape: staleOnly {url}")
        for c in reversed(priv.skitterClients):
            ce = c.cache(url)
            if ce is not None:
                return ce
        raise Exception(f"skitter.scrape: unable to staleOnly scrape: {url}")

    for c in priv.skitterClients:
        try:
            # util.logMessage(f'skitter.scrape: calling {c.ident}.scrape({url})')
            r = c.scrape(url)
            return r
        except Exception as e:
            util.logMessage(f"skitter.scrape: {c.ident}.scrape failed: {e}")
            pass

    if fallback:
        return sc.scrape(url)
    raise Exception(f"skitter.scrape: unable to scrape: {url}")


def softScrape(url: str, fallback: bool = False) -> sc.ScrapeMeta:
    # return old copy if any exists
    for c in reversed(priv.skitterClients):
        if isinstance(c, WeaverClient):
            continue
        with contextlib.suppress(Exception):
            # util.logMessage(f'skitter.softScrape: {c.ident}.staleScrape({url})')
            r = c.staleScrape(url)
            if r is not None:
                return r

    # attempt to softScrape
    for c in priv.skitterClients:
        with contextlib.suppress(Exception):
            # util.logMessage(f'FFNAdapter.softScrape: {c.ident}.softScrape({url})')
            return c.softScrape(url)

    if fallback:
        r = sc.softScrapeWithMeta(url)
        if r is not None:
            return r
    raise Exception(f"skitter.softScrape: unable to softScrape: {url}")


if __name__ == "__main__":
    import sys

    from scrape import canonizeUrl, saveWebRequest
    from skitter_client import SkitterClient

    skitter_primary: SkitterClient = priv.skitterClients[0]
    skitter_secondary: SkitterClient = priv.skitterClients[-1]

    if sys.argv[1] == "recache":
        for line in sys.stdin.readlines():
            line = line.strip()
            url = canonizeUrl(line)
            print(url)
            # we want the newest version of non-1 chapters, otherwise the oldest
            # (so we skip now-deleted info requests for chap 1)
            res = skitter_secondary.cache(url, rev=url.endswith("/1"))
            if res is not None:
                saveWebRequest(res["fetched"], res["url"], res["status"], res["raw"])
            else:
                print("  FAILED")
    elif sys.argv[1] == "rescrape":
        print("rescrape")
        for line in sys.stdin.readlines():
            line = line.strip()
            url = canonizeUrl(line)
            print(url)
            try:
                res = skitter_primary.crawl(url)
                saveWebRequest(res["fetched"], res["url"], res["status"], res["raw"])
            except:
                print("  FAILED")
                raise
