#!/usr/bin/env bash
# check that the setup can probably run

if [[ ! -f priv.py ]]; then
	echo "error: no priv.py file"
	exit 1
fi

exit 0

