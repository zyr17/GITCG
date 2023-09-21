from .companions import Companions
from .locations import Locations
from .items import Items
from .old_version import OldVersionLocations


Supports = (
    Locations | Companions | Items
    # finally old version cards
    | OldVersionLocations
)
