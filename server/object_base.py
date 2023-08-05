"""
Base classes of objects in the game table. They are all subclasses of
ObjectBase. Base class of complex objects (e.g. cards and charactors) should 
be defined in their own files.
"""


from utils import BaseModel
from typing import List, Literal
from .action import (
    ActionTypes, Actions, MakeDamageAction, ChargeAction
)
from .consts import (
    ObjectType, WeaponType, ElementType, DamageType, SkillType,
    DamageSourceType,
    ELEMENT_TO_DIE_COLOR,
)
from .modifiable_values import DiceCostValue
from .struct import SkillActionArguments
from .modifiable_values import DamageValue


class ObjectBase(BaseModel):
    """
    Base class of objects in the game table. All objects in the game table 
    should inherit from this class.
    """
    type: ObjectType = ObjectType.EMPTY
    player_id: int = -1
    index: int = 0
    event_triggers: List[ActionTypes] = []


class SkillBase(ObjectBase):
    """
    Base class of skills.
    """
    name: str
    type: Literal[ObjectType.SKILL] = ObjectType.SKILL
    damage_type: DamageType
    damage: int
    cost: DiceCostValue

    def is_valid(self, hp: int, charge: int) -> bool:
        """
        Check if the skill can be used.
        """
        return True

    def get_actions(self, args: SkillActionArguments) -> List[Actions]:
        """
        The skill is triggered, and get actions of the skill.
        By default, it will generate three actions:
        1. MakeDamageAction to attack the enemy active charactor with damage
            `self.damage` and damage type `self.damage_type`.
        2. ChargeAction to charge the active charactor by 1.
        3. SkillEndAction to declare skill end, and trigger the event.
        """
        return [
            MakeDamageAction(
                player_id = args.player_id,
                target_id = 1 - args.player_id,
                damage_value_list = [
                    DamageValue(
                        target_player_id = 1 - args.player_id,
                        target_charactor_id = args.enemy_active_charactor_id,
                        damage = self.damage,
                        damage_type = self.damage_type,
                        damage_source_type = 
                        DamageSourceType.CURRENT_PLAYER_CHARACTOR,
                        charge_cost = 0,
                    )
                ],
                change_charactor = args.enemy_active_charactor_id,
            ),
            ChargeAction(
                player_id = args.player_id,
                charactor_id = args.our_active_charactor_id,
                charge = 1,
            ),
        ]


class PhysicalNormalAttackBase(SkillBase):
    """
    Base class of physical normal attacks.
    """
    skill_type: Literal[SkillType.NORMAL_ATTACK] = SkillType.NORMAL_ATTACK
    damage_type: DamageType = DamageType.PHYSICAL
    damage: int = 2

    @staticmethod
    def get_cost(element: ElementType) -> DiceCostValue:
        return DiceCostValue(
            elemental_dice_color = ELEMENT_TO_DIE_COLOR[element],
            elemental_dice_number = 1,
            any_dice_number = 2,
        )


class ElementalNormalAttackBase(SkillBase):
    """
    Base class of elemental normal attacks.
    """
    skill_type: Literal[SkillType.NORMAL_ATTACK] = SkillType.NORMAL_ATTACK
    damage_type: DamageType
    damage: int = 1

    @staticmethod
    def get_cost(element: ElementType) -> DiceCostValue:
        return DiceCostValue(
            elemental_dice_color = ELEMENT_TO_DIE_COLOR[element],
            elemental_dice_number = 1,
            any_dice_number = 2,
        )


class ElementalSkillBase(SkillBase):
    """
    Base class of elemental skills.
    """
    skill_type: Literal[SkillType.ELEMENTAL_SKILL] = SkillType.ELEMENTAL_SKILL
    damage_type: DamageType
    damage: int = 3

    @staticmethod
    def get_cost(element: ElementType) -> DiceCostValue:
        return DiceCostValue(
            elemental_dice_color = ELEMENT_TO_DIE_COLOR[element],
            elemental_dice_number = 3,
        )


class ElementalBurstBase(SkillBase):
    """
    Base class of elemental bursts.
    """
    skill_type: Literal[SkillType.ELEMENTAL_BURST] = SkillType.ELEMENTAL_BURST
    damage_type: DamageType
    charge: int

    @staticmethod
    def get_cost(element: ElementType, number: int) -> DiceCostValue:
        return DiceCostValue(
            elemental_dice_color = ELEMENT_TO_DIE_COLOR[element],
            elemental_dice_number = number,
        )

    def is_valid(self, hp: int, charge: int) -> bool:
        """
        Check if the skill can be used.
        """
        return self.charge <= charge

    def get_actions(self, args: SkillActionArguments) -> List[Actions]:
        """
        When using elemental burst, the charge of the active charactor will be
        reduced by `self.charge`.
        """
        actions = super().get_actions(args)
        for action in actions:
            if isinstance(action, ChargeAction):
                action.charge = -self.charge
        return actions


class WeaponBase(ObjectBase):
    """
    Base class of weapons.
    """
    name: str
    type: Literal[ObjectType.WEAPON] = ObjectType.WEAPON
    weapon_type: WeaponType


class ArtifactBase(ObjectBase):
    """
    Base class of artifacts.
    """
    name: str
    type: Literal[ObjectType.ARTIFACT] = ObjectType.ARTIFACT


class TalentBase(ObjectBase):
    """
    Base class of talents.
    """
    name: str
    type: Literal[ObjectType.TALENT] = ObjectType.TALENT


class StatusBase(ObjectBase):
    """
    Base class of status.
    """
    name: str
    type: Literal[ObjectType.CHARACTOR_STATUS, ObjectType.TEAM_STATUS]


class CharactorStatusBase(StatusBase):
    """
    Base class of charactor status.
    """
    type: Literal[ObjectType.CHARACTOR_STATUS] = ObjectType.CHARACTOR_STATUS


class TeamStatusBase(StatusBase):
    """
    Base class of team status.
    """
    type: Literal[ObjectType.TEAM_STATUS] = ObjectType.TEAM_STATUS
