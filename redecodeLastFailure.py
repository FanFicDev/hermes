#!/usr/bin/env python3
import scrape

z = None
with open(scrape.decodeFailureDumpFile, "rb") as f:
    z = f.read()

r = scrape.decodeRequest(z, "")
if r is None:
    print("None")
else:
    print(len(r))
