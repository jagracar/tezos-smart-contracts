import smartpy as sp


class PlayerContract(sp.Contract):
    """This contract implements a basic ping-pong player.

    """

    def __init__(self, player):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            player=sp.TAddress,
            games=sp.TMap(sp.TNat, sp.TRecord(
                court=sp.TAddress,
                opponent=sp.TAddress,
                ball_hits=sp.TNat)),
            moves=sp.TMap(sp.TString, sp.TString)))

        # Initialize the contract storage
        self.init(
            player=player,
            games=sp.map(),
            moves={"ping": "pong", "pong": "ping"})

    @sp.entry_point
    def add_game(self, params):
        """Adds a game to the player games map.

        """
        # Define the input parameter data types
        sp.set_type(params.game_id, sp.TNat)
        sp.set_type(params.court, sp.TAddress)
        sp.set_type(params.opponent, sp.TAddress)

        # Check that the player called the entry point
        sp.verify(sp.sender == self.data.player)

        # Check that the game has not been added before
        sp.verify(~self.data.games.contains(params.game_id))

        # Add the game to the games map
        self.data.games[params.game_id] = sp.record(
            court=params.court,
            opponent=params.opponent,
            ball_hits=0)

        # Accept the game at the court
        accept_game = sp.contract(
            sp.TRecord(game_id=sp.TNat, accept=sp.TBool), params.court,
            "accept_game").open_some()
        sp.transfer(sp.record(
            game_id=params.game_id, accept=True), sp.mutez(0), accept_game)

    @sp.entry_point
    def reset_game(self, params):
        """Resets the game counters.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the court called the entry point
        game = self.data.games[params]
        sp.verify(sp.sender == game.court)

        # Reset the ball hits counter
        game.ball_hits = 0

    @sp.entry_point
    def play_game(self, params):
        """Plays a ping-pong game that has been previously registered in the
        ping-pong court.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the player called the entry point
        sp.verify(sp.sender == self.data.player)

        # Send the request to play a game to the court
        play_game = sp.contract(
            sp.TNat, self.data.games[params].court, "play_game").open_some()
        sp.transfer(params, sp.mutez(0), play_game)

    @sp.entry_point
    def serve_ball(self, params):
        """Serves the ball.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the court called the entry point
        game = self.data.games[params]
        sp.verify(sp.sender == game.court)

        # Update the ball hits counter
        game.ball_hits += 1

        # Send the ball to the other player
        receive_ball = sp.contract(
            sp.TRecord(game_id=sp.TNat, kind=sp.TString),
            game.opponent, "receive_ball").open_some()
        sp.transfer(
            sp.record(game_id=params, kind="ping"),
            sp.mutez(0), receive_ball)

    @sp.entry_point
    def receive_ball(self, params):
        """Receives the ball from the opponent player and tries to return it.

        """
        # Define the input parameter data types
        sp.set_type(params.game_id, sp.TNat)
        sp.set_type(params.kind, sp.TString)

        # Check that the opponent called the entry point
        game = self.data.games[params.game_id]
        sp.verify(sp.sender == game.opponent)

        # Check if the opponent made a mistake
        sp.if params.kind == "ouch":
            # The player won the game. Send the game result to the court
            game_winner = sp.contract(
                sp.TNat, game.court, "game_winner").open_some()
            sp.transfer(params.game_id, sp.mutez(0), game_winner)
        sp.else:
            # Update the ball hits counter
            game.ball_hits += 1

            # Send the ball back to the opponent
            receive_ball = sp.contract(
                sp.TRecord(game_id=sp.TNat, kind=sp.TString),
                game.opponent, "receive_ball").open_some()

            sp.if game.ball_hits >= 3:
                # After more than 3 ball hits the player is tired and makes a
                # mistake...
                sp.transfer(
                    sp.record(game_id=params.game_id, kind="ouch"),
                    sp.mutez(0), receive_ball)
            sp.else:
                sp.transfer(
                    sp.record(
                        game_id=params.game_id,
                        kind=self.data.moves[params.kind]),
                    sp.mutez(0), receive_ball)


class CourtContract(sp.Contract):
    """This contract implements a ping-pong court where ping-pong games can be
    played between two players.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            games=sp.TMap(sp.TNat, sp.TRecord(
                players=sp.TMap(sp.TAddress, sp.TRecord(
                    accepted=sp.TBool,
                    opponent=sp.TAddress,
                    victories=sp.TNat)),
                started=sp.TBool,
                played_games=sp.TNat))))

        # Initialize the contract storage
        self.init(games=sp.map())

    @sp.entry_point
    def register_game(self, params):
        """Registers a ping-pong game between two players.

        """
        # Define the input parameter data types
        sp.set_type(params.game_id, sp.TNat)
        sp.set_type(params.player_1, sp.TAddress)
        sp.set_type(params.player_2, sp.TAddress)

        # Check that the game has not been registered before
        sp.verify(~self.data.games.contains(params.game_id))

        # Register the game in the games map
        self.data.games[params.game_id] = sp.record(
            players={
                params.player_1: sp.record(
                    accepted=False, opponent=params.player_2, victories=0),
                params.player_2: sp.record(
                    accepted=False, opponent=params.player_1, victories=0)},
            started=False,
            played_games=0)

    @sp.entry_point
    def accept_game(self, params):
        """The player gives his acceptance or not about a registered ping-pong
        game.

        """
        # Define the input parameter data types
        sp.set_type(params.game_id, sp.TNat)
        sp.set_type(params.accept, sp.TBool)

        # Check that the sender is one of the game players
        game = self.data.games[params.game_id]
        sp.verify(game.players.contains(sp.sender))

        # Save the player acceptance
        game.players[sp.sender].accepted = params.accept

    @sp.entry_point
    def play_game(self, params):
        """Plays a ping-pong game in the court between the two players.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that one of the players called the entry point
        game = self.data.games[params]
        sp.verify(game.players.contains(sp.sender))

        # Check that both players accecpted to play the game
        sp.verify(game.players[sp.sender].accepted)
        opponent = game.players[sp.sender].opponent
        sp.verify(game.players[opponent].accepted)

        # Check that the game didn't start yet
        sp.verify(~game.started)

        # Reset the players counters
        reset_game_sender = sp.contract(
            sp.TNat, sp.sender, "reset_game").open_some()
        sp.transfer(params, sp.mutez(0), reset_game_sender)
        reset_game_opponent = sp.contract(
            sp.TNat, opponent, "reset_game").open_some()
        sp.transfer(params, sp.mutez(0), reset_game_opponent)

        # Set the game as started and increase the played games counter
        game.started = True
        game.played_games += 1

        # Order the sender to serve the ball
        serve_ball = sp.contract(sp.TNat, sp.sender, "serve_ball").open_some()
        sp.transfer(params, sp.mutez(0), serve_ball)

    @sp.entry_point
    def game_winner(self, params):
        """Informs the caller is the winner of the game.

        """
        # Define the input parameter data types
        sp.set_type(params, sp.TNat)

        # Check that one of the players called the entry point
        game = self.data.games[params]
        sp.verify(game.players.contains(sp.sender))

        # Check that the game was started
        sp.verify(game.started)

        # Save the game result
        game.players[sp.sender].victories += 1

        # Set the game as finished
        game.started = False


# Add a compilation target
sp.add_compilation_target("court", CourtContract())
sp.add_compilation_target("player", PlayerContract(sp.address("tz111")))
