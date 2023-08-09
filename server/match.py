import logging

import numpy as np
from typing import Literal, List, Any
from enum import Enum

from utils import BaseModel
from .deck import Deck
from .player_table import PlayerTable
from .action import (
    ActionBase, Actions,
    DrawCardAction,
    RestoreCardAction,
    RemoveCardAction,
    ChooseCharactorAction,
    CreateDiceAction,
    RemoveDiceAction,
    DeclareRoundEndAction,
    CombatActionAction,
    SwitchCharactorAction,
    MakeDamageAction,
    ChargeAction,
    SkillEndAction,
    CharactorDefeatedAction,
    GenerateChooseCharactorRequestAction,
)
from .interaction import (
    Requests, Responses, RequestActionType,
    SwitchCardRequest, SwitchCardResponse,
    ChooseCharactorRequest, ChooseCharactorResponse,
    RerollDiceRequest, RerollDiceResponse,
    SwitchCharactorRequest, SwitchCharactorResponse,
    ElementalTuningRequest, ElementalTuningResponse,
    DeclareRoundEndRequest, DeclareRoundEndResponse,
    UseSkillRequest, UseSkillResponse,
)
from .consts import (
    DieColor, ELEMENT_TO_DIE_COLOR,
    DAMAGE_TYPE_TO_ELEMENT,
    ElementalReactionType,
)
from .die import Die
from .event import (
    EventArgumentsBase,
    DrawCardEventArguments, 
    RestoreCardEventArguments, 
    RemoveCardEventArguments,
    ChooseCharactorEventArguments,
    CreateDiceEventArguments,
    RemoveDiceEventArguments,
    RoundPrepareEventArguments,
    DeclareRoundEndEventArguments,
    CombatActionEventArguments,
    SwitchCharactorEventArguments,
    ChargeEventArguments,
    SkillEndEventArguments,
    ReceiveDamageEventArguments,
    MakeDamageEventArguments,
    AfterMakeDamageEventArguments,
    CharactorDefeatedEventArguments,
)
from .object_base import ObjectBase
from .modifiable_values import (
    ModifiableValueBase,
    RerollValue, DiceCostValue,
    DamageMultiplyValue, DamageDecreaseValue,
)
from .struct import SkillActionArguments
from .elemental_reaction import (
    check_elemental_reaction,
    apply_elemental_reaction,
)
from .event_handler import SystemEventHandler


class MatchState(str, Enum):
    """
    Enum representing the state of a match.

    Attributes:
        INVALID (str): The match is invalid. Should not fall into it in common
            situations.
        ERROR (str): The match has encountered an error. Should not fall into
            it in common situations.
        WAITING (str): The match is waiting for start.
        STARTING (str): The match is starting, will generate initial objects, 
            decide who is the first player, draw initial card, etc.
        STARTING_CARD_SWITCH (str): Waiting for players to switch cards.
        STARTING_CHOOSE_CHARACTOR (str): Waiting for players to choose
            charactors.
        ROUND_START (str): A new round is starting.
        ROUND_ROLL_DICE (str): Waiting for players to re-roll dice.
        ROUND_PREPARING (str): Preparing phase starts.
        PLAYER_ACTION_START (str): Player action phase start.
        PLAYER_ACTION_REQUEST (str): Waiting for response from player.
        PLAYER_ACTION_ACT (str): After player has decided its action, the 
            action is being executed. Execution may be interrupted by requests,
            e.g. someone is knocked out, need to re-roll dice.
        ROUND_ENDING (str): Ending phase starts.
        ROUND_ENDED (str): The round has ended.
        ENDED (str): The match has ended.
    """
    INVALID = 'INVALID'
    ERROR = 'ERROR'
    WAITING = 'WAITING'

    STARTING = 'STARTING'
    STARTING_CARD_SWITCH = 'STARTING_CARD_SWITCH'
    STARTING_CHOOSE_CHARACTOR = 'STARTING_CHOOSE_CHARACTOR'

    ROUND_START = 'ROUND_START'
    ROUND_ROLL_DICE = 'ROUND_ROLL_DICE'
    ROUND_PREPARING = 'ROUND_PREPARING'

    PLAYER_ACTION_START = 'PLAYER_ACTION_START'
    PLAYER_ACTION_REQUEST = 'PLAYER_ACTION_REQUEST'
    PLAYER_ACTION_ACT = 'PLAYER_ACTION_ACT'

    ROUND_ENDING = 'ROUND_ENDING'
    ROUND_ENDED = 'ROUND_ENDED'

    ENDED = 'ENDED'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class MatchConfig(BaseModel):
    """
    """
    random_first_player: bool = True
    initial_hand_size: int = 5
    initial_card_draw: int = 2
    initial_dice_number: int = 8
    initial_dice_reroll_times: int = 1
    card_number: int = 30
    max_same_card_number: int = 2
    charactor_number: int = 3
    max_round_number: int = 15
    max_hand_size: int = 10
    max_dice_number: int = 16
    max_summon_number: int = 4
    max_support_number: int = 4

    def check_config(self) -> bool:
        """
        Check whether the config is legal.
        """
        if self.initial_hand_size > self.max_hand_size:
            logging.error('initial hand size should not be greater than '
                          'max hand size')
            return False
        if self.initial_card_draw > self.card_number:
            logging.error('initial card draw should not be greater than '
                          'card number')
            return False
        if self.initial_dice_number > self.max_dice_number:
            logging.error('initial dice number should not be greater than '
                          'max dice number')
            return False
        return True


class Match(BaseModel):
    """
    """

    name: Literal['Match'] = 'Match'

    match_config: MatchConfig = MatchConfig()

    # random state
    random_state: List[Any] = []
    _random_state: np.random.RandomState = np.random.RandomState()

    # event handlers to implement special rules. TODO add special handler
    event_handlers: List[ObjectBase] = [SystemEventHandler()]

    # match information
    round_number: int = 0
    current_player: int = -1
    player_tables: List[PlayerTable] = [PlayerTable(), PlayerTable()]
    match_state: MatchState = MatchState.WAITING
    action_queues: List[List[Actions]] = []
    requests: List[Requests] = []
    winner: int = -1

    def __init__(self, *argv, **kwargs):
        super().__init__(*argv, **kwargs)
        if self.random_state:
            random_state = self.random_state[:]
            random_state[1] = np.array(random_state[1], dtype = 'uint32')
            self._random_state.set_state(random_state)  # type: ignore

    def set_deck(self, decks: List[Deck]):
        """
        Set the deck of the match.
        """
        if self.match_state != MatchState.WAITING:
            logging.error('Match is not in waiting state.')
            return
        assert len(decks) == len(self.player_tables)
        for player_table, deck in zip(self.player_tables, decks):
            player_table.player_deck_information = deck

    def _save_random_state(self):
        """
        Save the random state.
        """
        self.random_state = list(self._random_state.get_state(
            legacy = True))  # type: ignore
        self.random_state[1] = self.random_state[1].tolist()

    def _random(self):
        """
        Return a random number ranges 0-1 based on random_state, and save new
        random state.
        """
        ret = self._random_state.random()
        self._save_random_state()
        return ret

    def _random_shuffle(self, array: List):
        """
        Shuffle the array based on random_state.
        """
        self._random_state.shuffle(array)
        self._save_random_state()

    def _set_match_state(self, new_state: MatchState):
        logging.info(f'Match state change from {self.match_state} to '
                     f'{new_state}.')
        self.match_state = new_state

    def start(self) -> bool:
        """
        Start a new match. MatchState should be WAITING. Check the config and
        start until reaching STARTING_CARD_SWITCH, then wait for responses 
        from player to switch cards.
        """
        if self.match_state != MatchState.WAITING:
            # TODO: support re-start
            # logging.error('Match is not waiting for start. If it is running '
            #               'or ended, please call stop first.')
            logging.error('Match is not waiting for start. If it is running '
                          'or ended, please re-generate a new match.')
            return False

        # make valid check
        if not self.match_config.check_config():
            logging.error('Match config is not valid.')
            self._set_match_state(MatchState.ERROR)
            return False
        if len(self.player_tables) != 2:
            logging.error('Only support 2 players now.')
            self._set_match_state(MatchState.ERROR)
            return False
        for pnum, player_table in enumerate(self.player_tables):
            is_legal = player_table.player_deck_information.check_legal(
                card_number = self.match_config.card_number,
                max_same_card_number = self.match_config.max_same_card_number,
                charactor_number = self.match_config.charactor_number
            )
            if not is_legal:
                logging.error(f'Player {pnum} deck is not legal.')
                self._set_match_state(MatchState.ERROR)
                return False

        self._set_match_state(MatchState.STARTING)

        # choose first player
        if self.match_config.random_first_player:
            self.current_player = int(self._random() > 0.5)
        else:
            self.current_player = 0
        logging.info(f'Player {self.current_player} is the first player')

        # copy and randomize based on deck
        for pnum, player_table in enumerate(self.player_tables):
            # copy charactors
            for charactor in player_table.player_deck_information.charactors:
                charactor_copy = charactor.copy()
                charactor_copy.player_id = pnum
                player_table.charactors.append(charactor_copy)
            # copy cards
            for card in player_table.player_deck_information.cards:
                card_copy = card.copy()
                card_copy.player_id = pnum
                player_table.table_deck.append(card_copy)
            self._random_shuffle(player_table.table_deck)
            # add draw initial cards action
            event_args = self._act(DrawCardAction(
                player_id = pnum, 
                number = self.match_config.initial_hand_size
            ))
            triggered_actions = self._trigger_events(event_args)
            if triggered_actions:
                logging.error('Initial draw card should not trigger actions.')
                self._set_match_state(MatchState.ERROR)
                return False
        return True

    def step(self, run_continuously: bool = True) -> bool:
        """
        Simulate one step of the match, or run continuously until a response
        is needed from agents.

        Args: 
            run_continuously (bool): If True, run continuously until a 
                response is needed from agents. Otherwise, simulate one step
                and return. Default: True.

        Returns:
            bool: True if success, False if error occurs.
        """
        while True:
            # check if game reaches end condition
            if self.is_game_end():
                self._set_match_state(MatchState.ENDED)
                return True
            # check if it need response
            elif len(self.requests) != 0:
                logging.info('There are still requests not responded.')
                return False
            # check if action is needed
            elif len(self.action_queues) != 0:
                self._next_action()
            # all response and action are cleared, start state transition
            elif self.match_state == MatchState.STARTING:
                self._set_match_state(MatchState.STARTING_CARD_SWITCH)
                self._request_switch_card()
            elif self.match_state == MatchState.STARTING_CARD_SWITCH:
                self._set_match_state(MatchState.STARTING_CHOOSE_CHARACTOR)
                for player_id in range(len(self.player_tables)):
                    self._request_choose_charactor(player_id)
            elif self.match_state == MatchState.STARTING_CHOOSE_CHARACTOR:
                self._set_match_state(MatchState.ROUND_START)
                self._round_start()
            elif self.match_state == MatchState.ROUND_ROLL_DICE:
                self._set_match_state(MatchState.ROUND_PREPARING)
                self._round_prepare()
            elif self.match_state == MatchState.ROUND_PREPARING:
                self._set_match_state(MatchState.PLAYER_ACTION_START)
                self._player_action_start()
            elif self.match_state == MatchState.PLAYER_ACTION_START:
                self._set_match_state(MatchState.PLAYER_ACTION_REQUEST)
                self._player_action_request()
            elif self.match_state == MatchState.PLAYER_ACTION_REQUEST:
                # request responded and all action clear
                self._player_action_end()
            elif self.match_state == MatchState.ROUND_ENDING:
                self._set_match_state(MatchState.ROUND_ENDED)
                self._round_ending()
            elif self.match_state == MatchState.ROUND_ENDED:
                self._set_match_state(MatchState.ROUND_START)
                self._round_start()
            elif self.match_state == MatchState.ENDED:
                logging.warning('Match has ended.')
                return True
            else:
                raise NotImplementedError(
                    f'Match state {self.match_state} not implemented.')
            if len(self.requests) or not run_continuously:
                if len(self.requests):
                    logging.info(
                        f'{len(self.requests)} requests generated, '
                        f'{", ".join([req.name for req in self.requests])}'
                    )
                return True

    def check_request_exist(self, request: Requests) -> bool:
        """
        Check if the request is valid.
        """
        for req in self.requests:
            if req == request:
                return True
        return False

    def respond(self, response: Responses) -> bool:
        """
        Deal with the response. After start, the match will simulate 
        until it needs response from player, and `self.requests` will have
        requests for all players. A player should choose all requests
        related to him and respond one of them. Different requests will use
        different respond function to deal with, and remove requests that do
        not need to respond or have responded. If all requests have been
        removed, call `self.step()` manually to continue simulation. 

        Returns:
            bool: True if success, False if error occurs.
        """
        logging.info(f'Response received: {response}')
        if len(self.requests) == 0:
            logging.error('Match is not waiting for response.')
            return False
        # check if the response is valid
        if not response.is_valid:
            logging.error('Response is not valid.')
            return False
        # check if the request exist
        if not self.check_request_exist(response.request):
            logging.error('Request does not exist.')
            return False
        # call different respond functions based on the type of response
        if isinstance(response, SwitchCharactorResponse):
            self._respond_switch_charactor(response)
        elif isinstance(response, ElementalTuningResponse):
            self._respond_elemental_tuning(response)
        elif isinstance(response, DeclareRoundEndResponse):
            self._respond_declare_round_end(response)
        elif isinstance(response, UseSkillResponse):
            self._respond_use_skill(response)
        # elif isinstance(response, UseCardResponse):
        #     self._respond_use_card(response)
        elif isinstance(response, SwitchCardResponse):
            self._respond_switch_card(response)
        elif isinstance(response, ChooseCharactorResponse):
            self._respond_choose_charactor(response)
        elif isinstance(response, RerollDiceResponse):
            self._respond_reroll_dice(response)
        else:
            logging.error(f'Response type {type(response)} not recognized.')
            return False
        return True

    def is_game_end(self) -> bool:
        """
        Check if the game reaches end condition. If game is ended, it will
        set `self.winner` to the winner of the game.

        Returns:
            bool: True if game reaches end condition, False otherwise.
        """
        # all charactors are defeated
        # TODO: for monsters, need different conditions
        for pnum, table in enumerate(self.player_tables):
            for charactor in table.charactors:
                if charactor.is_alive:
                    break
            else:
                assert len(self.player_tables) == 2
                self.winner = 1 - pnum
                return True
        return False

    def _next_action(self):
        """
        Do one action in `self._action_queue`. It will pick the first action in
        the last action queue, do it, and trigger events. if events have
        triggered new actions, they will be added as a new action queue.
        """
        # pop empty action queue
        while len(self.action_queues):
            if len(self.action_queues[-1]) == 0:
                self.action_queues.pop()
            else:
                break
        # if no action queue remain, return
        if len(self.action_queues) == 0:
            return
        activated_action = self.action_queues[-1].pop(0)
        logging.info(f'Action activated: {activated_action}')
        event_args = self._act(activated_action)
        triggered_actions = self._trigger_events(event_args)
        if triggered_actions:
            self.action_queues.append(triggered_actions)

    def _round_start(self):
        """
        Start a round. Will clear existing dice, generate new random dice
        and asking players to reroll dice.

        # TODO: implement locking dice colors like Jade Chamber.
        # TODO: send round start event.
        """
        self.round_number += 1
        for table in self.player_tables:
            table.has_round_ended = False
        for pnum, player_table in enumerate(self.player_tables):
            player_table.dice.clear()
        # generate new dice
        event_args: List[EventArgumentsBase] = []
        for pnum, player_table in enumerate(self.player_tables):
            one_event_args = self._act(CreateDiceAction(
                player_id = pnum,
                number = self.match_config.initial_dice_number,
                random = True
            ))
            event_args += one_event_args
        triggered_actions = self._trigger_events(event_args)
        if len(triggered_actions) != 0:
            logging.error('Create dice should not trigger actions.')
            self._set_match_state(MatchState.ERROR)
            return False
        # collect actions triggered by round start
        # reroll dice chance. reroll times can be modified by objects.
        for pnum, player_table in enumerate(self.player_tables):
            reroll_times = self.match_config.initial_dice_reroll_times
            reroll_value = RerollValue(
                value = reroll_times,
                player_id = pnum,
            )
            self._modify_value(reroll_value, mode = 'real')
            self._request_reroll_dice(pnum, reroll_value.value)
        self._set_match_state(MatchState.ROUND_ROLL_DICE)

    def _round_prepare(self):
        """
        Activate round_prepare event, and add to actions.
        """
        event_arg = RoundPrepareEventArguments(
            player_go_first = self.current_player,
            round = self.round_number,
            dice_colors = [
                [dice.color for dice in table.dice]
                for table in self.player_tables
            ],
        )
        actions = self._trigger_event(event_arg)
        logging.info(f'In round prepare, {len(actions)} actions triggered.')
        self.action_queues.append(actions)

    def _player_action_start(self):
        """
        Start a player's action phase. Will generate action phase start event.  
        TODO generate event
        """
        not_all_declare_end = False
        for table in self.player_tables:
            if not table.has_round_ended:
                not_all_declare_end = True
                break
        if not not_all_declare_end:
            # all declare ended, go to round ending
            self._set_match_state(MatchState.ROUND_ENDING)
            return

    def _player_action_request(self):
        """
        Will generate requests of available actions
        of the player. There will be the following actions:
        1. Use Skill: Pay the relevant cost and use your active character's 
            Skill(s).
        2. Switch Characters: Pay 1 Elemental Die of your choice to switch your 
            active character.
        3. Play Card: Pay the relevant cost and play card(s) from your Hand.
        4. Elemental Tuning: Discard a card from your Hand and change the 
            Elemental Type of 1 of your Elemental Die which Elemental Type
            does not match your active character's Elemental Type, and also
            not Omni.
        5. Declare Round End: End your actions for this Round. The first player 
            to declare the end of their Round will go first during the next 
            Round.
        """
        self._request_switch_charactor(self.current_player)
        self._request_elemental_tuning(self.current_player)
        self._request_declare_round_end(self.current_player)
        self._request_use_skill(self.current_player)
        self._request_use_card(self.current_player)

    def _player_action_end(self):
        """
        End a player's action phase. Will check status and go to proper state.
        """
        all_declare_end = True
        for table in self.player_tables:
            if not table.has_round_ended:
                all_declare_end = False
                break
        if all_declare_end:
            # all declare ended, go to round ending
            self._set_match_state(MatchState.ROUND_ENDING)
        else:
            # not all declare ended, go to next action
            self._set_match_state(MatchState.PLAYER_ACTION_START)

    def _round_ending(self):
        """
        End a round. Will send round end event, collect actions.
        """

    def get_object_lists(self) -> List[ObjectBase]:
        """
        Get all objects in the match by `self.table.get_object_lists`. 
        The order of objects should follow the game rule. The rules are:
        1. objects of `self.current_player` goes first
        2. objects belongs to charactor goes first
            2.1. active charactor first, otherwise the default order.
            2.2. for one charactor, order is weapon, artifact, talent, status.
            2.3. for status, order is their index in status list, i.e. 
                generated time.
        3. for other objects, order is: summon, support, hand, dice, deck.
            3.1. all other objects in same region are sorted by their index in
                the list.
        4. system event handler
        """
        return (
            self.player_tables[self.current_player].get_object_lists()
            + self.player_tables[1 - self.current_player].get_object_lists()
            + self.event_handlers
        )

    def _trigger_event(self, event_arg: EventArgumentsBase,
                       ) -> List[Actions]:
        """
        Trigger event. It will return a list of actions that will be triggered
        by the event. The actions will be sorted by the sort rule.
        """
        ret: List[Actions] = []
        object_list = self.get_object_lists()
        for obj in object_list:
            name = obj.__class__.__name__
            # TODO with pydantic, cannot overload function on None
            if hasattr(obj, 'name'):
                name = obj.name  # type: ignore
            handler_name = f'event_handler_{event_arg.type}'
            func = getattr(obj, handler_name, None)
            if func is not None:
                logging.info(f'Trigger event {event_arg.type} for {name}.')
                actions = func(event_arg)
                ret += actions
        return ret

    def _trigger_events(self, event_args: List[EventArgumentsBase],
                        ) -> List[Actions]:
        """
        Trigger events. It will return a list of actions that will be triggered
        by the events. The order of actions is the same as the order of events.
        For one event, the actions will be sorted by the sort rule.
        """
        ret: List[Actions] = []
        for event_arg in event_args:
            ret.extend(self._trigger_event(event_arg))
        return ret

    def _modify_value(self, value: ModifiableValueBase, 
                      mode: Literal['test', 'real'],
                      ) -> None:
        """
        Modify values. It will modify the value argument in-place.
        Args:
            value (ModifiableValues): The value to be modified. It contains 
                value itself and all necessary information to modify the value.
            sort_rule (ObjectSortRule): The sort rule used to sort objects.
            mode (Literal['test', 'real']): If 'test', objects will only modify
                the value but not updating inner state, which is used to 
                calculate costs used in requests. If 'real', it will modify 
                the value and update inner state, which means the request
                related to the value is executed.
        """
        object_list = self.get_object_lists()
        for obj in object_list:
            name = obj.__class__.__name__
            if hasattr(obj, 'name'):
                name = obj.name  # type: ignore
            logging.debug(f'Modify value {value.type} for {name}.')
            ...

    """
    Request functions. To generate specific requests.
    """

    def _request_switch_card(self):
        """
        Generate switch card requests.
        """
        for pnum, player_table in enumerate(self.player_tables):
            self.requests.append(SwitchCardRequest(
                player_id = pnum,
                card_names = [card.name for card in player_table.hands]
            ))

    def _request_choose_charactor(self, player_id: int):
        """
        Generate switch card requests.
        """
        table = self.player_tables[player_id]
        available: List[int] = []
        for cnum, charactor in enumerate(table.charactors):
            if charactor.is_alive:
                available.append(cnum)
        self.requests.append(ChooseCharactorRequest(
            player_id = player_id,
            available_charactor_ids = available
        ))

    def _request_reroll_dice(self, player_id: int, reroll_number: int):
        player_table = self.player_tables[player_id]
        self.requests.append(RerollDiceRequest(
            player_id = player_id,
            colors = [dice.color for dice in player_table.dice],
            reroll_times = reroll_number
        ))

    def _request_switch_charactor(self, player_id: int):
        """
        Generate switch charactor requests.
        TODO: With Leave It to Me, it can be a quick action.
        """
        table = self.player_tables[player_id]
        dice_cost = DiceCostValue(same_dice_number = 1)
        self._modify_value(dice_cost, mode = 'test')
        if not dice_cost.is_valid(
            dice_colors = [die.color for die in table.dice],
            strict = False,
        ):
            return
        candidate_charactor_ids = [
            x for x in range(len(table.charactors))
            if x != table.active_charactor_id 
            and table.charactors[x].is_alive
        ]
        if len(candidate_charactor_ids):
            self.requests.append(SwitchCharactorRequest(
                player_id = player_id,
                type = RequestActionType.COMBAT,  # TODO currently only combat
                active_charactor_id = table.active_charactor_id,
                candidate_charactor_ids = candidate_charactor_ids,
                dice_colors = [die.color for die in table.dice],
                cost = dice_cost,
            ))

    def _request_elemental_tuning(self, player_id: int):
        table = self.player_tables[player_id]
        target_color = ELEMENT_TO_DIE_COLOR[
            table.charactors[table.active_charactor_id].element
        ]
        available_dice_colors = [
            dice.color for dice in table.dice
            if dice.color != target_color and dice.color != DieColor.OMNI
        ]
        available_card_ids = list(range(len(table.hands)))
        if len(available_dice_colors) and len(available_card_ids):
            self.requests.append(ElementalTuningRequest(
                player_id = player_id,
                dice_colors = available_dice_colors,
                card_ids = available_card_ids
            ))

    def _request_declare_round_end(self, player_id: int):
        self.requests.append(DeclareRoundEndRequest(
            player_id = player_id
        ))

    def _request_use_skill(self, player_id: int):
        table = self.player_tables[player_id]
        front_charactor = table.charactors[table.active_charactor_id]
        for sid, skill in enumerate(front_charactor.skills):
            if skill.is_valid(front_charactor.hp, front_charactor.charge):
                cost = skill.cost.copy()
                self._modify_value(cost, mode = 'test')
                dice_colors = [die.color for die in table.dice]
                if cost.is_valid(dice_colors = dice_colors, strict = False):
                    self.requests.append(UseSkillRequest(
                        player_id = player_id,
                        # TODO currently only combat
                        type = RequestActionType.COMBAT,
                        charactor_id = table.active_charactor_id,
                        skill_id = sid,
                        dice_colors = dice_colors,
                        cost = cost
                    ))
                else:
                    ...

    def _request_use_card(self, player_id: int):
        """
        table = self.player_tables[player_id]
        available_card_ids = list(range(len(table.hands)))
        if len(available_card_ids):
            self.requests.append(UseCardRequest(
                player_id = player_id,
                card_ids = available_card_ids
            ))
        """
        ...

    """
    Response functions. To deal with specific responses.
    """

    def _respond_switch_card(self, response: SwitchCardResponse):
        # restore cards
        card_names = response.card_names
        card_name_dict = {}
        for card_name in card_names:
            if card_name not in card_name_dict:
                card_name_dict[card_name] = 0
            card_name_dict[card_name] += 1
        card_hand_ids = []
        card_hand_names = [x.name for x in self.player_tables[
            response.player_id].hands]
        for card_name, count in card_name_dict.items():
            start_idx = -1
            for _ in range(count):
                next_idx = card_hand_names.index(card_name, start_idx + 1)
                card_hand_ids.append(next_idx)
                start_idx = next_idx
        event_args: List[EventArgumentsBase] = []
        event_args += self._act(RestoreCardAction(
            player_id = response.player_id,
            card_ids = card_hand_ids
        ))
        event_args += self._act(
            DrawCardAction(
                player_id = response.player_id,
                number = len(response.card_ids)
            )
        )
        triggered_actions = self._trigger_events(event_args)
        if triggered_actions:
            logging.error('Initial switch card should not trigger '
                          'actions.')
            self._set_match_state(MatchState.ERROR)
            return
        # remove related requests
        self.requests = [
            req for req in self.requests
            if req.player_id != response.player_id
        ]

    def _respond_choose_charactor(self, response: ChooseCharactorResponse):
        event_args = self._act(
            ChooseCharactorAction.from_response(response)
        )
        triggered_actions = self._trigger_events(event_args)
        if len(triggered_actions) > 0:
            if len(self.action_queues) != 0:
                # already has actions in queue, append new actions
                # TODO extend or stack?
                self.action_queues[0].extend(triggered_actions)
            else:
                # no actions in queue, append new actions
                self.action_queues.append(triggered_actions)
        # remove related requests
        self.requests = [
            req for req in self.requests
            if req.player_id != response.player_id
        ]

    def _respond_reroll_dice(self, response: RerollDiceResponse):
        """
        Deal with reroll dice response. If there are still reroll times left,
        keep request and only substrat reroll times. If there are no reroll
        times left, remove request.
        """
        event_args = self._action_remove_dice(RemoveDiceAction.from_response(
            response
        ))
        triggered_actions: List[ActionBase] = []
        for event_arg in event_args:
            actions = self._trigger_event(event_arg)
            triggered_actions.extend(actions)
        if len(triggered_actions) > 0:
            logging.error('Removing dice in Reroll Dice should not trigger '
                          'actions.')
            self._set_match_state(MatchState.ERROR)
            return
        event_args = self._action_create_dice(CreateDiceAction(
            player_id = response.player_id,
            number = len(response.reroll_dice_ids),
            random = True,
        ))
        for event_arg in event_args:
            actions = self._trigger_event(event_arg)
            triggered_actions.extend(actions)
        if len(triggered_actions) > 0:
            if len(self.action_queues) != 0:
                # already has actions in queue, append new actions
                # TODO extend or stack?
                self.action_queues[0].extend(triggered_actions)
            else:
                # no actions in queue, append new actions
                self.action_queues.append(triggered_actions)
        # modify request
        for num, req in enumerate(self.requests):
            if isinstance(req, RerollDiceRequest):
                if req.player_id == response.player_id:
                    if req.reroll_times > 1:
                        req.reroll_times -= 1
                    else:
                        self.requests.pop(num)
                    break

    def _respond_switch_charactor(self, response: SwitchCharactorResponse):
        """
        Deal with switch charactor response. If it is combat action, add
        combat action to action queue. Remove related requests.
        """
        actions: List[ActionBase] = []
        cost_ids = response.cost_ids
        if len(cost_ids):
            actions.append(RemoveDiceAction(
                player_id = response.player_id,
                dice_ids = cost_ids,
            ))
        self._modify_value(
            value = response.request.cost.original_value,
            mode = 'real'
        )  # TODO: should use original value. need test.
        actions.append(SwitchCharactorAction.from_response(response))
        if response.request.type == RequestActionType.COMBAT:
            actions.append(CombatActionAction(
                player_id = response.player_id,
            ))
        self.action_queues.append(actions)
        self.requests = [x for x in self.requests
                         if x.player_id != response.player_id]

    def _respond_elemental_tuning(self, response: ElementalTuningResponse):
        """
        Deal with elemental tuning response. It is splitted into 3 actions,
        remove one hand card, remove one die, and add one die.
        """
        die_id = response.cost_id
        table = self.player_tables[response.player_id]
        actions: List[ActionBase] = []
        actions.append(RemoveCardAction(
            player_id = response.player_id,
            card_id = response.card_id,
            card_position = 'HAND',
            remove_type = 'BURNED'
        ))
        actions.append(RemoveDiceAction(
            player_id = response.player_id,
            dice_ids = [die_id]
        ))
        actions.append(CreateDiceAction(
            player_id = response.player_id,
            number = 1,
            color = ELEMENT_TO_DIE_COLOR[
                table.charactors[table.active_charactor_id].element]
        ))
        self.action_queues.append(actions)
        self.requests = [x for x in self.requests
                         if x.player_id != response.player_id]

    def _respond_declare_round_end(self, response: DeclareRoundEndResponse):
        """
        Deal with declare round end response. It is splitted into 2 actions,
        declare round end and combat action.
        """
        actions: List[ActionBase] = []
        actions.append(DeclareRoundEndAction.from_response(response))
        actions.append(CombatActionAction(
            player_id = response.player_id,
        ))
        self.action_queues.append(actions)
        self.requests = [x for x in self.requests
                         if x.player_id != response.player_id]

    def _respond_use_skill(self, response: UseSkillResponse):
        request = response.request
        self._modify_value(
            value = request.cost.original_value,
            mode = 'real'
        )  # TODO: should use original value. need test.
        skill = self.player_tables[response.player_id].charactors[
            request.charactor_id].skills[request.skill_id]
        skill_action_args = SkillActionArguments(
            player_id = response.player_id,
            our_active_charactor_id = self.player_tables[
                response.player_id].active_charactor_id,
            enemy_active_charactor_id = self.player_tables[
                1 - response.player_id].active_charactor_id,
            our_charactors = [
                i for i, c in enumerate(self.player_tables[
                    response.player_id].charactors)
                if c.is_alive
            ],
            enemy_charactors = [
                i for i, c in enumerate(self.player_tables[
                    1 - response.player_id].charactors)
                if c.is_alive
            ],
        )
        actions = skill.get_actions(skill_action_args)  # TODO: add information
        actions.append(SkillEndAction(
            player_id = response.player_id,
            charactor_id = request.charactor_id,
        ))
        if request.type == RequestActionType.COMBAT:
            actions.append(CombatActionAction(
                player_id = response.player_id,
            ))
        self.action_queues.append(actions)
        self.requests = [x for x in self.requests
                         if x.player_id != response.player_id]

    def _respond_use_card(self, response: Responses):
        ...

    """
    Action Functions
    """

    def _act(self, action: ActionBase) -> List[EventArgumentsBase]:
        """
        Act an action. It will call corresponding action function based on
        the type of the action.

        Action functions take Action as input, do 
        changes of the game table, and return a list of triggered events.
        In most case, the list should contain exactly one event argument,
        however we use list to make it compatible with future changes.

        Returns:
            A list of triggered event arguments. We wrap the returned event 
            arguments of action functions in a list to avoid error from linter.
        """
        if isinstance(action, ChooseCharactorAction):
            return list(self._action_choose_charactor(action))
        elif isinstance(action, CreateDiceAction):
            return list(self._action_create_dice(action))
        elif isinstance(action, RemoveDiceAction):
            return list(self._action_remove_dice(action))
        elif isinstance(action, RestoreCardAction):
            return list(self._action_restore_card(action))
        elif isinstance(action, DrawCardAction):
            return list(self._action_draw_card(action))
        elif isinstance(action, RemoveCardAction):
            return list(self._action_remove_card(action))
        elif isinstance(action, SwitchCharactorAction):
            return list(self._action_switch_charactor(action))
        elif isinstance(action, DeclareRoundEndAction):
            return list(self._action_declare_round_end(action))
        elif isinstance(action, CombatActionAction):
            return list(self._action_combat_action(action))
        elif isinstance(action, MakeDamageAction):
            return list(self._action_make_damage(action))
        elif isinstance(action, ChargeAction):
            return list(self._action_charge(action))
        elif isinstance(action, SkillEndAction):
            return list(self._action_skill_end(action))
        elif isinstance(action, CharactorDefeatedAction):
            return list(self._action_charactor_defeated(action))
        elif isinstance(action, GenerateChooseCharactorRequestAction):
            return list(self._action_generate_choose_charactor_request(action))
        else:
            logging.error(f'Unknown action {action}.')
            self._set_match_state(MatchState.ERROR)
            return []

    def _action_draw_card(
            self, 
            action: DrawCardAction) -> List[DrawCardEventArguments]:
        """
        Draw cards from the deck, and return the argument of triggered events.
        TODO: Input have draw rule, e.g. NRE.
        TODO: maintain card type from DECK_CARD to HAND_CARD
        TODO: destroy card if maximum hand size is reached
        """
        player_id = action.player_id
        number = action.number
        table = self.player_tables[player_id]
        if len(table.table_deck) < number:
            number = len(table.table_deck)
        names = [x.name for x in table.table_deck[:number]]
        table.hands.extend(table.table_deck[:number])
        table.table_deck = table.table_deck[number:]
        logging.info(
            f'Draw card action, player {player_id}, number {number}, '
            f'cards {names}, '
            f'deck size {len(table.table_deck)}, hand size {len(table.hands)}'
        )
        event_arg = DrawCardEventArguments(
            action = action,
        )
        return [event_arg]

    def _action_restore_card(
            self, 
            action: RestoreCardAction) -> List[RestoreCardEventArguments]:
        """
        Restore cards to the deck.
        """
        player_id = action.player_id
        table = self.player_tables[player_id]
        card_ids = action.card_ids[:]
        card_ids.sort(reverse = True)  # reverse order to avoid index error
        card_names = [table.hands[cid].name for cid in card_ids]
        for cid in card_ids:
            table.table_deck.append(table.hands[cid])
            table.hands = table.hands[:cid] + table.hands[cid + 1:]
        logging.info(
            f'Restore card action, player {player_id}, number {len(card_ids)},'
            f' cards: {card_names}, '
            f'deck size {len(table.table_deck)}, hand size {len(table.hands)}'
        )
        event_arg = RestoreCardEventArguments(
            action = action,
            card_names = card_names
        )
        return [event_arg]

    def _action_remove_card(self, action: RemoveCardAction) \
            -> List[RemoveCardEventArguments]:
        player_id = action.player_id
        card_position = action.card_position
        remove_type = action.remove_type  # used or burned (Keqing, EleTuning)
        table = self.player_tables[player_id]
        if card_position == 'HAND':
            card = table.hands.pop(action.card_id)
        elif card_position == 'DECK':
            card = table.table_deck.pop(action.card_id)
        else:
            logging.error(f'Unknown card position {card_position}.')
            self._set_match_state(MatchState.ERROR)
            return []
        logging.info(
            f'Remove hand card action, player {player_id}, '
            f'card position {card_position}, '
            f'card name {card.name}, '
            f'remove type {remove_type}.'
        )
        event_arg = RemoveCardEventArguments(
            action = action,
            card_name = card.name
        )
        return [event_arg]

    def _action_choose_charactor(self, action: ChooseCharactorAction) \
            -> List[ChooseCharactorEventArguments]:
        """
        This action triggers by game start and by active charactor is defeated.
        Be care of differences between choose_charactor when implementing 
        event triggers.
        """
        player_id = action.player_id
        charactor_id = action.charactor_id
        table = self.player_tables[player_id]
        logging.info(
            f'Choose charactor action, player {player_id}, '
            f'charactor id {charactor_id}, '
            f'name {table.charactors[charactor_id].name}'
        )
        original_charactor_id = table.active_charactor_id
        table.active_charactor_id = charactor_id
        event_arg = ChooseCharactorEventArguments(
            action = action,
            original_charactor_id = original_charactor_id
        )
        return [event_arg]

    def _action_create_dice(self, action: CreateDiceAction) \
            -> List[CreateDiceEventArguments]:
        """
        Create dice.
        """
        dice: List[Die] = []
        player_id = action.player_id
        table = self.player_tables[player_id]
        number = action.number
        color = action.color
        is_random = action.random
        is_different = action.different
        if is_random and is_different:
            logging.error('Dice cannot be both random and different.')
            self._set_match_state(MatchState.ERROR)
            return []
        candidates: List[DieColor] = [
            DieColor.CRYO, DieColor.PYRO, DieColor.HYDRO, DieColor.ELECTRO,
            DieColor.GEO, DieColor.DENDRO, DieColor.ANEMO
        ]
        # generate dice based on color
        if is_random:
            candidates.append(DieColor.OMNI)  # random, can be omni
            for _ in range(number):
                selected_color = candidates[int(self._random() 
                                                * len(candidates))]
                dice.append(Die(color = selected_color))
        elif is_different:
            if number > len(candidates):
                logging.error('Not enough dice colors.')
                self._set_match_state(MatchState.ERROR)
                return []
            self._random_shuffle(candidates)
            candidates = candidates[:number]
            for selected_color in candidates:
                dice.append(Die(color = selected_color))
        else:
            if color is None:
                logging.error('Dice color should be specified.')
                self._set_match_state(MatchState.ERROR)
                return []
            for _ in range(number):
                dice.append(Die(color = color))
        # if there are more dice than the maximum, discard the rest
        max_obtainable_dice = (self.match_config.max_dice_number 
                               - len(table.dice))
        for die in dice[:max_obtainable_dice]:
            table.dice.append(die)
        # sort dice by color
        table.sort_dice()
        logging.info(
            f'Create dice action, player {player_id}, '
            f'number {len(dice)}, '
            f'dice colors {[die.color for die in dice]}, '
            f'obtain {len(dice[:max_obtainable_dice])}, '
            f'over maximum {len(dice[max_obtainable_dice:])}, '
            f'current dice on table {table.dice}'
        )
        return [CreateDiceEventArguments(
            action = action,
            colors_generated = [die.color for die 
                                in dice[:max_obtainable_dice]],
            colors_over_maximum = [die.color for die 
                                   in dice[max_obtainable_dice:]]
        )]

    def _action_remove_dice(self, action: RemoveDiceAction) \
            -> List[RemoveDiceEventArguments]:
        player_id = action.player_id
        dice_ids = action.dice_ids
        table = self.player_tables[player_id]
        removed_dice: List[Die] = []
        dice_ids.sort(reverse = True)  # reverse order to avoid index error
        for idx in dice_ids:
            removed_dice.append(table.dice.pop(idx))
        # sort dice by color
        table.sort_dice()
        logging.info(
            f'Remove dice action, player {player_id}, '
            f'number {len(dice_ids)}, '
            f'dice colors {[die.color for die in removed_dice]}, '
            f'current dice on table {table.dice}'
        )
        return [RemoveDiceEventArguments(
            action = action,
            colors_removed = [die.color for die in removed_dice]
        )]

    def _action_declare_round_end(self, action: DeclareRoundEndAction) \
            -> List[DeclareRoundEndEventArguments]:
        player_id = action.player_id
        table = self.player_tables[player_id]
        logging.info(
            f'Declare round end action, player {player_id}.'
        )
        table.has_round_ended = True
        return [DeclareRoundEndEventArguments(
            action = action
        )]

    def _action_combat_action(self, action: CombatActionAction) \
            -> List[CombatActionEventArguments]:
        player_id = action.player_id
        if self.player_tables[1 - player_id].has_round_ended and \
                not self.player_tables[player_id].has_round_ended:
            # the other player has declared round end and current player not, 
            # do not change current player.
            pass
        else:
            # change current player. If no player has declared round end,
            # the current player will be changed to the other player.
            # Otherwise, two players all declared round end, the other player
            # goes first in the next round.
            self.current_player = 1 - player_id
        logging.info(
            f'player {player_id} did a combat action, current player '
            f'is {self.current_player}.'
        )
        return [CombatActionEventArguments(
            action = action
        )]

    def _action_switch_charactor(self, action: SwitchCharactorAction) \
            -> List[SwitchCharactorEventArguments]:
        """
        This action triggers by player manually declare charactor switch
        or by using skills or by overloaded. Be care of differences between
        choose_charactor when implementing event triggers.
        """
        player_id = action.player_id
        table = self.player_tables[player_id]
        current_active_id = table.active_charactor_id
        current_active_name = table.charactors[current_active_id].name
        charactor_id = action.charactor_id
        charactor_name = table.charactors[charactor_id].name
        logging.info(
            f'player {player_id} '
            f'from charactor {current_active_name}:{current_active_id} '
            f'switched to charactor {charactor_name}:{charactor_id}.'
        )
        table.active_charactor_id = charactor_id
        return [SwitchCharactorEventArguments(
            action = action,
            last_active_charactor_id = current_active_id,
        )]

    def _action_make_damage(self, action: MakeDamageAction) \
            -> List[ReceiveDamageEventArguments | MakeDamageEventArguments 
                    | AfterMakeDamageEventArguments 
                    | SwitchCharactorEventArguments]:
        """
        Make damage action. It will return two types of events:
        1. MakeDamageEventArguments: All damage information dealt by this 
            action.
        2. SwitchCharactorEventArguments: If this damage action contains
            charactor change, i.e. overloaded, Skills of Anemo charactors, etc.
            A SwitchCharactorEventArguments will be generated.
            NOTE: only charactor switch of charactor received this damage will
            trigger this event, charactor switch of attacker (Kazuha, Kenki, 
            When the Crane Returned) should be another SwtichCharactorAction.
        """
        damage_lists = action.damage_value_list
        target_id = action.target_id
        next_charactor: int = action.change_charactor
        events: List[ReceiveDamageEventArguments | MakeDamageEventArguments 
                     | AfterMakeDamageEventArguments
                     | SwitchCharactorEventArguments] = []
        infos: List[ReceiveDamageEventArguments] = []
        while len(damage_lists) > 0:
            damage = damage_lists.pop(0)
            damage_original = damage.copy()
            table = self.player_tables[damage.target_player_id]
            charactor = table.charactors[damage.target_charactor_id]
            damage_element_type = DAMAGE_TYPE_TO_ELEMENT[damage.damage_type]
            target_element_application = charactor.element_application
            [elemental_reaction, reacted_elements, applied_elements] = \
                check_elemental_reaction(
                    damage_element_type, 
                    target_element_application
            )
            if (elemental_reaction is ElementalReactionType.OVERLOADED
                    and damage.target_charactor_id 
                    == table.active_charactor_id):
                # overloaded to next charactor
                if damage.target_player_id != target_id:
                    self._set_match_state(MatchState.ERROR)
                    raise ValueError(
                        'Overloaded damage target player '
                        f'{damage.target_player_id} '
                        f'does not match action target player {target_id}.'
                    )
                nci = table.next_charactor_id()
                if nci is not None:
                    next_charactor = nci
            # apply elemental reaction, update damage and append new damages
            damages_after_elemental_reaction = \
                apply_elemental_reaction(
                    table.charactors,
                    damage, 
                    elemental_reaction, 
                    reacted_elements,
                )
            damage = damages_after_elemental_reaction.pop(0)
            damage_lists += damages_after_elemental_reaction
            # apply 3-step damage modification
            self._modify_value(damage, 'real')
            damage = DamageMultiplyValue.from_increase_value(damage)
            self._modify_value(damage, 'real')
            damage = DamageDecreaseValue.from_multiply_value(damage)
            self._modify_value(damage, 'real')
            # apply final damage and applied elements
            hp_before = charactor.hp
            charactor.hp -= damage.damage
            if charactor.hp < 0:
                charactor.hp = 0
            charactor.element_application = applied_elements
            infos.append(ReceiveDamageEventArguments(
                action = action,
                original_damage = damage_original,
                final_damage = damage,
                hp_before = hp_before,
                hp_after = charactor.hp,
                elemental_reaction = elemental_reaction,
                reacted_elements = reacted_elements,
            ))
        make_damage_event = MakeDamageEventArguments(
            action = action,
            damages = infos,
            charactor_hps = [[c.hp for c in table.charactors] 
                             for table in self.player_tables],
            charactor_alive = [[c.is_alive for c in table.charactors] 
                               for table in self.player_tables],
        )
        events.append(make_damage_event)
        events += infos
        events.append(AfterMakeDamageEventArguments.
                      from_make_damage_event_arguments(make_damage_event))
        if next_charactor != self.player_tables[target_id].active_charactor_id:
            # charactor switch
            sw_action = SwitchCharactorAction(
                player_id = target_id,
                charactor_id = next_charactor,
            )
            sw_events = self._action_switch_charactor(sw_action)
            events += sw_events
        # TODO side-effect of elemental reaction
        # TODO when active charactor is defeated, trigger event
        return events

    def _action_charge(self, action: ChargeAction) \
            -> List[ChargeEventArguments]:
        player_id = action.player_id
        table = self.player_tables[player_id]
        charactor = table.charactors[table.active_charactor_id]
        logging.info(
            f'player {player_id} '
            f'charactor {charactor.name}:{table.active_charactor_id} '
            f'charged {action.charge}.'
        )
        old_charge = charactor.charge
        charactor.charge += action.charge
        if charactor.charge > charactor.max_charge:
            charactor.charge = charactor.max_charge
        return [ChargeEventArguments(
            action = action,
            charge_before = old_charge,
            charge_after = charactor.charge,
        )]

    def _action_charactor_defeated(self, action: CharactorDefeatedAction) \
            -> List[CharactorDefeatedEventArguments]:
        player_id = action.player_id
        charactor_id = action.charactor_id
        table = self.player_tables[player_id]
        charactor = table.charactors[charactor_id]
        logging.info(
            f'player {player_id} '
            f'charactor {charactor.name}:{charactor_id} '
            f'defeated.'
        )
        charactor.weapon = None
        charactor.artifact = None
        charactor.talent = None
        charactor.status = []
        charactor.element_application = []
        charactor.is_alive = False
        # TODO: for monsters, may disappear and generate new from candidate
        need_switch = False
        if table.active_charactor_id == charactor_id:
            table.active_charactor_id = -1  # reset active charactor
            need_switch = True
        return [CharactorDefeatedEventArguments(
            action = action,
            need_switch = need_switch,
        )]

    """
    Action funtions that only used to trigger specific event
    """

    def _action_skill_end(self, action: SkillEndAction) \
            -> List[SkillEndEventArguments]:
        player_id = action.player_id
        table = self.player_tables[player_id]
        charactor = table.charactors[table.active_charactor_id]
        logging.info(
            f'player {player_id} '
            f'charactor {charactor.name}:{table.active_charactor_id} '
            f'skill ended.'
        )
        return [SkillEndEventArguments(
            action = action,
        )]

    """
    Action functions that generate requests. Should not trigger event, i.e.
    return empty list.
    """

    def _action_generate_choose_charactor_request(
        self, action: GenerateChooseCharactorRequestAction
    ) -> List[EventArgumentsBase]:
        # TODO switch, not choose
        self._request_choose_charactor(action.player_id)
        return []
