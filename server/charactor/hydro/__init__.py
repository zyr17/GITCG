from .mona import Mona, ProphecyOfSubmersion, Reflection
from .barbara import Barbara, MelodyLoop, GloriousSeason
from .rhodeia import RhodeiaOfLoch, StreamingSurge, Frog, Squirrel, Raptor
from .xingqiu import Xingqiu, TheScentRemained
from .tartaglia import Tartaglia, AbyssalMayhemHydrospout
from .sangonomiya_kokomi import (
    SangonomiyaKokomi, BakeKurage, TamakushiCasket
)
from .candace import Candace, TheOverflow


HydroCharactors = (
    Mona | Barbara | RhodeiaOfLoch | Xingqiu | Tartaglia | SangonomiyaKokomi
    | Candace
)
SummonsOfHydroCharactors = (
    Reflection | MelodyLoop | Frog | Squirrel | Raptor | BakeKurage
)
HydroCharactorTalents = (
    ProphecyOfSubmersion | GloriousSeason | StreamingSurge | TheScentRemained
    | AbyssalMayhemHydrospout | TamakushiCasket | TheOverflow
)
