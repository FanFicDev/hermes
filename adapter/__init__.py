from adapter.adapter import Adapter, ManualAdapter
from adapter.ffNetAdapter import FFNAdapter
from adapter.dummyAdapter import DummyAdapter
from adapter.ao3Adapter import Ao3Adapter
from adapter.hpFanficArchiveAdapter import HpFanficArchiveAdapter
from adapter.fictionAlleyAdapter import FictionAlleyAdapter
from adapter.fanficAuthorsAdapter import FanficAuthorsAdapter
from adapter.portkeyArchiveAdapter import PortkeyArchiveAdapter
from adapter.siyeAdapter import SiyeAdapter
from adapter.fictionPressAdapter import FictionPressAdapter
from adapter.fictionHuntAdapter import FictionHuntAdapter
from adapter.spaceBattlesAdapter import SpaceBattlesAdapter
from adapter.sufficientVelocityAdapter import SufficientVelocityAdapter
from adapter.questionableQuestingAdapter import QuestionableQuestingAdapter
from adapter.hpffAdapter import HarryPotterFanfictionAdapter
from adapter.parahumansAdapter import ParahumansAdapter
from adapter.adultFanfictionAdapter import AdultFanfictionAdapter
from adapter.fanficsMeAdapter import FanficsMeAdapter
from adapter.royalroadlAdapter import RoyalRoadlAdapter
from adapter.wavesArisenAdapter import WavesArisenAdapter
from adapter.sugarQuillAdapter import SugarQuillAdapter
from adapter.bulbagardenAdapter import BulbagardenAdapter
from adapter.theFanfictionForumAdapter import TheFanfictionForumAdapter
from adapter.fanficParadiseAdapter \
    import FanficParadiseSFWAdapter, FanficParadiseNSFWAdapter
from adapter.wanderingInnAdapter import WanderingInnAdapter

from htypes import adapters, FicType


def registerAdapters() -> None:
    adapters[FicType.manual] = ManualAdapter('')
    adapters[FicType.ff_net] = FFNAdapter()
    adapters[FicType.dummy] = DummyAdapter()
    adapters[FicType.ao3] = Ao3Adapter()
    adapters[FicType.hpfanficarchive] = HpFanficArchiveAdapter()
    adapters[FicType.fictionalley] = FictionAlleyAdapter()
    adapters[FicType.fanficauthors] = FanficAuthorsAdapter()
    adapters[FicType.portkeyarchive] = PortkeyArchiveAdapter()
    adapters[FicType.siye] = SiyeAdapter()
    adapters[FicType.fictionpress] = FictionPressAdapter()
    adapters[FicType.fictionhunt] = FictionHuntAdapter()
    adapters[FicType.spacebattles] = SpaceBattlesAdapter()
    adapters[FicType.sufficientvelocity] = SufficientVelocityAdapter()
    adapters[FicType.questionablequesting] = QuestionableQuestingAdapter()
    adapters[FicType.harrypotterfanfiction] = HarryPotterFanfictionAdapter()
    adapters[FicType.parahumans] = ParahumansAdapter()
    adapters[FicType.adultfanfiction] = AdultFanfictionAdapter()
    adapters[FicType.fanficsme] = FanficsMeAdapter()
    adapters[FicType.royalroadl] = RoyalRoadlAdapter()
    adapters[FicType.wavesarisen] = WavesArisenAdapter()
    adapters[FicType.sugarquill] = SugarQuillAdapter()
    adapters[FicType.bulbagarden] = BulbagardenAdapter()
    adapters[FicType.thefanfictionforum] = TheFanfictionForumAdapter()
    adapters[FicType.fanficparadisesfw] = FanficParadiseSFWAdapter()
    adapters[FicType.fanficparadisensfw] = FanficParadiseNSFWAdapter()
    adapters[FicType.wanderinginn] = WanderingInnAdapter()

# registerAdapters()
