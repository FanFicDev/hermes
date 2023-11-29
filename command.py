from typing import Any, Callable, List, Optional, Set, Tuple, Union, cast
import inspect


class Command:
    def __init__(self, name: str, targets: List[Callable]):
        self.name = name
        self.targets = targets
        self.tspecs = [inspect.getfullargspec(t) for t in self.targets]
        # ensure non-overlapping tspec?

        self.res: Optional[Any] = None

    def printUsage(self) -> None:
        for idx in range(len(self.targets)):
            print(f"usage: {self.__getUsage(idx)}")

        types: Set[type] = set()
        for idx in range(len(self.tspecs)):
            for arg in self.tspecs[idx].annotations:
                types |= {self.tspecs[idx].annotations[arg]}

        print("")
        for atype in types:
            h = self.__getTypeDescription(atype)
            if h is not None:
                print(h)

    def __getUsage(self, idx: int) -> str:
        if len(self.tspecs[idx].args) == 0:
            return self.name
        aspec: List[str] = []
        for arg in self.tspecs[idx].args:
            aspec += [f"{arg}:{self.tspecs[idx].annotations[arg]}"]
        return self.name + " " + " ".join(aspec)

    def __getTypeDescription(self, t: Any) -> Optional[str]:
        h = getattr(t, "help", None)
        if callable(h):
            return cast(str, t.help())
        else:
            return None

    def match(self, argv: List[str]) -> bool:
        if not self.name.startswith(argv[0]):
            return False

        for idx in range(len(self.targets)):
            if self.__try(idx, argv[1:]):
                return True
        self.printUsage()
        return False

    def __try(self, idx: int, argv: List[str]) -> bool:
        # cannot accept more parameters
        if len(self.tspecs[idx].args) < len(argv):
            return False

        # can accept up to len(targs) - optional suffix
        trailingOptional = self.__trailingOptionalCount(idx)
        if (len(self.tspecs[idx].args) - trailingOptional) > len(argv):
            return False

        targs: List[Any] = []
        for aidx in range(len(argv)):
            mres = self.__match(idx, aidx, argv[aidx])
            if mres[0] == False:
                self.printUsage()
                return False
            else:
                targs += [mres[1]]
        while len(targs) < len(self.tspecs[idx].args):
            targs += [None]

        # do execute
        self.res = self.targets[idx](*targs)
        return True

    def __trailingOptionalCount(self, idx: int) -> int:
        cnt = 0
        for aidx in reversed(range(len(self.tspecs[idx].args))):
            if self.__optional(idx, aidx):
                cnt += 1
            else:
                break
        return cnt

    def __optional(self, idx: int, aidx: int) -> bool:
        ours = self.tspecs[idx].annotations[self.tspecs[idx].args[aidx]]
        if ours == Union[int, None]:
            return True
        return False

    def __match(self, idx: int, aidx: int, possible: str) -> Tuple[bool, Any]:
        ours = self.tspecs[idx].annotations[self.tspecs[idx].args[aidx]]
        if ours == str:
            return (True, possible)
        if ours == int:
            return (True, int(possible))
        if ours == Union[int, None]:
            if len(possible) < 1:
                return (True, None)
            return (True, int(possible))
        if type(ours) == type(type):
            v = ours.tryParse(possible)
            if v is None:
                return (False, None)
            else:
                return (True, v)
        return (False, None)
