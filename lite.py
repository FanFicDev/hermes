import re
import threading
from typing import (
	Dict, List, Tuple, Any, Iterable, Optional, Sequence, Type, TypeVar
)
import psycopg2
import schema
from schema import ColumnInfo
import util
from lite_oil import getConnection, commit, shutdown

JSONable = Dict[str, Any]

__threadData = threading.local()
__columnInfo: Dict[str, List[ColumnInfo]] = {}
__tableNames: Dict[str, str] = {
	'TagBase': 'tag',
	'Genre': 'tag',
	'Tag': 'tag',
	'Fandom': 'tag',
	'Character': 'tag',
	'FicTagBase': 'fic_tag',
	'FicGenre': 'fic_tag',
	'FicTag': 'fic_tag',
	'FicFandom': 'fic_tag',
	'FicCharacter': 'fic_tag',
}

autocommit: bool = True
logQueries: bool = False


def getTableName(clsName: str) -> str:
	global __tableNames
	if clsName in __tableNames:
		return __tableNames[clsName]

	name = clsName

	if name.startswith('FFN'):
		name = 'ffn' + name[3:]
	name = name.replace('FFN', '_ffn')

	name = name[0].lower() + re.sub('([A-Z])', '_\\1', name[1:]).lower()
	__tableNames[clsName] = name
	return name


def transformQueryData(data: Iterable[Any]) -> Iterable[Any]:
	ld = list(data)
	nd = []
	for d in ld:
		if isinstance(d, bytes):
			nd.append(f'{{bytes: len:{len(d)}}}')
		else:
			nd.append(d)
	return tuple(nd)


def logQuery(kind: str, table: str, sql: str, data: Iterable[Any]) -> None:
	if not logQueries:
		return
	sql = sql.replace('\t', ' ').replace('\n', ' ')
	while sql.find('  ') >= 0:
		sql = sql.replace('  ', ' ')
	data = transformQueryData(data)
	util.logMessage(f'{kind}: sql={sql} data={data}')


T = TypeVar('T', bound='StoreType')


class StoreType(object):
	subDB: str = 'meta'
	columns: List[ColumnInfo]
	pkColumns: List[ColumnInfo]
	regColumns: List[ColumnInfo]

	@classmethod
	def getConnection(cls) -> 'psycopg2.connection':
		return getConnection(cls.subDB)

	@classmethod
	def getNonGeneratedColumns(cls) -> List[ColumnInfo]:
		return [col for col in cls.columns if col.type.lower().find('serial') < 0]

	@classmethod
	def getTableName(cls) -> str:
		return getTableName(cls.__name__)

	@classmethod
	def fromRow(cls: Type[T], row: Sequence[Any]) -> T:
		raise NotImplementedError()

	def toJSONable(self) -> JSONable:
		raise NotImplementedError()

	@classmethod
	def get(cls: Type[T], pkValues: Iterable[Any]) -> Optional[T]:
		table = cls.getTableName()

		conn = cls.getConnection()
		sql = 'SELECT * FROM {} WHERE '.format(table)
		whereParts = ['{} = %s'.format(pk.name) for pk in cls.pkColumns]
		if len(whereParts) == 0:
			raise Exception('table {} has no primary key'.format(table))
		sql += ' AND '.join(whereParts)

		with conn.cursor() as curs:
			logQuery('get', table, sql, pkValues)
			curs.execute(sql, pkValues)
			r = curs.fetchone()

		if r is None:
			return None

		return cls.fromRow(r)

	@classmethod
	def lookup(cls: Type[T], pkValues: Sequence[Any]) -> T:
		obj = cls.get(pkValues)
		if obj is not None:
			return obj
		raise Exception(f"unable to lookup {cls.__name__}: {pkValues}")

	@staticmethod
	def buildWhere(whereData: Dict[str, Any] = None) -> Tuple[Iterable[Any], str]:
		operators = {'>', '<', '>=', '<=', '!=', '==', 'is'}
		data: List[Any] = []
		whereSql = ''
		if whereData is not None and len(whereData) > 0:
			whereParts: List[str] = []
			for col in whereData:
				bit = whereData[col]
				if (
					isinstance(bit, tuple) and len(bit) == 2 and isinstance(bit[0], str)
					and bit[0] in operators
				):
					whereParts += [f'{col} {bit[0]} %s']
					data += [bit[1]]
				else:
					whereParts += ['{} = %s'.format(col)]
					data += [whereData[col]]
			whereSql = ' WHERE ' + ' AND '.join(whereParts)
		return (tuple(data), whereSql)

	@classmethod
	def select(
		cls: Type[T],
		whereData: Dict[str, Any] = None,
		orderBy: str = None
	) -> List[T]:
		table = cls.getTableName()
		conn = cls.getConnection()

		data, whereSql = StoreType.buildWhere(whereData)
		sql = 'SELECT * FROM {} {}'.format(table, whereSql)

		if orderBy is not None:
			sql += ' ORDER BY ' + orderBy

		with conn.cursor() as curs:
			logQuery('select', table, sql, data)
			curs.execute(sql, data)
			res = [cls.fromRow(r) for r in curs.fetchall()]

		return res

	@classmethod
	def count(cls, whereData: Dict[str, Any] = None) -> int:
		table = cls.getTableName()
		conn = cls.getConnection()

		data, whereSql = StoreType.buildWhere(whereData)
		sql = 'SELECT COUNT(1) FROM {} {}'.format(table, whereSql)
		print(sql)

		with conn.cursor() as curs:
			logQuery('count', table, sql, data)
			curs.execute(sql, data)
			r = curs.fetchone()
		assert (r is not None)
		return int(r[0])

	def __getParts(self, which: List[str]) -> Iterable[Any]:
		return tuple([self.__dict__[piece] for piece in which])

	def toTuple(self) -> Iterable[Any]:
		cols = type(self).columns
		return self.__getParts([col.name for col in cols])

	def toInsertTuple(self) -> Iterable[Any]:
		cols = type(self).getNonGeneratedColumns()
		return self.__getParts([col.name for col in cols])

	def getPKTuple(self) -> Iterable[Any]:
		return self.__getParts([col.name for col in type(self).pkColumns])

	def getNonPKTuple(self) -> Iterable[Any]:
		return self.__getParts([col.name for col in type(self).regColumns])

	def insert(self) -> None:
		table = type(self).getTableName()
		cols = type(self).getNonGeneratedColumns()
		sql = 'INSERT INTO {}({}) VALUES({})'.format(
			table, ', '.join([c.name for c in cols]), ', '.join(['%s'] * len(cols))
		)
		data = self.toInsertTuple()
		conn = type(self).getConnection()
		with conn.cursor() as curs:
			try:
				logQuery('insert', table, sql, data)
				curs.execute(sql, data)
			except:
				util.logMessage(f'failed to insert: {sql}: {data}', 'lite.log')
				raise

		global autocommit
		if autocommit == True:
			conn.commit()

	def update(self) -> None:
		table = type(self).getTableName()
		pkCols = type(self).pkColumns
		nkCols = type(self).regColumns

		sql = 'UPDATE {} '.format(table)
		sql += ' SET ' + (', '.join([col.name + ' = %s' for col in nkCols]))
		sql += ' WHERE ' + (' AND '.join([col.name + ' = %s' for col in pkCols]))
		data = tuple(list(self.getNonPKTuple()) + list(self.getPKTuple()))

		conn = type(self).getConnection()
		with conn.cursor() as curs:
			logQuery('update', table, sql, data)
			curs.execute(sql, data)

		global autocommit
		if autocommit == True:
			conn.commit()

	def upsert(self) -> None:
		me = type(self).get(self.getPKTuple())
		if me == None:
			self.insert()
		else:
			self.update()

	@classmethod
	def new(cls: Type[T]) -> T:
		obj = cls()
		for col in cls.columns:
			# don't overwrite values set by the constructor
			if col.name in obj.__dict__:
				continue
			obj.__setattr__(col.name, col.dflt_value)
		return obj

	@classmethod
	def create(cls: Type[T], pkValues: Sequence[Any]) -> T:
		obj = cls.new()
		for i in range(len(cls.pkColumns)):
			obj.__setattr__(cls.pkColumns[i].name, pkValues[i])

		obj.insert()
		res = cls.get(pkValues)
		if res is None:
			raise Exception('unable to create')
		return res

	@classmethod
	def getOrCreate(cls: Type[T], pkValues: Sequence[Any]) -> T:
		obj = cls.get(pkValues)
		if obj is not None:
			return obj
		return cls.create(pkValues)
