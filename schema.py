#!/usr/bin/env python3
from typing import List, Dict, Any, Tuple, Optional, IO, Sequence
import os
import sys
import shutil
import time
import datetime
import psycopg2
from psycopg2.extensions import AsIs, register_adapter, new_type, register_type

def initDB(symlink_only: bool) -> None:
	indexes: List[int] = []
	path = ['./sql/']
	scripts = []
	with open('./doc/db_setup') as f:
		started = False
		for line in f:
			line = line.rstrip()
			# start at sql/
			if not started:
				started = line == 'sql/'
				continue
			# end with ==
			if started and line == '==':
				break
			# skip empty lines
			if len(line.strip()) < 1:
				continue

			# count all but the first tab for depth
			depth = -1
			while line.startswith('\t'):
				depth += 1
				line = line[1:]

			while len(indexes) <= depth:
				indexes += [0]

			indexes[depth] += 1
			indexes = indexes[:1 + depth]
			path = path[:1 + depth]

			line = line.strip()
			if not line.endswith('/'):
				scripts += [(path, line, list(indexes))]
			else:
				path += [line]

	maxDepth = len(indexes)

	shutil.rmtree('./sql/fresh/')
	os.mkdir('./sql/fresh/')
	spaths = []
	for path, fname, idxs in scripts:
		idxs += [0] * (maxDepth - len(idxs))
		nstub = '-'.join(map(lambda i: f'{i:02}', idxs))
		fstub = ''.join(path[1:]).replace('/', '-')
		lname = './sql/fresh/' + nstub + '-' + fstub + fname
		spath = ''.join(path) + fname
		spaths += [spath]
		tname = '../../' + spath
		os.symlink(tname, lname)

	if symlink_only:
		return

	from lite_oil import getConnection
	with getConnection('hermes') as conn:
		with conn.cursor() as curs:
			for spath in spaths:
				print(f'executing {spath}')
				with open(spath, 'r') as f:
					sql = f.read()
					curs.execute(sql)

if __name__ == '__main__':
	symlink_only = True
	if len(sys.argv) > 1 and sys.argv[1] == '--init':
		symlink_only = False

	initDB(symlink_only)

tables = [
	('source', '''
		id serial primary key,
		url url not null,
		name varchar(1024) not null,
		description varchar(4096) not null
	'''),
	('language', '''
		id serial primary key,
		name varchar(1024) not null
	'''),
	('author', '''
		id bigserial primary key,
		name varchar(1024) not null,
		urlId varchar(12) not null unique
	'''),
	('author_source', '''
		id bigserial primary key,
		authorId int8 not null references author(id),
		sourceId int4 not null references source(id),
		name varchar(1024) not null,
		url url not null,
		localId varchar(1024) not null
	'''),
	('fic', '''
		id bigserial primary key,
		urlId varchar(12) not null unique,

		sourceId int4 not null references source(id),

		localId varchar(1024) not null,
		url url not null,

		importStatus importStatus not null default('pending'),

		created oil_timestamp not null,
		fetched oil_timestamp not null,

		authorId int8 not null references author(id),

		-- optional metadata
		ficStatus ficStatus not null default('broken'),

		title varchar(4096) null,
		description text null,

		ageRating varchar(128) null,
		languageId int4 null references language(id),

		chapterCount int4 null,
		wordCount int4 null,

		reviewCount int4 null,
		favoriteCount int4 null,
		followCount int4 null,

		updated oil_timestamp null,
		published oil_timestamp null,

		extraMeta text,

		unique(sourceId, localId)
	'''),
	('fic_chapter', '''
		ficId int8 not null references fic(id),
		chapterId int4 not null,
		localChapterId varchar(1024) not null,

		url url not null,
		fetched oil_timestamp,

		title varchar(4096) null,
		content bytea null,

		primary key(ficId, chapterId),
		unique(ficId, localChapterId)
	'''),
	('users', '''
		id bigserial primary key,
		created int8,
		updated int8,
		name text unique,
		hash text,
		mail text unique,
		apikey text unique
	'''),
	('user_fic', '''
		userId int8 not null references users(id),
		ficId int8 not null references fic(id),

		readStatus ficStatus not null default('ongoing'),

		lastChapterRead int4 null,
		lastChapterViewed int4 null,

		rating smallint null,
		isFavorite boolean not null default(false),

		lastViewed oil_timestamp null,

		primary key(userId, ficId)
	'''),
	('user_fic_chapter', '''
		userId int8 not null references users(id),
		ficId int8 not null references fic(id),
		localChapterId varchar(1024) not null,

		readStatus ficStatus not null default('ongoing'),

		line int4 not null default(0),
		subLine int4 not null default(0),

		modified oil_timestamp not null default(oil_timestamp()),
		markedRead oil_timestamp null,
		markedAbandoned oil_timestamp null,

		foreign key(ficId, loaclChapterId) references fic_chapter(ficId, localChapterId),
		primary key(userId, ficId, localChapterId)
	'''),
	('tag', '''
		id bigserial primary key,
		type tag_type not null,
		name text not null,
		parent bigint null,
		sourceId bigint null
	'''),
	('fic_tag', '''
		ficId bigint not null references fic(id),
		tagId bigint not null references tag(id),
		priority integer not null default(0)
	'''),
	('read_event', '''
		userId int8 not null references users(id),
		ficId int8 not null references fic(id),
		localChapterId varchar(1024) not null,
		created oil_timestamp not null,
		ficStatus ficStatus not null default('complete'),
		foreign key(ficId, localChapterId) references fic_chapter(ficId, localChapterId)
	'''),
]

enums = {
	'ficStatus': ('broken', 'abandoned', 'ongoing', 'complete'),
	'importStatus': ('pending', 'metadata', 'content', 'deep'),
	'tag_type': ('tag', 'genre', 'fandom', 'character'),
}

#importQueueTable = '''CREATE TABLE `import_queue` (
#	`ident` TEXT PRIMARY KEY NOT NULL,
#	`added` INT NOT NULL,
#	`touched` INT NULL,
#	`tries` INT NOT NULL,
#	`status` INT NOT NULL
#);'''

entities: Dict[str, Any] = {
	'tables': tables,
	'enums': enums,
}

def getClassName(name: str) -> str:
	if name.startswith('ffn'):
		name = 'FFN' + name[3:]
	name = name.replace('_ffn', '_FFN')

	name = ''.join([n[0:1].upper() + n[1:] for n in name.split('_')])
	if name.endswith('ies'):
		name = name[:-3] + 'y'
	elif name.endswith('ueue') or name.endswith('atus'):
		pass
	elif name.endswith('s'):
		name = name[:-1]

	return name

def getTypeOid(typename: str, namespace: str = 'public') -> int:
	from lite_oil import getConnection
	with getConnection('hermes') as conn:
		with conn.cursor() as curs:
			curs.execute('''
				SELECT pg_type.oid
				  FROM pg_type JOIN pg_namespace
				         ON typnamespace = pg_namespace.oid
				WHERE typname = %(typename)s
				  AND nspname = %(namespace)s
				''', {'typename': typename, 'namespace': namespace})
			r = curs.fetchone()
			if r is None:
				raise Exception(f'unable to determine oid: {typename}, {namespace}')
			return int(r[0])

class OilTimestamp:
	def __init__(self, uts: float) -> None:
		if uts > (time.time() * 5):
			raise Exception(f"{uts} is almost certainly already an oil timestamp")
		self.ots = int(uts * 1000)
	def toUTS(self) -> int:
		return self.ots // 1000
	def toDateTime(self) -> 'datetime.datetime':
		return datetime.datetime.fromtimestamp(self.toUTS())
	def toDateString(self) -> str:
		return self.toDateTime().strftime('%Y-%m-%d')
	def __lt__(self, rhs: 'OilTimestamp') -> bool:
		return self.ots < rhs.ots
	@classmethod
	def fromOil(cls, ots: int) -> 'OilTimestamp':
		return OilTimestamp(ots / 1000)
	@classmethod
	def fromNullableOil(cls, ots: Optional[int]) -> Optional['OilTimestamp']:
		if ots is None:
			return None
		return OilTimestamp(ots / 1000)
	@classmethod
	def now(cls) -> 'OilTimestamp':
		return OilTimestamp(time.time())


def adaptOilTimestamp(oil_timestamp: OilTimestamp) -> AsIs:
	return AsIs(str(oil_timestamp.ots))
def castOilTimestamp(value: Optional[str], curs: 'psycopg2.cursor'
		) -> Optional[OilTimestamp]:
	if value is None: return None
	return OilTimestamp.fromOil(int(value))

register_adapter(OilTimestamp, adaptOilTimestamp)
_OilTimestamp = new_type((getTypeOid('oil_timestamp'),), "_OilTimestamp", castOilTimestamp)
register_type(_OilTimestamp)

def oil_timestamp() -> OilTimestamp:
	return OilTimestamp(time.time())

columnTypes = {
	'boolean': 'bool',
	'smallint': 'int',
	'integer': 'int',
	'bigint': 'int',
	'serial': 'int',
	'bigserial': 'int',
	'int4': 'int',
	'int8': 'int',
	'text': 'str',
	'bytea': 'bytes',
	'character varying(4096)': 'str',
	'character varying(1024)': 'str',
	'character varying(128)': 'str',
	'character varying(12)': 'str',
	'varchar(4096)': 'str',
	'varchar(1024)': 'str',
	'varchar(128)': 'str',
	'varchar(12)': 'str',
	'url': 'str',
	'oil_timestamp': 'OilTimestamp',
}
for enum in entities['enums']:
	columnTypes[enum] = getClassName(enum)

ColumnInfoRow = Tuple[int, str, str, bool, Optional[Any], int, str]
class ColumnInfo:
	def __init__(self, row: ColumnInfoRow):
		self.cid, self.name, self.type, \
			self.notnull, self.dflt_value, self.pk, self.ptype = row
	def toTuple(self) -> ColumnInfoRow:
		return (self.cid, self.name, self.type,
			self.notnull, self.dflt_value, self.pk, self.ptype)
	def toSourceTuple(self) -> str:
		return f"({self.cid}, {repr(self.name)}, {repr(self.type)}, " \
				+ f"{self.notnull}, {self.dflt_value}, {self.pk}, {repr(self.ptype)})"
	def __str__(self) -> str:
		return str(self.__dict__)
	@staticmethod
	def fromSQL(sql: str) -> List['ColumnInfo']:
		cid = 0
		pkCount = 0
		info: List['ColumnInfo'] = []
		for sqlLine in sql.split('\n'):
			line = sqlLine.rstrip(',').strip()
			if len(line) < 1:
				continue
			if line.startswith('--'):
				continue
			lline = line.lower()
			if lline.startswith('unique'):
				continue # TODO
			if lline.startswith('foreign key'):
				continue # TODO
			if lline.startswith('primary key'):
				if pkCount > 0:
					raise Exception('multiple pk definition?')
				names = line[len('primary key('):-1] # strip ) too
				for n in names.split(','):
					name = n.strip()
					pkCount += 1
					for ci in info:
						if ci.name == name:
							ci.pk = pkCount
							break
					else:
						raise Exception(f'unable to find pk column {name}?')
				continue

			parts = line.split()
			ctype = parts[1]
			if ctype == 'character' and parts[2].startswith('varying'):
				ctype += ' ' + parts[2]
			if ctype.endswith(','):
				ctype = ctype[:-1]
			if ctype not in columnTypes:
				raise Exception(f'unable to determine type of column: {ctype}')
			notnull = lline.find('not null') > -1
			pk = 0
			if lline.find('primary key') > -1:
				pkCount += 1
				pk = pkCount
				notnull = True
			ptype = columnTypes[ctype]

			dflt: Any = None
			for p in parts:
				if not p.lower().startswith('default('):
					continue
				v = p[len('default('):-1] # strip closing ) too
				dflt = str(v)
				if ctype in entities['enums']:
					dflt = f'{ptype}[{dflt}]'
				elif ptype == 'bool':
					dflt = 'True' if p.lower() == 'true' else 'False'
				elif ptype == 'str':
					dflt = repr(dflt)

			if not notnull:
				ptype = f'Optional[{ptype}]'

			info += [
					ColumnInfo((cid, parts[0], ctype, notnull, dflt, pk, ptype))
				]
			cid += 1
		return info

def writeColumnInfo(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	f.write('\tcolumns = [ColumnInfo(ct) for ct in [\n')
	for column in columns:
		f.write(f'\t\t{column.toSourceTuple()},\n')
	f.write('\t]]\n')

	pkColumnIds = [ci.cid for ci in columns if ci.pk > 0]
	f.write('\tpkColumns: List[ColumnInfo] = [\n')
	f.write('\t\t' + ','.join([f'columns[{cid}]' for cid in pkColumnIds]))
	f.write('\n\t]\n')

	regColumnIds = [ci.cid for ci in columns if ci.pk == 0]
	f.write('\tregColumns: List[ColumnInfo] = [\n')
	f.write('\t\t' + ','.join([f'columns[{cid}]' for cid in regColumnIds]))
	f.write('\n\t]\n')

	f.write('\tfields = {')
	f.write(','.join([repr(ci.name) for ci in columns]))
	f.write('}\n')

def writeInit(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	# default values?
	f.write(f'\tdef __init__(self) -> None:\n')
	for col in columns:
		if col.dflt_value is not None:
			f.write(f'\t\tself.{col.name}: {col.ptype} = {col.dflt_value}\n')
		elif not col.notnull:
			f.write(f'\t\tself.{col.name}: {col.ptype} = None\n')
		else:
			f.write(f'\t\tself.{col.name}: {col.ptype}\n')
	f.write('\n')

def writeFromRow(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	f.writelines([
		'\t@classmethod\n',
		f"\tdef fromRow(cls: Type[_{clsName}T], row: Sequence[Any]) -> _{clsName}T:\n",
		'\t\tself = cls()\n',
	])
	for col in columns:
		if col.type == 'bytea':
			if col.notnull:
				f.write(f'\t\tself.{col.name} = row[{col.cid}].tobytes()\n')
			else:
				f.write(f'\t\tself.{col.name} = row[{col.cid}].tobytes() if row[{col.cid}] is not None else None\n')
		elif col.type == 'oil_timestamp':
			if col.notnull:
				f.write(f'\t\tself.{col.name} = OilTimestamp.fromOil(row[{col.cid}])\n')
			else:
				f.write(f'\t\tself.{col.name} = OilTimestamp.fromNullableOil(row[{col.cid}])\n')
		else:
			f.write(f'\t\tself.{col.name} = row[{col.cid}]\n')
	f.write('\t\treturn self\n\n')

def writeToTuple(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	tupleTypes = ', '.join([ci.ptype for ci in columns])
	memberNames = ', '.join([f'self.{ci.name}' for ci in columns])
	f.writelines([
		f"\tdef toTuple(self) -> Tuple[{tupleTypes}]:\n",
		f'\t\treturn ({memberNames},)\n',
	])
	f.write('\n')

def writeToInsertTuple(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	columns = [c for c in columns if c.type.lower().find('serial') < 0]
	tupleTypes = ', '.join([ci.ptype for ci in columns])
	memberNames = ', '.join([f'self.{ci.name}' for ci in columns])
	f.writelines([
		f"\tdef toInsertTuple(self) -> Tuple[{tupleTypes}]:\n",
		f'\t\treturn ({memberNames},)\n',
	])
	f.write('\n')

def writeToJSONable(f: IO, clsName: str, columns: List[ColumnInfo]) -> None:
	if len(columns) < 1:
		f.writelines([
			f"\tdef toJSONable(self) -> lite.JSONable:\n",
			f'\t\treturn {{ }}\n',
		])
		return

	f.writelines([
		f"\tdef toJSONable(self) -> lite.JSONable:\n",
		f'\t\treturn {{\n',
	])
	for col in columns:
		if col.type == 'oil_timestamp':
			if col.notnull:
				f.write(f'\t\t\t"{col.name}": self.{col.name}.toDateTime().isoformat(),\n')
			else:
				f.write(f'\t\t\t"{col.name}": None if self.{col.name} is None else self.{col.name}.toDateTime().isoformat(),\n')
		else:
			f.write(f'\t\t\t"{col.name}": self.{col.name},\n')

	f.writelines([
		f'\t\t}}\n',
		f'\n',
	])

def writeEnum(f: IO, name: str, values: Sequence[str]) -> None:
	clsName = getClassName(name)
	print(f'  generating enum {name} => {clsName}')
	f.write(f'class {clsName}(enum.IntEnum):\n')
	for value, vname in enumerate(values):
		print(f'    {vname} = {value}')
		f.write(f'\t{vname} = {value}\n')
	oid = getTypeOid(name.lower())
	f.writelines([
		'\n',
		f'def adapt{clsName}({name}: {clsName}) -> AsIs:\n'
		f"\treturn AsIs(\"'%s'::{name}\" % {name}.name)\n",
		f"def cast{clsName}(value: Optional[str], curs: 'psycopg2.cursor'\n",
		f'\t\t) -> Optional[{clsName}]:\n',
		f'\tif value is None: return None\n',
		f'\treturn {clsName}[value]\n',
		'\n',
		f'register_adapter({clsName}, adapt{clsName})\n',
		f'_{clsName} = new_type(({oid},), "_{clsName}", cast{clsName})\n',
		f'register_type(_{clsName})\n',
		'\n',
	])

def generateBaseClasses() -> None:
	import os
	us = os.path.realpath(os.path.expanduser(__file__))
	here = os.path.dirname(us)
	targ = os.path.join(here, 'store_bases.py')

	with open(targ, 'w') as f:
		f.writelines([
			'import typing\n',
			'from typing import Optional, Type, Sequence, List, Tuple, Any, NewType, TypeVar\n',
			'import lite\n',
			'import enum\n',
			'import psycopg2\n',
			'from psycopg2.extensions import AsIs, register_adapter, new_type, register_type\n',
			'from schema import ColumnInfo, OilTimestamp, oil_timestamp\n',
			'\n',
		])

		print(f'generating enums')
		for enum, values in entities['enums'].items():
			writeEnum(f, enum, values)

		print(f'generating tables')
		for table, sql in entities['tables']:
			clsName = getClassName(table)
			print(f'  generating table {table} => {clsName}')
			cols = ColumnInfo.fromSQL(sql)
			for col in cols:
				print(f'    {str(col)}')

			f.write(f"_{clsName}T = TypeVar('_{clsName}T', bound='{clsName}')\n")
			f.write(f'class {clsName}(lite.StoreType):\n')
			writeColumnInfo(f, clsName, cols)
			writeInit(f, clsName, cols)
			writeFromRow(f, clsName, cols)
			writeToTuple(f, clsName, cols)
			writeToInsertTuple(f, clsName, cols)
			writeToJSONable(f, clsName, cols)

if __name__ == '__main__':
	generateBaseClasses()
	# TODO compare computed columns here to actual columns from psql?

