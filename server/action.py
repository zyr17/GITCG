from enum import Enum
from utils import BaseModel
from typing import Literal, List
from .interaction import (
    ResponseBase,
    ChooseCharactorResponse,
    RerollDiceResponse,
    DeclareRoundEndResponse,
    SwitchCharactorResponse,
)
from .consts import DieColor
from .modifiable_values import DamageValue


class ActionTypes(str, Enum):
    EMPTY = 'EMPTY'
    DRAW_CARD = 'DRAW_CARD'
    RESTORE_CARD = 'RESTORE_CARD'
    REMOVE_CARD = 'REMOVE_CARD'
    CHOOSE_CHARACTOR = 'CHOOSE_CHARACTOR'
    CREATE_DICE = 'CREATE_DICE'
    REMOVE_DICE = 'REMOVE_DICE'
    DECLARE_ROUND_END = 'DECLARE_ROUND_END'
    COMBAT_ACTION = 'COMBAT_ACTION'
    SWITCH_CHARACTOR = 'SWITCH_CHARACTOR'
    CHARGE = 'CHARGE'
    SKILL_END = 'SKILL_END'
    CHARACTOR_DEFEATED = 'CHARACTOR_DEFEATED'

    # system phase actions
    ROUND_PREPARE = 'ROUND_PREPARE'
    ROUND_END = 'ROUND_END'

    # make damage related events
    RECEIVE_DAMAGE = 'RECEIVE_DAMAGE'
    MAKE_DAMAGE = 'MAKE_DAMAGE'
    AFTER_MAKE_DAMAGE = 'AFTER_MAKE_DAMAGE'

    # generate request actions
    GENERATE_CHOOSE_CHARACTOR = 'GENERATE_CHOOSE_CHARACTOR'


class ActionBase(BaseModel):
    """
    Base class for game actions.
    An action contains arguments to make changes to the game table.

    Attributes:
        action_type (Literal[ActionTypes]): The type of the action.
    """
    type: Literal[ActionTypes.EMPTY] = ActionTypes.EMPTY


class DrawCardAction(ActionBase):
    """
    Action for drawing cards.
    """
    type: Literal[ActionTypes.DRAW_CARD] = ActionTypes.DRAW_CARD
    player_id: int
    number: int


class RestoreCardAction(ActionBase):
    """
    Action for restoring cards.
    """
    type: Literal[ActionTypes.RESTORE_CARD] = ActionTypes.RESTORE_CARD
    player_id: int
    card_ids: List[int]


class RemoveCardAction(ActionBase):
    """
    Action for removing cards.
    """
    type: Literal[ActionTypes.REMOVE_CARD] = ActionTypes.REMOVE_CARD
    player_id: int
    card_id: int
    card_position: Literal['HAND', 'DECK']
    remove_type: Literal['USED', 'BURNED']


class ChooseCharactorAction(ActionBase):
    """
    Action for choosing charactors.
    """
    type: Literal[ActionTypes.CHOOSE_CHARACTOR] = ActionTypes.CHOOSE_CHARACTOR
    player_id: int
    charactor_id: int

    @classmethod
    def from_response(cls, response: ChooseCharactorResponse):
        """
        Generate ChooseCharactorAction from ChooseCharactorResponse.
        """
        return cls(
            player_id = response.player_id,
            charactor_id = response.charactor_id,
        )


class CreateDiceAction(ActionBase):
    """
    Action for creating dice.

    Args:
        player_id (int): The ID of the player to create the dice for.
        number (int): The number of dice to create.
        color (DieColor | None): The color of the dice to create. If None,
            the following generate rules will be activated.
        random (bool): Whether to randomly generate the color of dice.
        different (bool): Whether to generate different colors of dice.
    """
    type: Literal[ActionTypes.CREATE_DICE] = ActionTypes.CREATE_DICE
    player_id: int
    number: int
    color: DieColor | None = None
    random: bool = False
    different: bool = False


class RemoveDiceAction(ActionBase):
    """
    Action for removing dice.

    Args:
        player_id (int): The ID of the player to remove the dice for.
        dice_ids (List[int]): The IDs of the dice to remove.
    """
    type: Literal[ActionTypes.REMOVE_DICE] = ActionTypes.REMOVE_DICE
    player_id: int
    dice_ids: List[int]

    @classmethod
    def from_response(cls, response: RerollDiceResponse):
        """
        Generate RemoveDiceAction from RerollDiceResponse.
        TODO: from other responses, i.e. use skill response.
        """
        return cls(
            player_id = response.player_id,
            dice_ids = response.reroll_dice_ids,
        )


class DeclareRoundEndAction(ActionBase):
    """
    Action for declaring the end of the round.
    """
    type: Literal[ActionTypes.DECLARE_ROUND_END] = \
        ActionTypes.DECLARE_ROUND_END
    player_id: int

    @classmethod
    def from_response(cls, response: DeclareRoundEndResponse):
        """
        Generate DeclareRoundEndAction from DeclareRoundEndResponse.
        """
        return cls(
            player_id = response.player_id,
        )


class CombatActionAction(ActionBase):
    """
    Action for combat.
    """
    type: Literal[ActionTypes.COMBAT_ACTION] = ActionTypes.COMBAT_ACTION
    player_id: int

    @classmethod
    def from_response(cls, response: ResponseBase):
        """
        Generate CombatActionAction from Responses.
        """
        return cls(
            player_id = response.player_id,
        )


class SwitchCharactorAction(ActionBase):
    """
    Action for switching charactor.
    """
    type: Literal[ActionTypes.SWITCH_CHARACTOR] = ActionTypes.SWITCH_CHARACTOR
    player_id: int
    charactor_id: int

    @classmethod
    def from_response(cls, response: SwitchCharactorResponse):
        """
        Generate SwitchCharactorAction from SwitchCharactorResponse.
        """
        return cls(
            player_id = response.player_id,
            charactor_id = response.charactor_id,
        )


class MakeDamageAction(ActionBase):
    """
    Action for making damage. Heal treats as negative damage. Elemental 
    applies to the charactor (e.g. Kokomi) treats as zero damage.

    Args:
        player_id (int): The ID of the player to make damage from.
        damage_value_list (List[DamageValue]): The damage values to make.
        target_id (int): The ID of the player to make damage to.
        change_charactor (int): Change to charactor ID, if not change, ID
            should same as current active charactor ID.
    """
    type: Literal[ActionTypes.MAKE_DAMAGE] = ActionTypes.MAKE_DAMAGE
    player_id: int
    damage_value_list: List[DamageValue]
    target_id: int
    change_charactor: int


class ChargeAction(ActionBase):
    """
    Action for charging.
    """
    type: Literal[ActionTypes.CHARGE] = ActionTypes.CHARGE
    player_id: int
    charactor_id: int
    charge: int


class SkillEndAction(ActionBase):
    """
    Action for ending skill.
    """
    type: Literal[ActionTypes.SKILL_END] = ActionTypes.SKILL_END
    player_id: int
    charactor_id: int


class CharactorDefeatedAction(ActionBase):
    """
    Action for charactor defeated.
    """
    type: Literal[ActionTypes.CHARACTOR_DEFEATED] = \
        ActionTypes.CHARACTOR_DEFEATED
    player_id: int
    charactor_id: int


class GenerateChooseCharactorRequestAction(ActionBase):
    """
    Action for generating choose charactor action.
    """
    type: Literal[ActionTypes.GENERATE_CHOOSE_CHARACTOR] = \
        ActionTypes.GENERATE_CHOOSE_CHARACTOR
    player_id: int


Actions = (
    ActionBase | DrawCardAction | RestoreCardAction | RemoveCardAction 
    | ChooseCharactorAction | CreateDiceAction | RemoveDiceAction
    | DeclareRoundEndAction | CombatActionAction | SwitchCharactorAction
    | MakeDamageAction | ChargeAction | SkillEndAction 
    | CharactorDefeatedAction | GenerateChooseCharactorRequestAction
)
