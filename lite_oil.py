from typing import Dict, Optional
import os
import psycopg2

__conns: Dict[str, 'psycopg2.connection'] = {}


def getConnection(subDB: str) -> 'psycopg2.connection':
	global __conns
	if subDB in __conns:
		return __conns[subDB]

	connParms: Dict[str, Optional[str]] = {
		'dbname': 'hermes',  # TODO
		'user': None,
		'password': None,
		'host': None,
		'port': None,
	}

	for key in connParms:
		envKey = f'OIL_DB_{key.upper()}'
		if envKey not in os.environ:
			continue
		connParms[key] = os.environ[envKey]

	connStr = ' '.join(
		[f'{k}={v}' for k, v in connParms.items() if v is not None]
	)

	conn = psycopg2.connect(connStr)
	__conns[subDB] = conn
	return conn


def commit() -> None:
	global __conns
	for subDB in __conns:
		__conns[subDB].commit()


def shutdown() -> None:
	global __conns
	for subDB in list(__conns.keys()):
		__conns[subDB].commit()
		__conns[subDB].close()
		del __conns[subDB]
