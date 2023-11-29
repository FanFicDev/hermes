import re
import time
import traceback
from typing import Optional, List, Dict

from htypes import FicType, FicId
from store import OilTimestamp, Language, FicStatus, Fic, FicChapter, Fandom
import util
import scrape
import skitter

from adapter.adapter import Adapter
from adapter.regex_matcher import RegexMatcher

# yapf: disable
ffNetGenres = {"Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
	"Friendship", "General", "Horror", "Humor", "Hurt/Comfort", "Mystery",
	"Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual", "Supernatural",
	"Suspense", "Tragedy", "Western"}

ffNetFandomCategories = {
	'anime', 'book', 'cartoon', 'game', 'misc', 'movie', 'play', 'tv', 'comic',
}

ffNetFandomMap = {
	'A-Certain-Scientific-Railgun-%E3%81%A8%E3%81%82%E3%82%8B%E7%A7%91%E5%AD%A6%E3%81%AE%E8%B6%85%E9%9B%BB%E7%A3%81%E7%A0%B2': 'A Certain Scientific Railgun',
	'Addams-Family': 'Addams Family',
	'Aeon-Flux': 'Aeon Flux',
	'A-for-Andromeda-1961': 'A for Andromeda',
	'Alex-Rider': 'Alex Rider',
	'Alias': 'Alias',
	'Alpha-Centauri': 'Alpha Centauri',
	'Alphas': 'Alphas',
	'Angel': 'Angel',
	'A-Nightmare-on-Elm-Street': 'A Nightmare on Elm Street',
	'Anime-X-overs': '',
	'Army-Wives': 'Army Wives',
	'Arpeggio-of-Blue-Steel-%E8%92%BC%E3%81%8D%E9%8B%BC%E3%81%AE%E3%82%A2%E3%83%AB%E3%83%9A%E3%82%B8%E3%82%AA': 'Arpeggio of Blue Steel',
	'Arrow': 'Arrow',
	'Artemis-Fowl': 'Artemis Fowl',
	'A-song-of-Ice-and-Fire': 'A song of Ice and Fire',
	'Attack-on-Titan-%E9%80%B2%E6%92%83%E3%81%AE%E5%B7%A8%E4%BA%BA': 'Attack on Titan',
	'Avatar': "James Cameron's Avatar",
	'Avatar-Last-Airbender': 'Avatar',
	'Avengers': 'Avengers',
	'Babylon-5': 'Babylon 5',
	'Baldur-s-Gate': "Baldur's Gate",
	'Basilisk': 'Basilisk',
	'Batman': 'Batman',
	'Batman-Begins-Dark-Knight': 'Batman',
	'Battlestar-Galactica-2003': 'Battlestar Galactica',
	'Ben-10': 'Ben 10',
	'Bend-it-Like-Beckham': 'Bend It Like Beckham',
	'Big-Bang-Theory': 'Big Bang Theory',
	'Big-Hero-6': 'Big Hero 6',
	'Big-O': 'Big O',
	'BioShock': 'BioShock',
	'Birds-Of-Prey': 'Birds Of Prey',
	'Black-Panther': 'Black Panther',
	'Black-Sails': 'Black Sails',
	'Blade': 'Blade',
	'Bleach': 'Bleach',
	'Book-X-overs': '',
	'Breakout-Kings': 'Breakout Kings',
	'Buffy-The-Vampire-Slayer': 'Buffy the Vampire Slayer',
	'Buffy-X-overs': 'Buffy the Vampire Slayer',
	'Calvin-Hobbes': 'Calvin & Hobbes',
	'Campione-%E3%82%AB%E3%83%B3%E3%83%94%E3%82%AA%E3%83%BC%E3%83%8D': 'Campione!',
	'Captain-America': 'Captain America',
	'Card-Captor-Sakura': 'Cardcaptor Sakura',
	'Castle': 'Castle',
	'Castlevania': 'Castlevania',
	'Charmed': 'Charmed',
	'Chrome-Shelled-Regios': 'Chrome Shelled Regios',
	'Chronicles-of-Narnia': 'Chronicles of Narnia',
	'Chrono-Cross': 'Chrono Cross',
	'Chuck': 'Chuck',
	'Clannad': 'Clannad',
	'Code-Geass': 'Code Geass',
	'Command-Conquer': 'Command & Conquer',
	'CSI-New-York': 'CSI New York',
	'Cthulhu-Mythos': 'Cthulhu',
	'Culture-Iain-M-Bank': 'The Culture',
	'Danny-Phantom': 'Danny Phantom',
	'Dark-Angel': 'Dark Angel',
	'Darker-than-BLACK': 'Darker than Black',
	'Darkest-Dungeon': 'Darkest Dungeon',
	'Dark-Souls': 'Dark Souls',
	'Darkstalkers': 'Darkstalkers',
	'DC-Superheroes': 'DC',
	'Deadpool': 'Deadpool',
	'Death-in-Paradise': 'Death in Paradise',
	'Death-Note': 'Death Note',
	'Descent': 'Descent',
	'Destiny': 'Destiny',
	'Detective-Conan-Case-Closed': 'Detective Conan',
	'Devil-May-Cry': 'Devil May Cry',
	'Diablo': 'Diablo',
	'Discworld': 'Discworld',
	'Disgaea': 'Disgaea',
	'Dishonored': 'Dishonored',
	'Disney': '',
	'Doctor-Who': 'Doctor Who',
	'Dollhouse': 'Dollhouse',
	'Dominion': 'Dominion',
	'Doom': 'Doom',
	'Dota-2': 'Dota 2',
	'Dracula': 'Dracula',
	'Dragon-Age': 'Dragon Age',
	'Dragon-Ball-Z': 'Dragon Ball Z',
	'Dragonriders-of-Pern-series': 'Dragonriders of Pern',
	'Dresden-Files': 'Dresden Files',
	'Duchess': 'Duchess',
	'Dune': 'Dune',
	'Dungeons-and-Dragons': 'Dungeons and Dragons',
	'Elder-Scroll-series': 'Elder Scolls',
	'Endless-Ocean': 'Endless Ocean',
	'Evangelion': 'Evangelion',
	'EVE-Online': 'EVE Online',
	'Fairly-OddParents': 'Fairly OddParents',
	'Fairy-Tail': 'Fairy Tail',
	'Fallout': 'Fallout',
	'Familiar-of-Zero': 'Familiar of Zero',
	'Fantastic-Four': 'Fantastic Four',
	'Farscape': 'Farscape',
	'Fate-stay-night': 'Fate/stay night',
	'Final-Fantasy-VIII': 'Final Fantasy VIII',
	'Final-Fantasy-X': 'Final Fantasy X',
	'Fingersmith': 'Fingersmith',
	'Firefly': 'Firefly',
	'Fringe': 'Fringe',
	'Frozen': 'Frozen',
	'Fullmetal-Alchemist': 'Fullmetal Alchemist',
	'Futurama': 'Futurama',
	'Game-of-Thrones': 'Game of Thrones',
	'Game-X-overs': '',
	'Gates': 'Gates',
	'Gemma-Doyle-Trilogy': 'Gemma Doyle',
	'Gilmore-Girls': 'Gilmore Girls',
	'Girl-Genius': 'Girl Genius',
	'Gold-Digger': 'Gold Digger',
	'Good-Omens': 'Good Omens',
	'Good-Wife': 'Good Wife',
	'Gossip-Girl': 'Gossip Girl',
	'Gravity-Falls': 'Gravity Falls',
	'Grim-Adventures-of-Billy-Mandy': 'Grim Adventures of Billy and Mandy',
	'Grimm': 'Grimm',
	'Grindhouse': 'Grindhouse',
	'Gunbuster': 'Gunbuster',
	'Gundam-UC': 'Gundam UC',
	'Haibane-Renmei': 'Haibane Renmei',
	'Half-Life': 'Half-Life',
	'Halo': 'Halo',
	'Harry-Potter': 'Harry Potter',
	'Haruhi-Suzumiya-series': 'Haruhi Suzumiya',
	'Hawaii-Five-0': 'Hawaii Five-O',
	'Hellsing': 'Hellsing',
	'Heroes': 'Heroes',
	'High-School-DxD-%E3%83%8F%E3%82%A4%E3%82%B9%E3%82%AF%E3%83%BC%E3%83%ABD-D': 'High School DxD',
	'His-Dark-Materials': 'His Dark Materials',
	'Hobbit': 'The Hobbit',
	'Hollows-Kim-Harrison': 'Hollows',
	'Honor-Harrington': 'Honor Harrington',
	'House-M-D': 'House, M.D.',
	'House-of-Wax': 'House of Wax',
	'How-to-Train-Your-Dragon': 'How to Train Your Dragon',
	'Hunger-Games': 'Hunger Games',
	'Hyperdimension-Neptunia': 'Hyperdimension Neptunia',
	'Inheritance-Cycle': 'Inheritance Cycle',
	'Inside': 'Inside',
	'Inuyasha': 'Inuyasha',
	'Invader-Zim': 'Invader Zim',
	'Ironman': 'Ironman',
	'Jak-and-Daxter': 'Jak and Dakter',
	'Jennifer-s-Body': "Jennifer's Body",
	'Jessica-Jones': 'Jessica Jones',
	'John-Wick': 'John Wick',
	'JoJo-s-Bizarre-Adventure': "JoJo's Bizarre Adventure",
	'Jurassic-Park': 'Jurassic Park',
	'Justice-League': 'Justice League',
	'Kamen-Rider': 'Kamen Rider',
	'Kantai-Collection': 'Kantai Collection',
	'Katekyo-Hitman-Reborn': 'Katekyo Hitman Reborn!',
	'Kick-Ass': 'Kick-Ass',
	'Kill-Bill': 'Kill Bill',
	'Kim-Possible': 'Kim Possible',
	'Kushiel-s-Legacy-series': "Kushiel's Legacy",
	'La-Corda-D-Oro': "La Corda D'Oro",
	'La-Femme-Nikita': 'La Femme Nikita',
	'Law-and-Order-SVU': 'Law and Order',
	'League-of-Legends': 'League of Legends',
	'Legend-of-Korra': 'Legend of Korra',
	'Legend-of-the-Seeker': 'Legend of the Seeker',
	'Legend-of-Zelda': 'Legend of Zelda',
	'Little-Witch-Academia-%E3%83%AA%E3%83%88%E3%83%AB-%E3%82%A6%E3%82%A3%E3%83%83%E3%83%81-%E3%82%A2%E3%82%AB%E3%83%87%E3%83%9F%E3%82%A2': 'Little Witch Academia',
	'Lord-of-the-Rings': 'Lord of the Rings',
	'Lost-Girl': 'Lost Girl',
	'Lost': 'Lost',
	'Loud-House': 'Loud House',
	'Love-Hina': 'Love Hina',
	'Luke-Cage': 'Luke Cage',
	'Magical-Girl-Lyrical-Nanoha': 'Magical Girl Lyrical Nanoha',
	'Magic-The-Gathering': 'Magic: The Gathering',
	'Maid-Sama': 'Maid Sama!',
	'Man-from-Earth': 'Man from Earth',
	'Marco-Polo-2014': 'Marco Polo',
	'Maria-sama-ga-Miteru': 'Maria-sama ga Miteru',
	'Mario': 'Mario',
	'Marvel': 'Marvel',
	'Mass-Effect': 'Mass Effect',
	'Matrix': 'Matrix',
	'Merlin': 'Merlin',
	'Metal-Gear': 'Metal Gear',
	'Metroid': 'Metroid',
	'Miles-Vorkosigan': 'Miles Vorkosigan',
	'Misc-Anime-Manga': 'Miscellaneous Anime/Manga',
	'Misc-Books': 'Miscellaneous Books',
	'Misc-Games': 'Miscellaneous Games',
	'Misc-Movies': 'Miscellaneous Movies',
	'Misc-Tv-Shows': 'Miscellaneous TV Shows',
	'Mistborn-Trilogy': 'Mistborn',
	'Monster-Hunter': 'Monster Hunter',
	'Moonlight': 'Moonlight',
	'Movie-X-overs': '',
	'Mrs-Brown-s-Boys': "Mrs. Brown's Boys",
	'Mummy': 'Mummy',
	'Mushishi': 'Mushishi',
	'My-Hero-Academia-%E5%83%95%E3%81%AE%E3%83%92%E3%83%BC%E3%83%AD%E3%83%BC%E3%82%A2%E3%82%AB%E3%83%87%E3%83%9F%E3%82%A2': 'My Hero Academia',
	'My-Little-Pony': 'My Little Pony',
	'Mystic-Knights': 'Mystic Knights',
	'Mythology': '',
	'Naruto': 'Naruto',
	'NCIS': 'NCIS',
	'NCIS-Los-Angeles': 'NCIS',
	'NCIS-New-Orleans': 'NCIS',
	'Negima-Magister-Negi-Magi-%E9%AD%94%E6%B3%95%E5%85%88%E7%94%9F%E3%83%8D%E3%82%AE%E3%81%BE': 'Magical Teacher Negima',
	'Nier': 'Nier',
	'Night-Shift-2014': 'Night Shift',
	'Nikita': 'Nikita',
	'Noir': 'Noir',
	'Once-Upon-a-Time': 'Once Upon a Time',
	'One-Piece': 'One Piece',
	'One-Punch-Man-%E3%83%AF%E3%83%B3%E3%83%91%E3%83%B3%E3%83%9E%E3%83%B3': 'One Punch Man',
	'Originals': 'Originals',
	'Orphan-Black': 'Orphan Black',
	'Ouran-High-School-Host-Club': 'Ouran High School Host Club',
	'Overlord-%E3%82%AA%E3%83%BC%E3%83%90%E3%83%BC%E3%83%AD%E3%83%BC%E3%83%89': 'Overlord',
	'Overwatch': 'Overwatch',
	'Pacific-Rim': 'Pacific Rim',
	'Patriot': 'Patriot',
	'Percy-Jackson-and-the-Olympians': 'Percy Jackson and the Olympians',
	'Persona-Series': 'Persona',
	'Pippi-Longstocking': 'Pippin Longstocking',
	'Pirates-of-the-Caribbean': 'Pirates of the Caribbean',
	'Pok%C3%A9mon': 'Pokemon',
	'Popular': '',
	'Portal': 'Portal',
	'Power-Rangers': 'Power Rangers',
	'Pride-and-Prejudice': 'Pride and Prejudice',
	'Princess-Mononoke': 'Princess Mononoke',
	'Princess-Protection-Program': 'Princess Protection Program',
	'Princess-Series-Jim-C-Hines': 'Princess Series',
	'Prototype': 'Prototype',
	'Psych': 'Psych',
	'Punisher': 'Punisher',
	'Puella-Magi-Madoka-Magica-%E9%AD%94%E6%B3%95%E5%B0%91%E5%A5%B3%E3%81%BE%E3%81%A9%E3%81%8B-%E3%83%9E%E3%82%AE%E3%82%AB': 'Madoka Magica',
	'Quantum-Leap': 'Quantum Leap',
	'Rambo-series': 'Rambo',
	'Ranma': 'Ranma',
	'Red-Dwarf': 'Red Dwarf',
	'Red-vs-Blue': 'Red vs Blue',
	'Resident-Evil-series': 'Resident Evil',
	'Rise-Blood-Hunter': 'Rise: Blood Hunter',
	'Rizzoli-Isles': 'Rizzoli Isles',
	'Rome': 'Rome',
	'Roswell': 'Roswell',
	'Runaways': 'Runaways',
	'Rurouni-Kenshin': 'Rurouni Kenshin',
	'RWBY': 'RWBY',
	'Sabrina-1995': 'Sabrina',
	'Sailor-Moon': 'Sailor Moon',
	'Samurai-Jack': 'Samurai Jack',
	'Sanctuary': 'Sanctuary',
	'Sandman': 'Sandman',
	'Scooby-Doo': 'Scooby Doo',
	'Scorpion': 'Scorpion',
	'SCP-Foundation-Mythos': 'SCP Foundation',
	'Screenplays': 'Screenplays',
	'Secret-Garden': 'Secret Garden',
	'Sekirei': 'Sekirei',
	'Shadowrun': 'Shadowrun',
	'Shantae': 'Shantae',
	'Sherlock': 'Sherlock Holmes',
	'Skins': 'Skins',
	'Skip-Beat': 'Skip Beat!',
	'Sky-Captain-and-the-World-of-Tomorrow': 'Sky Captain and the World of Tomorrow',
	'Sky-High': 'Sky High',
	'Sleepless-In-Seattle': 'Sleepless In Seattle',
	'Smallville': 'Superman',
	'Sonic-the-Hedgehog': 'Sonic',
	'Sons-of-Anarchy': 'Sons of Anarchy',
	'Soul-Eater': 'Soul Eater',
	'South-Park': 'South Park',
	'Spartacus-Blood-and-Sand': 'Spartacus: Blood and Sand',
	'Spectacular-Spider-Man': 'Spiderman',
	'Spider-Man-The-Animated-Series': 'Spiderman',
	'Spyro-the-Dragon': 'Spyro the Dragon',
	'StarCraft': 'StarCraft',
	'Stargate-Atlantis': 'Stargate Atlantis',
	'Stargate-SG-1': 'Stargate SG-1',
	'Stargate-Universe': 'Stargate Universe',
	'Star-Trek-2009': 'Star Trek',
	'StarTrek-Enterprise': 'Star Trek',
	'Star-Trek-Online': 'Star Trek',
	'StarTrek-Other': 'Star Trek',
	'StarTrek-The-Next-Generation': 'Star Trek',
	'StarTrek-The-Original-Series': 'Star Trek',
	'StarTrek-Voyager': 'Star Trek',
	'Star-Wars-Rebels': 'Star Wars',
	'Star-Wars': 'Star Wars',
	'Star-Wars-The-Clone-Wars': 'Star Wars',
	'Steins-Gate-%E3%82%B7%E3%83%A5%E3%82%BF%E3%82%A4%E3%83%B3%E3%82%BA-%E3%82%B2%E3%83%BC%E3%83%88': 'Steins;Gate',
	'Stormlight-Archive': 'Stormlight Archive',
	'Strawberry-Panic': 'Strawberry Panic!',
	'Supergirl': 'Supergirl',
	'Superman': 'Superman',
	'Supernatural': 'Supernatural',
	'Super-Smash-Brothers': 'Super Smash Brothers',
	'Sword-Art-Online-%E3%82%BD%E3%83%BC%E3%83%89%E3%82%A2%E3%83%BC%E3%83%88-%E3%82%AA%E3%83%B3%E3%83%A9%E3%82%A4%E3%83%B3': 'Sword Art Online',
	'System-Shock': 'System Shock',
	'Tangled': 'Tangled',
	'Teen-Titans': 'Teen Titans',
	'Terminator-Sarah-Connor-Chronicles': 'Terminator: The Sarah Connor Chronicles',
	'Terminator': 'Terminator',
	'Thor': 'Thor',
	'Titanfall': 'Titanfall',
	'Toaru-Majutsu-no-Index-%E3%81%A8%E3%81%82%E3%82%8B%E9%AD%94%E8%A1%93%E3%81%AE%E7%A6%81%E6%9B%B8%E7%9B%AE%E9%8C%B2': 'A Certain Magical Index',
	'Tomb-Raider': 'Tomb Raider',
	'Torchwood': 'Torchwood',
	'Total-Annihilation': 'Total Annihilation',
	'Transformers-Beast-Wars': 'Transformers',
	'Trixie-Belden': 'Trixie Belden',
	'True-Blood': 'True Blood',
	'TV-X-overs': '',
	'Twilight': 'Twilight',
	'Undertale': 'Undertale',
	'Underworld': 'Underworld',
	'Uzumaki': 'Uzumaki',
	'Vampire-Diaries': 'Vampire Diaries',
	'Vampire-The-Masquerade': 'Vampire The Masquerade',
	'Veronica-Mars': 'Veronica Mars',
	'Wakfu': 'Wakfu',
	'Walking-Dead': 'Walking Dead',
	'Warcraft': 'Warcraft',
	'Warehouse-13': 'Warehouse 13',
	'Warframe': 'Warframe',
	'Warhammer': 'Warhammer',
	'Web-Shows': '',
	'Wentworth': 'Wentworth',
	'Where-on-Earth-is-Carmen-Sandiego': 'Where on Earth is Carmen Sandiego',
	'White-Collar': 'White Collar',
	'White-Wolf': 'White Wolf',
	'Wicked': 'Wicked',
	'Winnie-the-Pooh': 'Winnie the Pooh',
	'Witcher': 'Witcher',
	'Wonder-Woman': 'Wonder Woman',
	'World-of-Darkness': 'World of Darkness',
	'Worm': 'Worm',
	'X-Com': 'X-Com',
	'Xena-Warrior-Princess': 'Xena Warrior Princess',
	'X-Files': 'X-Files',
	'X-Men-Evolution': 'X-Men',
	'X-Men-The-Movie': 'X-Men',
	'x-men': 'X-Men',
	'X-Men': 'X-Men',
	'X-overs': '',
	'Yandere-Simulator': 'Yandere Simulator',
	'Young-Justice': 'Young Justice',
	'Yu-Yu-Hakusho': 'Yu Yu Hakusho',
}

ffNetFandomIdMap = {
	7: 'StarTrek-The-Next-Generation',
	8: 'Star-Wars',
	12: 'Babylon-5',
	13: 'Buffy-The-Vampire-Slayer',
	17: 'StarTrek-Voyager',
	21: 'Doctor-Who',
	22: 'StarTrek-Other',
	28: 'X-Men',
	29: 'X-overs',
	36: 'Misc-Anime-Manga',
	39: 'Sailor-Moon',
	50: 'Batman',
	51: 'Sandman',
	62: 'DC-Superheroes',
	65: 'Transformers-Beast-Wars',
	68: 'Stargate-SG-1',
	71: 'La-Femme-Nikita',
	74: 'Power-Rangers',
	80: 'Pok%C3%A9mon',
	83: 'Dragon-Ball-Z',
	85: 'Scooby-Doo',
	93: 'Ranma',
	109: 'Futurama',
	110: 'Matrix',
	119: 'Evangelion',
	123: 'Legend-of-Zelda',
	162: 'Misc-Games',
	183: 'Misc-Books',
	224: 'Harry-Potter',
	255: 'Angel',
	266: 'Calvin-Hobbes',
	291: 'White-Wolf',
	341: 'Red-Dwarf',
	347: 'Mario',
	351: 'Discworld',
	355: 'Rurouni-Kenshin',
	357: 'Marvel',
	361: 'StarCraft',
	382: 'Lord-of-the-Rings',
	424: 'X-Com',
	427: 'Diablo',
	431: 'Princess-Mononoke',
	432: 'Dune',
	436: 'Inuyasha',
	438: 'Tomb-Raider',
	447: 'Mummy',
	462: 'Total-Annihilation',
	480: 'Metal-Gear',
	512: 'Yu-Yu-Hakusho',
	513: 'Castlevania',
	542: 'Metroid',
	545: 'Anime-X-overs',
	546: 'Game-X-overs',
	548: 'TV-X-overs',
	550: 'Book-X-overs',
	551: 'Movie-X-overs',
	599: 'Half-Life',
	621: 'My-Little-Pony',
	632: 'His-Dark-Materials',
	640: 'Command-Conquer',
	703: 'Superman',
	716: 'X-Men-Evolution',
	721: 'X-Men-The-Movie',
	725: 'Fallout',
	735: 'Alpha-Centauri',
	762: 'Warhammer',
	771: 'Ironman',
	784: 'Love-Hina',
	885: 'Detective-Conan-Case-Closed',
	930: 'Doom',
	939: 'Big-O',
	992: 'A-Nightmare-on-Elm-Street',
	1035: 'Warcraft',
	1096: 'Buffy-X-overs',
	1116: 'Dungeons-and-Dragons',
	1182: 'Good-Omens',
	1244: 'Artemis-Fowl',
	1303: 'Smallville',
	1313: 'Darkstalkers',
	1335: 'Gunbuster',
	1337: 'Devil-May-Cry',
	1349: 'Gundam-UC',
	1353: 'Avengers',
	1356: 'Hellsing',
	1402: 'Naruto',
	1434: 'One-Piece',
	1462: 'Kim-Possible',
	1484: 'World-of-Darkness',
	1501: 'Shadowrun',
	1511: 'Jak-and-Daxter',
	1535: 'Jurassic-Park',
	1536: 'Firefly',
	1565: 'Magic-The-Gathering',
	1639: 'Teen-Titans',
	1668: 'NCIS',
	1681: 'Justice-League',
	1703: 'Fullmetal-Alchemist',
	1758: 'Bleach',
	1776: 'Danny-Phantom',
	1797: 'Haibane-Renmei',
	1825: 'Disgaea',
	1833: 'Stargate-Atlantis',
	1918: 'Punisher',
	1923: 'Alex-Rider',
	1955: 'Star-Wars',
	1960: 'Battlestar-Galactica-2003',
	1963: 'Gold-Digger',
	1968: 'House-M-D',
	1977: 'Death-Note',
	1992: 'Inheritance-Cycle',
	2002: 'Avatar-Last-Airbender',
	2102: 'Negima-Magister-Negi-Magi-%E9%AD%94%E6%B3%95%E5%85%88%E7%94%9F%E3%83%8D%E3%82%AE%E3%81%BE',
	2211: 'Sky-High',
	2237: 'Supernatural',
	2264: 'Dragonriders-of-Pern-series',
	2448: 'Magical-Girl-Lyrical-Nanoha',
	2458: 'Twilight',
	2464: 'Ben-10',
	2480: 'Ouran-High-School-Host-Club',
	2489: 'Dresden-Files',
	2508: 'Elder-Scroll-series',
	2622: 'Percy-Jackson-and-the-Olympians',
	2686: 'Heroes',
	2734: 'Katekyo-Hitman-Reborn',
	2745: 'Basilisk',
	2746: 'Fate-stay-night',
	2755: 'Code-Geass',
	2762: 'Familiar-of-Zero',
	2784: 'Kamen-Rider',
	2789: 'Torchwood',
	2799: 'Mushishi',
	2832: 'JoJo-s-Bizarre-Adventure',
	2924: 'Fairy-Tail',
	2927: 'Mass-Effect',
	2967: 'EVE-Online',
	2984: 'BioShock',
	2999: 'Soul-Eater',
	3077: 'Addams-Family',
	3075: 'Portal',
	3147: 'Wonder-Woman',
	3301: 'Merlin',
	3369: 'Sekirei',
	3423: 'Uzumaki',
	3530: 'Monster-Hunter',
	3624: 'Pride-and-Prejudice',
	3651: 'Hobbit',
	3733: 'Winnie-the-Pooh',
	3840: 'Fantastic-Four',
	3855: 'Toaru-Majutsu-no-Index-%E3%81%A8%E3%81%82%E3%82%8B%E9%AD%94%E8%A1%93%E3%81%AE%E7%A6%81%E6%9B%B8%E7%9B%AE%E9%8C%B2',
	4062: 'Mythology',
	4085: 'Star-Wars-The-Clone-Wars',
	4178: 'Chrome-Shelled-Regios',
	4254: 'A-song-of-Ice-and-Fire',
	4494: 'Castle',
	4501: 'Rambo-series',
	4524: 'Prototype',
	4834: 'Deadpool',
	4863: 'Star-Trek-2009',
	5217: 'Girl-Genius',
	5716: 'Dragon-Age',
	5763: 'Cthulhu-Mythos',
	5908: 'Avatar',
	6282: 'Web-Shows',
	6346: 'Mistborn-Trilogy',
	6445: 'Grim-Adventures-of-Billy-Mandy',
	6524: 'How-to-Train-Your-Dragon',
	6852: 'Man-from-Earth',
	6879: 'X-Men',
	6912: 'Nier',
	7014: 'A-for-Andromeda-1961',
	7186: 'Rizzoli-Isles',
	7190: 'Sherlock',
	7500: 'Hawaii-Five-0',
	7763: 'Walking-Dead',
	7815: 'Dracula',
	8004: 'Culture-Iain-M-Bank',
	8107: 'Puella-Magi-Madoka-Magica-%E9%AD%94%E6%B3%95%E5%B0%91%E5%A5%B3%E3%81%BE%E3%81%A9%E3%81%8B-%E3%83%9E%E3%82%AE%E3%82%AB',
	8282: 'Thor',
	8324: 'Game-of-Thrones',
	8365: 'Wakfu',
	8388: 'x-men',
	8665: 'Sword-Art-Online-%E3%82%BD%E3%83%BC%E3%83%89%E3%82%A2%E3%83%BC%E3%83%88-%E3%82%AA%E3%83%B3%E3%83%A9%E3%82%A4%E3%83%B3',
	8719: 'Witcher',
	8802: 'Steins-Gate-%E3%82%B7%E3%83%A5%E3%82%BF%E3%82%A4%E3%83%B3%E3%82%BA-%E3%82%B2%E3%83%BC%E3%83%88',
	8810: 'Captain-America',
	8848: 'Shantae',
	9211: 'Grimm',
	9295: 'System-Shock',
	9310: 'Dark-Souls',
	9502: 'High-School-DxD-%E3%83%8F%E3%82%A4%E3%82%B9%E3%82%AF%E3%83%BC%E3%83%ABD-D',
	9621: 'Star-Trek-Online',
	9742: 'Attack-on-Titan-%E9%80%B2%E6%92%83%E3%81%AE%E5%B7%A8%E4%BA%BA',
	9727: 'Dota-2',
	9748: 'Legend-of-Korra',
	9786: 'Avengers',
	9996: 'Red-vs-Blue',
	10009: 'Gravity-Falls',
	10073: 'Arrow',
	10100: 'Dishonored',
	10131: 'Campione-%E3%82%AB%E3%83%B3%E3%83%94%E3%82%AA%E3%83%BC%E3%83%8D',
	10353: 'Mrs-Brown-s-Boys',
	10387: 'Warframe',
	10582: 'Little-Witch-Academia-%E3%83%AA%E3%83%88%E3%83%AB-%E3%82%A6%E3%82%A3%E3%83%83%E3%83%81-%E3%82%A2%E3%82%AB%E3%83%87%E3%83%9F%E3%82%A2',
	10786: 'Pacific-Rim',
	10833: 'RWBY',
	10867: 'Worm',
	10883: 'Originals',
	10896: 'Frozen',
	11015: 'A-Certain-Scientific-Railgun-%E3%81%A8%E3%81%82%E3%82%8B%E7%A7%91%E5%AD%A6%E3%81%AE%E8%B6%85%E9%9B%BB%E7%A3%81%E7%A0%B2',
	11059: 'Arpeggio-of-Blue-Steel-%E8%92%BC%E3%81%8D%E9%8B%BC%E3%81%AE%E3%82%A2%E3%83%AB%E3%83%9A%E3%82%B8%E3%82%AA',
	11392: 'Titanfall',
	11559: 'Destiny',
	11242: 'Stormlight-Archive',
	11297: 'One-Punch-Man-%E3%83%AF%E3%83%B3%E3%83%91%E3%83%B3%E3%83%9E%E3%83%B3',
	11875: 'Overwatch',
	12047: 'John-Wick',
	12415: 'Darkest-Dungeon',
	12493: 'Overlord-%E3%82%AA%E3%83%BC%E3%83%90%E3%83%BC%E3%83%AD%E3%83%BC%E3%83%89',
	12496: 'SCP-Foundation-Mythos',
	12585: 'Undertale',
	12930: 'Yandere-Simulator',
	13176: 'Luke-Cage',
	13878: 'Black-Panther',
}
# yapf: enable


class FFNAdapter(Adapter):
	def __init__(self) -> None:
		super().__init__(
			True, 'https://www.fanfiction.net', 'fanfiction.net', FicType.ff_net,
			'ffn'
		)

	def constructUrl(
		self,
		storyId: str,
		chapterId: Optional[int] = None,
		title: Optional[str] = None
	) -> str:
		if chapterId is None:
			return '{}/s/{}'.format(self.baseUrl, storyId)
		if title is None:
			return '{}/s/{}/{}'.format(self.baseUrl, storyId, chapterId)
		return '{}/s/{}/{}/{}'.format(
			self.baseUrl, storyId, chapterId, util.urlTitle(title)
		)

	def buildUrl(self, chapter: 'FicChapter') -> str:
		# TODO: do we need these 2 lines or will they always be done by however
		# FicChapter is created?
		if chapter.fic is None:
			chapter.fic = Fic.lookup((chapter.ficId, ))
		return self.constructUrl(
			chapter.fic.localId, chapter.chapterId, chapter.fic.title
		)

	def tryParseUrl(self, url: str) -> Optional[FicId]:
		if url.find('?') >= 0:
			url = url.split('?')[0]
		parts = url.split('/')
		httpOrHttps = (parts[0] == 'https:' or parts[0] == 'http:')
		if len(parts) < 5:
			return None
		if (not parts[2].endswith(self.urlFragments[0])) or (not httpOrHttps):
			return None
		if parts[3] != 's' and parts[3] != 'r':
			return None
		if (
			len(parts) < 5 or len(parts[4].strip()) < 1
			or not parts[4].strip().isnumeric()
		):
			return None

		storyId = int(parts[4])
		chapterId = None
		ambi = True
		if (
			len(parts) >= 6 and parts[3] == 's' and len(parts[5].strip()) > 0
			and parts[5].strip().isnumeric()
		):
			chapterId = int(parts[5].strip())
			ambi = False
		# upstream supports a chapter id after the story slug too, but it does not
		# normally generate such urls -- only use it as a fallback
		if (
			ambi and len(parts) >= 7 and parts[3] == 's' and len(parts[6].strip()) > 0
			and parts[6].strip().isnumeric()
		):
			chapterId = int(parts[6].strip())
			ambi = False
		return FicId(self.ftype, str(storyId), chapterId, ambi)

	def create(self, fic: Fic) -> Fic:
		fic.url = self.constructUrl(fic.localId, 1)

		# scrape fresh info
		data = self.scrape(fic.url)['raw']
		#data = self.softScrape(fic.url)

		fic = self.parseInfoInto(fic, data)
		fic.upsert()

		chapter = fic.chapter(1)
		chapter.url = fic.url
		chapter.setHtml(data)
		chapter.upsert()

		return Fic.lookup((fic.id, ))

	def getFromZList(self, localId: int, ts: int, html: str) -> Fic:
		fic = None
		existing = Fic.select({'sourceId': self.ftype, 'localId': str(localId)})
		if len(existing) != 1:
			fic = Fic.new()
			fic.sourceId = self.ftype
			fic.localId = str(localId)
			fic.created = OilTimestamp.now()
		else:
			fic = existing[0]
		return self.createFromZList(fic, ts, html)

	def createFromZList(self, fic: Fic, ts: int, data: str) -> Fic:
		fic.url = self.constructUrl(fic.localId, 1)

		fic = self.parseZListInfoInto(fic, ts, data)
		fic.upsert()

		return Fic.lookup((fic.id, ))

	def extractContent(self, fic: Fic, html: str) -> str:
		if (
			html.lower().find('chapter not found.') != -1
			and html.lower().find("id='storytext'") == -1
		):
			raise Exception('unable to find chapter content')
		lines = html.replace('\r', '\n').replace('>', '>\n').split('\n')
		parts: List[str] = []
		inStory = False
		for line in lines:
			if line.find("id='storytext'") != -1 or line.find('id="storytext"') != -1:
				inStory = True
			if inStory:
				if (
					line.find("SELECT id=chap_select") != -1
					or line.lower().find('<script') != -1
				):
					inStory = False
					break
				parts += [line]
		while len(parts) > 0 and (
			parts[-1].startswith('&lt; Prev</button')
			or parts[-1].startswith('<button class=btn TYPE=BUTTON')
		):
			parts = parts[:-1]
		return ' '.join(parts)

	def canonizeUrl(self, url: str) -> str:
		fid = self.tryParseUrl(url)
		if fid is None: raise ValueError
		return self.constructUrl(fid.localId, fid.chapterId)

	def getCurrentInfo(self, fic: Fic) -> Fic:
		# scrape fresh info
		# FIXME if we do this we lose a periodic record of meta
		#data = scrape.scrape(self.constructUrl(
		#		fic.localId, fic.chapterCount + 1, fic.title))
		#if str(data).find('Chapter not found.') >= 0:
		#	data = self.scrape(self.constructUrl(fic.localId, 1))
		data = self.scrape(self.constructUrl(fic.localId, 1))

		return self.parseInfoInto(fic, data['raw'])

	def handleFandom(self, fic: Fic, fandom: str) -> List[Fandom]:
		# save raw/messy fandom
		fandoms = [Fandom.define(fandom, sourceId=self.ftype)]

		# ensure messy is in our map
		if fandom not in ffNetFandomMap:
			util.logMessage('unknown fandom: {} (from {})'.format(fandom, fic.url))
		else:
			fandoms.append(Fandom.define(ffNetFandomMap[fandom]))

		return fandoms

	def handleCrossoverFandom(
		self, fic: Fic, fandom: str, fIds: List[int], href: str
	) -> List[Fandom]:
		# save raw/messy fandom
		fandoms = [Fandom.define(fandom, sourceId=self.ftype)]

		# ensure fandom ids are in our map

		# check for missing id maps
		missingIds = [fId for fId in fIds if fId not in ffNetFandomIdMap]
		if len(missingIds) > 0:
			util.logMessage(
				'unknown fandom ids: {} from {} in {}'.format(
					missingIds, href, fic.url
				)
			)
			return fandoms

		# translate to messy
		messys = [ffNetFandomIdMap[fId] for fId in fIds]
		# check for missing messy
		missingMessy = [m for m in messys if m not in ffNetFandomMap]
		if len(missingMessy) > 0:
			util.logMessage(
				'unknown messy fandom: {} from {}'.format(missingMessy, href)
			)
			return fandoms

		# check crossover value
		expected = '{}_and_{}_Crossovers'.format(messys[0], messys[1])
		if expected != fandom:
			util.logMessage(
				'crossover got "{}" expected "{}"'.format(fandom, expected)
			)
			return fandoms

		# map messy to clean
		cleans = [ffNetFandomMap[m] for m in messys]
		for clean in cleans:
			if len(clean) > 0:
				fandoms.append(Fandom.define(clean))
		return fandoms

	def parseInfoInto(self, fic: Fic, wwwHtml: str) -> Fic:
		from bs4 import BeautifulSoup
		deletedFicTexts = [
			# probably deleted by user
			'Story Not FoundUnable to locate story. Code 1.',
			# probably deleted by admin
			'Story Not FoundUnable to locate story. Code 2.',
			# unknown
			'Story Not FoundStory is unavailable for reading. (A)',
		]
		soup = BeautifulSoup(wwwHtml, 'html5lib')
		profile_top = soup.find(id='profile_top')
		# story might've been deleted
		if profile_top is None:
			gui_warnings = soup.find_all('span', {'class': 'gui_warning'})
			for gui_warning in gui_warnings:
				for deletedFicText in deletedFicTexts:
					if gui_warning.get_text() == deletedFicText:
						if fic.ficStatus != FicStatus.complete:
							fic.ficStatus = FicStatus.abandoned
						fic.upsert()
						return fic

		text = profile_top.get_text()
		pt_str = str(profile_top)

		fic.fetched = OilTimestamp.now()
		fic.languageId = Language.getId("English")  # TODO: don't hard code?

		for b in profile_top.find_all('b'):
			b_class = b.get('class')
			if len(b_class) == 1 and b_class[0] == 'xcontrast_txt':
				fic.title = b.get_text()
				break
		else:
			raise Exception('error: unable to find title:\n{}\n'.format(pt_str))

		fic.url = self.constructUrl(fic.localId, 1, fic.title)

		descriptionFound = False
		for div in profile_top.find_all('div'):
			div_class = div.get('class')
			if (
				div.get('style') == 'margin-top:2px' and len(div_class) == 1
				and div_class[0] == 'xcontrast_txt'
			):
				fic.description = div.get_text()
				descriptionFound = True
				break
		if descriptionFound == False:
			raise Exception('error: unable to find description:\n{}\n'.format(pt_str))

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		# TODO we should match this only on the section following the description
		matcher = RegexMatcher(
			text, {
				'ageRating': ('Rated:\s+Fiction\s*(\S+)', str),
				'chapterCount?': ('Chapters:\s+(\d+)', int),
				'wordCount': ('Words:\s+(\S+)', int),
				'reviewCount?': ('Reviews:\s+(\S+)', int),
				'favoriteCount?': ('Favs:\s+(\S+)', int),
				'followCount?': ('Follows:\s+(\S+)', int),
				'updated?': ('Rated:.*Updated:\s+(\S+)', str),
				'published': ('Published:\s+([^-]+)', str),
			}
		)
		matcher.matchAll(fic)

		if fic.published is not None:
			publishedUts = util.parseDateAsUnix(fic.published, fic.fetched)
			fic.published = OilTimestamp(publishedUts)

		if fic.updated is None:
			fic.updated = fic.published
		elif fic.updated is not None:
			updatedUts = util.parseDateAsUnix(fic.updated, fic.fetched)
			fic.updated = OilTimestamp(updatedUts)

		if fic.chapterCount is None:
			fic.chapterCount = 1

		match = re.search(
			'(Rated|Chapters|Words|Updated|Published):.*Status:\s+(\S+)', text
		)
		if match is None:
			fic.ficStatus = FicStatus.ongoing
		else:
			status = match.group(2)
			if status == 'Complete':
				fic.ficStatus = FicStatus.complete
			else:
				raise Exception('unknown status: {}: {}'.format(fic.url, status))

		for a in profile_top.find_all('a'):
			a_href = a.get('href')
			if a_href.startswith('/u/'):
				author = a.get_text()
				authorUrl = self.baseUrl + a_href
				authorId = a_href.split('/')[2]
				self.setAuthor(fic, author, authorUrl, authorId)
				break
		else:
			raise Exception('unable to find author:\n{}'.format(text))

		preStoryLinks = soup.find(id='pre_story_links')
		preStoryLinksLinks = []
		if preStoryLinks is not None:
			preStoryLinksLinks = preStoryLinks.find_all('a')
		pendingFandoms: List[Fandom] = []
		for a in preStoryLinksLinks:
			href = a.get('href')
			hrefParts = href.split('/')

			# if it's a top level category
			if (
				len(hrefParts) == 3 and len(hrefParts[0]) == 0
				and len(hrefParts[2]) == 0
			):
				cat = hrefParts[1]
				if cat in ffNetFandomCategories:
					continue  # skip categories
				raise Exception('unknown category: {}'.format(cat))

			# if it's a crossover /Fandom1_and_Fandm2_Crossovers/f1id/f2id/
			if (
				len(hrefParts) == 5 and hrefParts[1].endswith("_Crossovers")
				and len(hrefParts[0]) == 0 and len(hrefParts[4]) == 0
			):
				fIds = [int(hrefParts[2]), int(hrefParts[3])]
				pendingFandoms += self.handleCrossoverFandom(
					fic, hrefParts[1], fIds, href
				)
				continue

			# if it's a regular fandom in some category
			if (
				len(hrefParts) == 4 and len(hrefParts[0]) == 0
				and len(hrefParts[3]) == 0
			):
				# ensure category is in our map
				if hrefParts[1] not in ffNetFandomCategories:
					raise Exception('unknown category: {}'.format(hrefParts[1]))

				pendingFandoms += self.handleFandom(fic, hrefParts[2])
				continue

			util.logMessage('unknown fandom {0}: {1}'.format(fic.id, href))

		fic.upsert()
		poss = Fic.select({'sourceId': fic.sourceId, 'localId': fic.localId})
		if len(poss) != 1:
			raise Exception(f'unable to upsert fic?')
		fic = poss[0]
		for pfandom in pendingFandoms:
			fic.add(pfandom)

		if fic.chapterCount is None:
			return fic

		chapterTitles = []
		if fic.chapterCount > 1:
			chapterSelect = soup.find(id='chap_select')
			chapterOptions = []
			if chapterSelect is not None:
				chapterOptions = chapterSelect.findAll('option')
			chapterTitles = [co.getText().strip() for co in chapterOptions]

		for cid in range(1, fic.chapterCount + 1):
			ch = fic.chapter(cid)
			ch.localChapterId = str(cid)
			ch.url = self.constructUrl(fic.localId, cid)
			if len(chapterTitles) > cid:
				ch.title = util.cleanChapterTitle(chapterTitles[cid - 1], cid)
			elif fic.chapterCount == 1 and cid == 1:
				ch.title = fic.title
			ch.upsert()

		metaSpan = profile_top.find('span', {'class': 'xgray'})
		if metaSpan is not None:
			try:
				res = self.parseFicMetaSpan(metaSpan.decode_contents())
				#fic.language = res["language"]

				# reconstruct
				fields = [
					('rated', 'Rated: Fiction ZZZ'),
					('language', 'Language: ZZZ'),
					('genres', 'Genre: ZZZ'),
					('characters', 'Characters: ZZZ'),
					('reviews', 'Reviews: ZZZ'),
					('favorites', 'Favs: ZZZ'),
					('follows', 'Follows: ZZZ'),
				]
				rmeta = ' - '.join(
					[f[1].replace('ZZZ', res[f[0]]) for f in fields if f[0] in res]
				)

				fic.extraMeta = rmeta
				publishedUts = util.parseDateAsUnix(res['published'], fic.fetched)
				fic.published = OilTimestamp(publishedUts)
				fic.updated = fic.published
				if 'updated' in res:
					updatedUts = util.parseDateAsUnix(res['updated'], fic.fetched)
					fic.updated = OilTimestamp(updatedUts)
				fic.upsert()

			except Exception as e:
				util.logMessage(
					f'FFNAdapter.parseInfoInto: .parseFicMetaSpan:\n{e}\n{traceback.format_exc()}'
				)
				util.logMessage(
					f'FFNAdapter.parseFicMetaSpan: {metaSpan.decode_contents()}'
				)
				pass

		return fic

	def parseFicMetaSpan(self, metaSpan: str) -> Dict[str, str]:
		#util.logMessage(f'FFNAdapter.parseFicMetaSpan: {metaSpan}')
		#   Rated: (ageRating)
		#   language
		#   optional genre(/genre)
		#   optional chars
		#   optional Chapters: (chapterCount)
		#   Words: (commaWords)
		#   optional Reviews: (commaReviews)
		#   optional Favs: (commaFavs)
		#   optional Follows: (commaFollows)
		#   optional Updated: (texty date)
		#   Published: (texty date)
		#   optional Status: Complete
		#   id: (fid)

		text = metaSpan.strip()
		res = {}

		keys = [
			('rated', "Rated:\s+<[^>]*>Fiction\s*(K|K\+|T|M)<[^>]*>"),
		]

		for n, kre in keys:
			optional = n.endswith('?')
			n = n.rstrip('?')
			kre = f'^{kre}($| - )'
			#print(n, kre)

			match = re.search(kre, text)
			if match is not None:
				res[n] = match.group(1)
				text = text[len(match.group(0)):].strip()
			elif not optional:
				raise Exception(f'error: cannot find {n} in {text}')

		tend = text.find(' - ')
		language, text = text[:tend], text[tend + len(' - '):]
		res['language'] = language

		rkeys = [
			('id', "id:\s+(\d+)"),
			('status?', "Status:\s+(\S+)"),
			(
				'published',
				"Published:\s+<span data-xutime=['\"](\d+)['\"]>(\S+)</span>"
			),
			('updated?', "Updated:\s+<span data-xutime=['\"](\d+)['\"]>(\S+)</span>"),
			('follows?', "Follows:\s+(\S+)"),
			('favorites?', "Favs:\s+(\S+)"),
			('reviews?', "Reviews:\s+<[^>]*>(\S+)<[^>]*>"),
			('words', "Words:\s+(\S+)"),
			('chapters?', "Chapters:\s+(\S+)"),
		]

		for n, kre in rkeys:
			optional = n.endswith('?')
			n = n.rstrip('?')
			kre = f'(^| - ){kre}$'
			#print(n, kre)

			match = re.search(kre, text)
			if match is not None:
				res[n] = match.group(2)
				text = text[:-len(match.group(0))].strip()
			elif not optional:
				raise Exception(f'error: cannot find {n} in {text}')

		if text.find(' - ') >= 0:
			tend = text.find(' - ')
			genres, chars = text[:tend], text[tend + len(' - '):]
			res['genres'] = genres.strip()
			res['characters'] = chars.strip()
			text = ''
		elif len(text) > 0 and text in ffNetGenres:
			res['genres'] = text
			text = ''
		elif len(text) > 0:
			# we have either an option genre(/genre) OR an optional chars
			for g1 in ffNetGenres:
				if len(text) < 1:
					break
				for g2 in ffNetGenres:
					if text == f'{g1}/{g2}':
						res['genres'] = text
						text = ''
						break

		if len(text) > 0:
			res['characters'] = text

		return res

	def parseZListInfoInto(self, fic: Fic, ts: int, html: str) -> Fic:
		# existing data is newer, do nothing
		if fic.fetched is not None and fic.fetched.toUTS() > ts:
			return fic
		from bs4 import BeautifulSoup

		soup = BeautifulSoup(html, 'html5lib')

		text = soup.get_text()
		pt_str = str(html)

		fic.fetched = OilTimestamp(ts)
		fic.languageId = Language.getId("English")  # TODO: don't hard code?

		fic.url = self.constructUrl(fic.localId, 1, fic.title)

		# default optional fields
		fic.reviewCount = 0
		fic.favoriteCount = 0
		fic.followCount = 0

		for a in soup.find_all('a', {'class': 'stitle'}):
			fic.title = a.getText()
			break
		else:
			raise Exception('error: unable to find title:\n{}\n'.format(pt_str))

		for div in soup.find_all('div', {'class': 'z-padtop'}):
			fic.description = div.contents[0]
			break
		else:
			raise Exception('error: unable to find description:\n{}\n'.format(pt_str))

		matcher = RegexMatcher(
			text, {
				'ageRating': ('Rated:\s+(?:Fiction)?\s*(\S+)', str),
				'chapterCount?': ('Chapters:\s+(\d+)', int),
				'wordCount': ('Words:\s+(\S+)', int),
				'reviewCount?': ('Reviews:\s+(\S+)', int),
				'favoriteCount?': ('Favs:\s+(\S+)', int),
				'followCount?': ('Follows:\s+(\S+)', int),
				'updated?': ('Updated:\s+(\S+)', str),
				'published': ('Published:\s+([^-]+)', str),
			}
		)
		matcher.matchAll(fic)

		if fic.published is not None:
			publishedUts = util.parseDateAsUnix(fic.published, fic.fetched)
			fic.published = OilTimestamp(publishedUts)

		if fic.updated is None:
			fic.updated = fic.published
		elif fic.updated is not None:
			updatedUts = util.parseDateAsUnix(fic.updated, fic.fetched)
			fic.updated = OilTimestamp(updatedUts)

		if fic.chapterCount is None:
			fic.chapterCount = 1

		match = re.search(
			'(Rated|Chapters|Words|Updated|Published):.*-\s+(Complete)', text
		)
		if match is None:
			fic.ficStatus = FicStatus.ongoing
		else:
			status = match.group(2)
			if status == 'Complete':
				fic.ficStatus = FicStatus.complete
			else:
				raise Exception('unknown status: {}: {}'.format(fic.url, status))

		for a in soup.find_all('a'):
			a_href = a.get('href')
			if a_href.startswith('/u/'):
				author = a.get_text()
				authorUrl = self.baseUrl + a_href
				authorId = a_href.split('/')[2]
				self.setAuthor(fic, author, authorUrl, authorId)
				break
		else:
			raise Exception('unable to find author:\n{}'.format(text))

		zl = soup.find('div', {'class': 'z-list'})
		fan = None if zl is None else zl.get('data-category')
		pendingFandoms: List[Fandom] = []
		if fan is not None:
			pendingFandoms += self.handleFandom(fic, fan)
			# TODO: crossovers?

		#print('---')
		#print(fic.__dict__)
		#raise Exception('todo')

		fic.upsert()
		for pfandom in pendingFandoms:
			fic.add(pfandom)

		return fic

	def scrape(self, url: str) -> scrape.ScrapeMeta:
		return skitter.scrape(url)

	def softScrape(self, chapter: FicChapter) -> str:
		if chapter.url is None:
			chapter.url = self.buildUrl(chapter)  # type: ignore
			chapter.localChapterId = str(chapter.chapterId)
			chapter.upsert()
		fic = chapter.getFic()

		# TODO should we be passing '%' instead of chapter.fic.title ?
		#url = scrape.getLastUrlLikeOrDefault(
		#		(self.constructUrl(fic.localId, chapter.chapterId, None),
		#		self.constructUrl(fic.localId, chapter.chapterId, fic.title)))
		curl = self.constructUrl(fic.localId, chapter.chapterId, None)
		#util.logMessage(f'FFNAdapter.scrape: {curl}')
		url = scrape.getLastUrlLike(curl)
		if url is None:
			url = curl

		data = str(skitter.softScrape(url)['raw'])

		if data is None:
			raise Exception('unable to scrape? FIXME')
		if (
			data.lower().find('chapter not found.') != -1
			and data.lower().find("id='storytext'") == -1
		):
			ts = scrape.getMostRecentScrapeTime(url)
			if ts is None:
				raise Exception('no most recent scrape time? FIXME')
			# if we last scraped more than half an hour ago rescrape
			if int(time.time()) - ts > (60 * 30):
				url = self.constructUrl(fic.localId, chapter.chapterId, None)
				data = self.scrape(url)['raw']
		if data is None:
			raise Exception('unable to scrape? FIXME')

		if (
			data.lower().find('chapter not found.') != -1
			and data.lower().find("id='storytext'") == -1
		):
			raise Exception('unable to find chapter content {}'.format(url))

		return data
