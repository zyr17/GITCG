from typing import Literal, List
from ...consts import ObjectType
from ..base import StatusBase
from ...action import RemoveObjectAction, Actions
from ...event import RoundEndEventArguments


class CharactorStatusBase(StatusBase):
    """
    Base class of charactor status.
    """
    type: Literal[ObjectType.CHARACTOR_STATUS] = ObjectType.CHARACTOR_STATUS


class UsageCharactorStatus(CharactorStatusBase):
    """
    Base class of team status that based on usages.
    It will implement a method to check if run out of usage; when run out
    of usage, it will remove itself.
    """
    name: Literal['UsageCharactorStatus'] = 'UsageCharactorStatus'
    max_usage: int = 999

    def check_remove_triggered(self) -> List[Actions]:
        """
        Check if the status should be removed.
        when usage has changed, call this function to check if the status
        should be removed.
        """
        if self.usage <= 0:
            return [RemoveObjectAction(
                object_position = self.position,
                object_id = self.id,
            )]
        return []


class RoundCharactorStatus(CharactorStatusBase):
    """
    Base class of team status that based on rounds.  It will implement the 
    event trigger on ROUND_END to check if run out of usages; when run out
    of usages, it will remove itself.
    """
    name: Literal['RoundCharactorStatus'] = 'RoundCharactorStatus'
    usage: int
    max_usage: int = 999

    def check_should_remove(self) -> List[RemoveObjectAction]:
        """
        Check if the status should be removed.
        when round has changed, call this function to check if the status
        should be removed.
        """
        if self.usage <= 0:
            return [RemoveObjectAction(
                object_position = self.position,
                object_id = self.id,
            )]
        return []

    def event_handler_ROUND_END(self, event: RoundEndEventArguments) \
            -> List[Actions]:
        """
        After round ending, check whether the round status should be removed.
        """
        self.usage -= 1
        return list(self.check_should_remove())
