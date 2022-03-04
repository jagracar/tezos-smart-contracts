"""Unit tests for the ping-pong game classes.

"""

import smartpy as sp

# Import the pingPongContract module
pingPongContract = sp.io.import_script_from_url(
    "file:python/contracts/pingPongContract.py")


@sp.add_test(name="Test player initialization")
def test_player_initialization():
    # Define the test account
    player = sp.address("tz1Player")

    # Initialize the contract
    player_contract = pingPongContract.PlayerContract(player)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += player_contract

    # Check that the information in the contract strorage is correct
    scenario.verify(player_contract.data.player == player)
    scenario.verify(sp.len(player_contract.data.games) == 0)
    scenario.verify(player_contract.data.moves["ping"] == "pong")
    scenario.verify(player_contract.data.moves["pong"] == "ping")


@sp.add_test(name="Test court initialization")
def test_court_initialization():
    # Initialize the contract
    court_contract = pingPongContract.CourtContract()

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += court_contract

    # Check that the information in the contract strorage is correct
    scenario.verify(sp.len(court_contract.data.games) == 0)


@sp.add_test(name="Test register game")
def test_register_game():
    # Define the test accounts
    player_1 = sp.address("tz1Player1")
    player_2 = sp.address("tz1Player2")

    # Initialize the contracts
    player_1_contract = pingPongContract.PlayerContract(player_1)
    player_2_contract = pingPongContract.PlayerContract(player_2)
    court_contract = pingPongContract.CourtContract()

    # Add the scontracts to the test scenario
    scenario = sp.test_scenario()
    scenario += player_1_contract
    scenario += player_2_contract
    scenario += court_contract

    # Register a game between the two players
    game_id = 3
    court_contract.register_game(sp.record(
        game_id=game_id,
        player_1=player_1_contract.address,
        player_2=player_2_contract.address))

    # Check that the information in the contract strorage is correct
    scenario.verify(sp.len(court_contract.data.games) == 1)
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].accepted == False)
    scenario.verify(game.players[
        player_1_contract.address].opponent == player_2_contract.address)
    scenario.verify(game.players[player_1_contract.address].victories == 0)
    scenario.verify(game.players[player_2_contract.address].accepted == False)
    scenario.verify(game.players[
        player_2_contract.address].opponent == player_1_contract.address)
    scenario.verify(game.players[player_2_contract.address].victories == 0)
    scenario.verify(~game.started)
    scenario.verify(game.played_games == 0)

    # Check that one cannot register the same game again
    court_contract.register_game(sp.record(
        game_id=game_id,
        player_1=player_1_contract.address,
        player_2=player_2_contract.address)).run(valid=False)


@sp.add_test(name="Test accept game")
def test_accept_game():
    # Define the test accounts
    player_1 = sp.address("tz1Player1")
    player_2 = sp.address("tz1Player2")

    # Initialize the contracts
    player_1_contract = pingPongContract.PlayerContract(player_1)
    player_2_contract = pingPongContract.PlayerContract(player_2)
    court_contract = pingPongContract.CourtContract()

    # Add the scontracts to the test scenario
    scenario = sp.test_scenario()
    scenario += player_1_contract
    scenario += player_2_contract
    scenario += court_contract

    # Register a game between the two players
    game_id = 5
    court_contract.register_game(sp.record(
        game_id=game_id,
        player_1=player_1_contract.address,
        player_2=player_2_contract.address))

    # Player 2 accepts the game
    court_contract.accept_game(sp.record(
        game_id=game_id, accept=True)).run(sender=player_2_contract.address)

    # Check that the information in the contract strorage is correct
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].accepted == False)
    scenario.verify(game.players[player_2_contract.address].accepted == True)


@sp.add_test(name="Test add game")
def test_add_game():
    # Define the test accounts
    player_1 = sp.address("tz1Player1")
    player_2 = sp.address("tz1Player2")

    # Initialize the contracts
    player_1_contract = pingPongContract.PlayerContract(player_1)
    player_2_contract = pingPongContract.PlayerContract(player_2)
    court_contract = pingPongContract.CourtContract()

    # Add the scontracts to the test scenario
    scenario = sp.test_scenario()
    scenario += player_1_contract
    scenario += player_2_contract
    scenario += court_contract

    # Register a game between the two players
    game_id = 5
    court_contract.register_game(sp.record(
        game_id=game_id,
        player_1=player_1_contract.address,
        player_2=player_2_contract.address))

    # Add the game to the two players
    player_1_contract.add_game(sp.record(
        game_id=game_id, court=court_contract.address,
        opponent=player_2_contract.address)).run(sender=player_1)
    player_2_contract.add_game(sp.record(
        game_id=game_id, court=court_contract.address,
        opponent=player_1_contract.address)).run(sender=player_2)

    # Check that the information in the contract strorages is correct
    scenario.verify(sp.len(player_1_contract.data.games) == 1)
    game = player_1_contract.data.games[game_id]
    scenario.verify(game.court == court_contract.address)
    scenario.verify(game.opponent == player_2_contract.address)
    scenario.verify(game.ball_hits == 0)
    game = player_2_contract.data.games[game_id]
    scenario.verify(game.court == court_contract.address)
    scenario.verify(game.opponent == player_1_contract.address)
    scenario.verify(game.ball_hits == 0)
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].accepted == True)
    scenario.verify(game.players[player_2_contract.address].accepted == True)


@sp.add_test(name="Test play game")
def test_play_game():
    # Define the test accounts
    player_1 = sp.address("tz1Player1")
    player_2 = sp.address("tz1Player2")

    # Initialize the contracts
    player_1_contract = pingPongContract.PlayerContract(player_1)
    player_2_contract = pingPongContract.PlayerContract(player_2)
    court_contract = pingPongContract.CourtContract()

    # Add the scontracts to the test scenario
    scenario = sp.test_scenario()
    scenario += player_1_contract
    scenario += player_2_contract
    scenario += court_contract

    # Register a game between the two players
    game_id = 5
    court_contract.register_game(sp.record(
        game_id=game_id,
        player_1=player_1_contract.address,
        player_2=player_2_contract.address))

    # Add the game to the two players
    player_1_contract.add_game(sp.record(
        game_id=game_id, court=court_contract.address,
        opponent=player_2_contract.address)).run(sender=player_1)
    player_2_contract.add_game(sp.record(
        game_id=game_id, court=court_contract.address,
        opponent=player_1_contract.address)).run(sender=player_2)

    # Play one game
    player_1_contract.play_game(game_id).run(sender=player_1)

    # Check that the information in the contract strorages is correct
    scenario.verify(player_1_contract.data.games[game_id].ball_hits == 3)
    scenario.verify(player_2_contract.data.games[game_id].ball_hits == 2)
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].victories == 0)
    scenario.verify(game.players[player_2_contract.address].victories == 1)
    scenario.verify(~game.started)
    scenario.verify(game.played_games == 1)

    # Play another game
    player_2_contract.play_game(game_id).run(sender=player_2)

    # Check that the information in the contract strorages is correct
    scenario.verify(player_1_contract.data.games[game_id].ball_hits == 2)
    scenario.verify(player_2_contract.data.games[game_id].ball_hits == 3)
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].victories == 1)
    scenario.verify(game.players[player_2_contract.address].victories == 1)
    scenario.verify(~game.started)
    scenario.verify(game.played_games == 2)

    # Play another game
    player_2_contract.play_game(game_id).run(sender=player_2)

    # Check that the information in the contract strorages is correct
    scenario.verify(player_1_contract.data.games[game_id].ball_hits == 2)
    scenario.verify(player_2_contract.data.games[game_id].ball_hits == 3)
    game = court_contract.data.games[game_id]
    scenario.verify(game.players[player_1_contract.address].victories == 2)
    scenario.verify(game.players[player_2_contract.address].victories == 1)
    scenario.verify(~game.started)
    scenario.verify(game.played_games == 3)
