from agents.interaction_agent import InteractionAgent
from server.match import Match, MatchState
from server.deck import Deck
from tests.utils_for_test import (
    get_test_id_from_command, make_respond, 
    get_random_state, set_16_omni
)


def test_liyue_harbor():
    cmd_records = [
        [
            "sw_card",
            "choose 0",
            "card 0 0 0 1",
            "card 0 0 0 1",
            "card 0 0 0 1",
            "card 0 0 0 1",
            "card 0 0 0 1",
            "end",
            "TEST 1 hand 10 8",
            "card 0 0 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "card 0 3 0 1",
            "end",
            "TEST 1 hand 10 10",
            "TEST 2 deck 5 17",
            "TEST 3 support 1 0",
            "end"
        ],
        [
            "sw_card",
            "choose 0",
            "card 0 0 0 1",
            "end",
            "end"
        ]
    ]
    agent_0 = InteractionAgent(
        player_idx = 0,
        verbose_level = 0,
        commands = cmd_records[0],
        only_use_command = True
    )
    agent_1 = InteractionAgent(
        player_idx = 1,
        verbose_level = 0,
        commands = cmd_records[1],
        only_use_command = True
    )
    # initialize match. It is recommended to use default random state to make
    # replay unchanged.
    match = Match(random_state = get_random_state())
    # deck information
    deck = Deck.from_str(
        '''
        charactor:PyroMobMage
        charactor:ElectroMobMage
        charactor:Noelle
        Liyue Harbor Wharf*30
        '''
    )
    match.set_deck([deck, deck])
    match.config.max_same_card_number = None
    match.config.charactor_number = None
    match.config.card_number = None
    # check whether random_first_player is enabled.
    match.config.random_first_player = False
    # check whether in rich mode (16 omni each round)
    set_16_omni(match)
    match.start()
    match.step()

    while True:
        if match.need_respond(0):
            agent = agent_0
        elif match.need_respond(1):
            agent = agent_1
        else:
            raise AssertionError('No need respond.')
        # do tests
        while True:
            cmd = agent.commands[0]
            test_id = get_test_id_from_command(agent)
            if test_id != 0:
                data = [int(x) for x in cmd.strip().split()[-2:]]
                assert len(data) == 2
            else:
                data = []
            if test_id == 0:
                # id 0 means current command is not a test command.
                break
            elif test_id == 1:
                # hand
                for table, d in zip(match.player_tables, data):
                    assert len(table.hands) == d
            elif test_id == 2:
                # deck
                for table, d in zip(match.player_tables, data):
                    assert len(table.table_deck) == d
            elif test_id == 3:
                # support
                for table, d in zip(match.player_tables, data):
                    assert len(table.supports) == d
            else:
                raise AssertionError(f'Unknown test id {test_id}')
        # respond
        make_respond(agent, match)
        if len(agent_1.commands) == 0 and len(agent_0.commands) == 0:
            break

    # simulate ends, check final state
    assert match.state != MatchState.ERROR


def test_tenshukaku():
    cmd_records = [
        [
            "sw_card",
            "choose 0",
            "reroll",
            "card 0 0 1 2",
            "card 0 0 1 2",
            "card 0 0 1 2",
            "TEST 1 no card can use",
            "end",
            "reroll",
            "TEST 2 dice number 11 8 over are omni",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "TEST 2 dice number 11 8 ...",
            "end",
            "reroll 2 5 6 7",
            "TEST 2 dice number 11 11",
            "end"
        ],
        [
            "sw_card",
            "choose 0",
            "reroll pyro dendro anemo",
            "card 0 0 2 3",
            "card 0 0 2 3",
            "card 0 0 0 1",
            "TEST 1 no card can use",
            "end",
            "reroll",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "end",
            "reroll"
        ]
    ]
    agent_0 = InteractionAgent(
        player_idx = 0,
        verbose_level = 0,
        commands = cmd_records[0],
        only_use_command = True
    )
    agent_1 = InteractionAgent(
        player_idx = 1,
        verbose_level = 0,
        commands = cmd_records[1],
        only_use_command = True
    )
    # initialize match. It is recommended to use default random state to make
    # replay unchanged.
    match = Match(random_state = get_random_state())
    # deck information
    deck = Deck.from_str(
        '''
        charactor:PyroMobMage
        charactor:ElectroMobMage
        charactor:Noelle
        Tenshukaku*30
        '''
    )
    match.set_deck([deck, deck])
    match.config.max_same_card_number = None
    match.config.charactor_number = None
    match.config.card_number = None
    # check whether random_first_player is enabled.
    match.config.random_first_player = False
    match.start()
    match.step()

    while True:
        if match.need_respond(0):
            agent = agent_0
        elif match.need_respond(1):
            agent = agent_1
        else:
            raise AssertionError('No need respond.')
        # do tests
        while True:
            cmd = agent.commands[0]
            test_id = get_test_id_from_command(agent)
            if test_id == 0:
                # id 0 means current command is not a test command.
                break
            elif test_id == 1:
                for req in match.requests:
                    assert req.name != 'UseCardRequest'
            elif test_id == 2:
                cmd = cmd.strip().split()
                dn = [int(cmd[4]), int(cmd[5])]
                for table, d in zip(match.player_tables, dn):
                    assert len(table.dice.colors) == d
                    part = table.dice.colors[:-8]
                    for c in part:
                        assert c == 'OMNI'
            else:
                raise AssertionError(f'Unknown test id {test_id}')
        # respond
        make_respond(agent, match)
        if len(agent_1.commands) == 0 and len(agent_0.commands) == 0:
            break

    # simulate ends, check final state
    assert match.state != MatchState.ERROR


def test_sumeru_city():
    cmd_records = [
        [
            "sw_card",
            "choose 2",
            "reroll 0 7",
            "card 3 2 cryo electro",
            "card 2 0 0 1",
            "TEST 1 skill cost 2",
            "card 2 0 0 1",
            "TEST 1 skill cost 0",
            "card 0 0",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "TEST 1 skill cost 2",
            "card 1 0 6 7",
            "sw_char 0 0",
            "sw_char 1 0",
            "sw_char 0 2",
            "sw_char 2 2",
            "TEST 1 skill cost 0",
            "skill 0",
            "TEST 1 skill cost 2",
            "skill 1 0 1",
            "end",
            "reroll 0 1 2 3 4 6 7",
            "end",
            "reroll",
            "end",
            "reroll",
            "end"
        ],
        [
            "sw_card",
            "choose 2",
            "reroll",
            "card 0 0 1 2",
            "card 0 0 2 3",
            "TEST 1 skill cost 3",
            "card 0 0 0 2",
            "TEST 1 skill cost 0",
            "tune 0 0",
            "TEST 2 no skill",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "end",
            "reroll",
            "end",
            "reroll",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "TEST 1 skill cost 0",
            "card 3 0",
            "card 0 0 0 1",
            "card 0 0 1 2",
            "TEST 1 skill cost 1",
            "tune 1 0",
            "tune 0 3",
            "tune 0 3",
            "TEST 1 skill cost 3",
            "sw_char 1 0",
            "sw_char 2 0",
            "TEST 1 skill cost 1",
            "end"
        ]
    ]
    agent_0 = InteractionAgent(
        player_idx = 0,
        verbose_level = 0,
        commands = cmd_records[0],
        only_use_command = True
    )
    agent_1 = InteractionAgent(
        player_idx = 1,
        verbose_level = 0,
        commands = cmd_records[1],
        only_use_command = True
    )
    # initialize match. It is recommended to use default random state to make
    # replay unchanged.
    match = Match(random_state = get_random_state())
    # deck information
    deck = Deck.from_str(
        '''
        charactor:PyroMobMage
        charactor:ElectroMobMage
        charactor:Noelle
        Sumeru City*15
        I Got Your Back*10
        # Archaic Petra
        Mask of Solitude Basalt*5
        '''
    )
    match.set_deck([deck, deck])
    match.config.max_same_card_number = None
    match.config.charactor_number = None
    match.config.card_number = None
    # check whether random_first_player is enabled.
    match.config.random_first_player = False
    match.start()
    match.step()

    while True:
        if match.need_respond(0):
            agent = agent_0
        elif match.need_respond(1):
            agent = agent_1
        else:
            raise AssertionError('No need respond.')
        # do tests
        while True:
            cmd = agent.commands[0]
            test_id = get_test_id_from_command(agent)
            if test_id == 0:
                # id 0 means current command is not a test command.
                break
            elif test_id == 1:
                cmd = cmd.strip().split()
                cost = int(cmd[-1])
                for req in match.requests:
                    if req.name == 'UseSkillRequest':
                        assert req.cost.total_dice_cost == cost
            elif test_id == 2:
                for req in match.requests:
                    assert req.name != "UseSkillRequest"
            else:
                raise AssertionError(f'Unknown test id {test_id}')
        # respond
        make_respond(agent, match)
        if len(agent_1.commands) == 0 and len(agent_0.commands) == 0:
            break

    # simulate ends, check final state
    assert match.state != MatchState.ERROR


def test_vanarana():
    """
    """
    agent_0 = InteractionAgent(
        player_idx = 0,
        verbose_level = 0,
        commands = [
            "sw_card",
            "choose 0",
            "reroll",
            "card 0 0",
            "card 0 0",
            "card 0 0",
            "card 0 0",
            "end",
            "TEST 1 8 dice and all usage",
            "reroll",
            "TEST 2 16 dice",
            "card 0 0",
            "sw_char 2 0",
            "sw_char 0 0",
            "sw_char 2 0",
            "sw_char 0 0",
            "sw_char 2 0",
            "sw_char 0 0",
            "sw_char 2 0",
            "sw_char 0 0",
            "sw_char 2 0",
            "end",
            "TEST 3 7 dice",
            "reroll",
            "end",
            "reroll",
            "end",
            "TEST 4 ppeeggdd+cccheaoo",
            "reroll",
        ],
        only_use_command = True
    )
    agent_1 = InteractionAgent(
        player_idx = 1,
        verbose_level = 0,
        commands = [
            "sw_card",
            "choose 0",
            "reroll",
            "card 0 0",
            "card 0 0",
            "card 0 0",
            "card 0 0",
            "card 0 0",
            "end",
            "reroll",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "end",
            "reroll 0 1 2 3 4 5 6 7",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "sw_char 0 1",
            "sw_char 2 1",
            "end",
            "reroll 1 2 3 4 5 6 7",
            "end"
        ],
        only_use_command = True
    )
    match = Match(random_state = get_random_state())
    deck = Deck.from_str(
        '''
        charactor:Fischl
        charactor:Mona
        charactor:Nahida
        # Gambler's Earrings*2
        # Wine-Stained Tricorne*2
        # Vanarana
        # Timmie*2
        # Rana*2
        # Strategize*2
        # The Bestest Travel Companion!*2
        # Covenant of Rock
        Vanarana*30
        '''
    )
    match.set_deck([deck, deck])
    match.config.max_same_card_number = 30
    match.config.random_first_player = False
    assert match.start()
    match.step()

    while True:
        if match.need_respond(0):
            while True:
                test_id = get_test_id_from_command(agent_0)
                if test_id == 1:
                    current_colors = [
                        match.player_tables[0].dice.colors.copy(),
                        match.player_tables[1].dice.colors.copy()
                    ]
                    assert len(current_colors[0]) == 8
                    assert len(current_colors[1]) == 8
                    assert len(match.player_tables[0].supports) == 4
                    assert len(match.player_tables[1].supports) == 4
                    colors = [
                        ['HYDRO', 'HYDRO'],
                        ['HYDRO', 'HYDRO'],
                        ['GEO', 'GEO'],
                        ['CRYO', 'ANEMO']
                    ]
                    for support, color in zip(
                        match.player_tables[0].supports, colors
                    ):
                        assert support.name == 'Vanarana'
                        assert support.usage == 2
                        assert support.colors == color
                    colors = [
                        ['HYDRO', 'HYDRO'],
                        ['ELECTRO', 'ELECTRO'],
                        ['PYRO', 'DENDRO'],
                        ['ANEMO', 'OMNI']
                    ]
                    for support, color in zip(
                        match.player_tables[1].supports, colors
                    ):
                        assert support.name == 'Vanarana'
                        assert support.usage == 2
                        assert support.colors == color
                elif test_id == 2:
                    assert len(match.player_tables[0].dice.colors) == 16
                    assert len(match.player_tables[1].dice.colors) == 16
                elif test_id == 3:
                    supports = match.player_tables[0].supports
                    assert len(supports) == 4
                    assert supports[3].usage == 1
                    for i in range(3):
                        assert supports[i].usage == 2
                    colors = [
                        ['GEO', 'GEO'],
                        ['DENDRO', 'DENDRO'],
                        ['ELECTRO', 'GEO'],
                        ['ANEMO']
                    ]
                    for support, c in zip(supports, colors):
                        assert support.name == 'Vanarana'
                        assert support.colors == c
                    supports = match.player_tables[1].supports
                    assert len(supports) == 4
                    assert supports[0].usage == 1
                    for i in range(3):
                        assert supports[i + 1].usage == 0
                    colors = [
                        ['OMNI'],
                        [],
                        [],
                        []
                    ]
                    for support, c in zip(supports, colors):
                        assert support.name == 'Vanarana'
                        assert support.colors == c
                elif test_id == 4:
                    supports = (
                        match.player_tables[0].supports
                        + match.player_tables[1].supports
                    )
                    assert len(supports) == 8
                    colors = [
                        ['CRYO', 'CRYO'],
                        ['PYRO', 'PYRO'],
                        ['ELECTRO', 'ELECTRO'],
                        ['GEO', 'GEO'],
                        ['CRYO', 'CRYO'],
                        ['CRYO', 'HYDRO'],
                        ['ELECTRO', 'ANEMO'],
                        ['OMNI', 'OMNI']
                    ]
                    for support, c in zip(supports, colors):
                        assert support.name == 'Vanarana'
                        assert support.colors == c
                else:
                    break
            make_respond(agent_0, match)
        elif match.need_respond(1):
            make_respond(agent_1, match)
        else:
            raise AssertionError('No need respond.')
        if len(agent_1.commands) == 0 and len(agent_0.commands) == 0:
            break

    assert match.state != MatchState.ERROR


if __name__ == '__main__':
    test_liyue_harbor()
    test_tenshukaku()
    test_sumeru_city()
    test_vanarana()
