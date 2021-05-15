select fc1.fic_id, fc1.cid, fc2.cid, fc1.markedRead, fc2.markedRead,
	fc1.markedRead - fc2.markedRead
from fic_chapters fc1
inner join fic_chapters fc2
	on fc2.fic_id = fc1.fic_id
	and fc2.cid = fc1.cid - 1
where fc1.markedRead is not null
	and fc2.markedRead is not null
	and fc1.markedRead - fc2.markedRead > 5;

