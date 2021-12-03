import smartpy as sp


class MultisignWalletContract(sp.Contract):
    """This contract implements a basic multisign wallet.

    Users of the wallet can add their own proposals and vote proposals added by
    other users. The proposals can be executed when the number of minimum
    positive votes is reached.

    The contract implements the following types of proposals:

        - Transfer mutez from the contract to another account.
        - Transfer FA2 tokens from the contract to another account.
        - Change the minimum votes parameter.
        - Change the expiration time parameter.
        - Add a new user to the contract.
        - Remove one user from the contract.
        - Execute some arbitrary lambda function.

    """

    PROPOSAL_TYPE = sp.TRecord(
        # The type of proposal: transfer_mutez, transfer_token, add_user, etc
        type=sp.TString,
        # Flag to indicate if the proposal has been already executed
        executed=sp.TBool,
        # The user that submitted the proposal
        issuer=sp.TAddress,
        # The time when the proposal was submitted
        timestamp=sp.TTimestamp,
        # The number of positive votes that the proposal has received
        positive_votes=sp.TNat,
        # The number of mutez to transfer (only used in transfer_mutez proposals)
        mutez_amount=sp.TOption(sp.TMutez),
        # The token contract address (only used in transfer_token proposals)
        token_contract=sp.TOption(sp.TAddress),
        # The token id (only used in transfer_token proposals)
        token_id=sp.TOption(sp.TNat),
        # The number of token editions (only used in transfer_token proposals)
        token_amount=sp.TOption(sp.TNat),
        # The transfer destination (only userd in transfer_mutez and transfer_token proposals)
        destination=sp.TOption(sp.TAddress),
        # The minimum votes for accepting a proposal (only used in minimum_votes proposals)
        minimum_votes=sp.TOption(sp.TNat),
        # The proposal expiration time in days (only used in expiration_time proposals)
        expiration_time=sp.TOption(sp.TNat),
        # The address of the user to add or remove (only used in add_user and remove_user proposals)
        user=sp.TOption(sp.TAddress),
        # The lambda function to execute (only used in execute_lambda proposals)
        lambda_function=sp.TOption(sp.TLambda(sp.TUnit, sp.TList(sp.TOperation)))).layout((
            "type", (
                "executed", (
                    "issuer", (
                        "timestamp", (
                            "positive_votes", (
                                "mutez_amount", (
                                    "token_contract", (
                                        "token_id", (
                                            "token_amount", (
                                                "destination", (
                                                    "minimum_votes", (
                                                        "expiration_time", (
                                                            "user",
                                                            "lambda_function"))))))))))))))
    """The proposal type definition."""

    def __init__(self, users, minimum_votes, expiration_time=sp.nat(5)):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            users=sp.TSet(sp.TAddress),
            proposals=sp.TBigMap(sp.TNat, MultisignWalletContract.PROPOSAL_TYPE),
            votes=sp.TBigMap(sp.TPair(sp.TNat, sp.TAddress), sp.TBool),
            minimum_votes=sp.TNat,
            expiration_time=sp.TNat,
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            users=users,
            proposals=sp.big_map(),
            votes=sp.big_map(),
            minimum_votes=minimum_votes,
            expiration_time=expiration_time,
            counter=0)

    def check_is_user(self):
        """Checks that the address that called the entry point is from one of
        the users.

        """
        sp.verify(self.data.users.contains(sp.sender),
                  message="This can only be executed by one of the wallet users")

    def check_proposal_is_valid(self, proposal_id):
        """Checks that the proposal_id is from a valid proposal.

        """
        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(proposal_id),
                  message="The proposal doesn't exist")

        # Check that the proposal has not been executed
        proposal = self.data.proposals[proposal_id]
        sp.verify(~proposal.executed, message="The proposal has been executed")

        # Check that the proposal has not expired
        has_expired = sp.now > proposal.timestamp.add_days(sp.to_int(self.data.expiration_time))
        sp.verify(~has_expired, message="The proposal has expired")

    def add_proposal(self, type, mutez_amount=sp.none, token_contract=sp.none,
                     token_id=sp.none, token_amount=sp.none,
                     destination=sp.none, minimum_votes=sp.none,
                     expiration_time=sp.none, user=sp.none, lambda_function=sp.none):
        """Adds a new proposal to the proposals big map.

        """
        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type=type,
            executed=False,
            issuer=sp.sender,
            timestamp=sp.now,
            positive_votes=0,
            mutez_amount=mutez_amount,
            token_contract=token_contract,
            token_id=token_id,
            token_amount=token_amount,
            destination=destination,
            minimum_votes=minimum_votes,
            expiration_time=expiration_time,
            user=user,
            lambda_function=lambda_function)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def default(self, unit):
        """Default entrypoint that allows receiving tez and token transfers in
        the same way as one would do with a normal tz wallet.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Do nothing, just receive tez or tokens
        pass

    @sp.entry_point
    def transfer_mutez_proposal(self, params):
        """Adds a new transfer mutez proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            mutez_amount=sp.TMutez,
            destination=sp.TAddress).layout(("mutez_amount", "destination")))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("transfer_mutez",
                          mutez_amount=sp.some(params.mutez_amount),
                          destination=sp.some(params.destination))

    @sp.entry_point
    def transfer_token_proposal(self, params):
        """Adds a new transfer token proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            token_contract=sp.TAddress,
            token_id=sp.TNat,
            token_amount=sp.TNat,
            destination=sp.TAddress).layout(
                ("token_contract", ("token_id", ("token_amount", "destination")))))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("transfer_token",
                          token_contract=sp.some(params.token_contract),
                          token_id=sp.some(params.token_id),
                          token_amount=sp.some(params.token_amount),
                          destination=sp.some(params.destination))

    @sp.entry_point
    def minimum_votes_proposal(self, minimum_votes):
        """Adds a new minimum votes proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(minimum_votes, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposed minimum votes are at least 1
        sp.verify(minimum_votes >= 1,
                  message="The minimum_votes parameter cannot be smaller than 1")

        # Add the proposal
        self.add_proposal("minimum_votes",
                          minimum_votes=sp.some(minimum_votes))

    @sp.entry_point
    def expiration_time_proposal(self, expiration_time):
        """Adds a new expiration time proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(expiration_time, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposed expiration time is at least 1 day
        sp.verify(expiration_time >= 1,
                  message="The expiration_time parameter cannot be smaller than 1 day")

        # Add the proposal
        self.add_proposal("expiration_time",
                          expiration_time=sp.some(expiration_time))

    @sp.entry_point
    def add_user_proposal(self, user):
        """Adds a new add user proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(user, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the new user is not in the users list
        sp.verify(~self.data.users.contains(user),
                  message="The proposed address is in the users list")

        # Add the proposal
        self.add_proposal("add_user", user=sp.some(user))

    @sp.entry_point
    def remove_user_proposal(self, user):
        """Adds a new remove user proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(user, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the user to remove is in the users list
        sp.verify(self.data.users.contains(user),
                  message="The proposed address is not in the users list")

        # Add the proposal
        self.add_proposal("remove_user", user=sp.some(user))

    @sp.entry_point
    def lambda_proposal(self, lambda_function):
        """Adds a new lambda proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(lambda_function,
                    sp.TLambda(sp.TUnit, sp.TList(sp.TOperation)))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("lambda", lambda_function=sp.some(lambda_function))

    @sp.entry_point
    def vote_proposal(self, params):
        """Adds one vote for a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            approval=sp.TBool).layout(("proposal_id", "approval")))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that is a valid proposal
        self.check_proposal_is_valid(params.proposal_id)

        # Check if the user voted positive before and remove their previous vote
        # from the proposal positive votes counter
        proposal = self.data.proposals[params.proposal_id]

        sp.if self.data.votes.get((params.proposal_id, sp.sender), default_value=False):
            proposal.positive_votes = sp.as_nat(proposal.positive_votes - 1)

        # Add the vote to the proposal positive votes counter if it's positive
        sp.if params.approval:
            proposal.positive_votes += 1

        # Add or update the users vote
        self.data.votes[(params.proposal_id, sp.sender)] = params.approval

    @sp.entry_point
    def execute_proposal(self, proposal_id):
        """Executes a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that is a valid proposal
        self.check_proposal_is_valid(proposal_id)

        # Check that the proposal received enough positive votes
        proposal = self.data.proposals[proposal_id]
        sp.verify(proposal.positive_votes >= self.data.minimum_votes,
                  message="The proposal didn't receive enough positive votes")

        # Execute the proposal
        proposal.executed = True

        sp.if proposal.type == "transfer_mutez":
            sp.send(proposal.destination.open_some(),
                    proposal.mutez_amount.open_some())

        sp.if proposal.type == "transfer_token":
            self.fa2_transfer(
                fa2=proposal.token_contract.open_some(),
                from_=sp.self_address,
                to_=proposal.destination.open_some(),
                token_id=proposal.token_id.open_some(),
                token_amount=proposal.token_amount.open_some())

        sp.if proposal.type == "minimum_votes":
            sp.verify(proposal.minimum_votes.open_some() <= sp.len(self.data.users.elements()),
                      message="The minimum_votes parameter cannot be higher than the number of users")
            self.data.minimum_votes = proposal.minimum_votes.open_some()

        sp.if proposal.type == "expiration_time":
            self.data.expiration_time = proposal.expiration_time.open_some()

        sp.if proposal.type == "add_user":
            self.data.users.add(proposal.user.open_some())

        sp.if proposal.type == "remove_user":
            sp.verify(sp.len(self.data.users.elements()) > 1,
                      message="The last user cannot be removed")
            self.data.users.remove(proposal.user.open_some())

            # Update the minimum votes parameter if necessary
            sp.if self.data.minimum_votes > sp.len(self.data.users.elements()):
                self.data.minimum_votes = sp.len(self.data.users.elements())

        sp.if proposal.type == "lambda":
            operations = proposal.lambda_function.open_some()(sp.unit)
            sp.add_operations(operations)

    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
        """Transfers a number of editions of a FA2 token between to addresses.

        """
        # Get a handle to the FA2 token transfer entry point
        c = sp.contract(
            t=sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(sp.TRecord(
                    to_=sp.TAddress,
                    token_id=sp.TNat,
                    amount=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            address=fa2,
            entry_point="transfer").open_some()

        # Transfer the FA2 token editions to the new address
        sp.transfer(
            arg=sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    to_=to_,
                    token_id=token_id,
                    amount=token_amount)]))]),
            amount=sp.mutez(0),
            destination=c)


# Add a compilation target initialized to some random user accounts
sp.add_compilation_target("multisign", MultisignWalletContract(
    users=sp.set([sp.address("tz1gnL9CeM5h5kRzWZztFYLypCNnVQZjndBN"),
                  sp.address("tz1h9TG6uuxv2FtmE5yqMyKQqx8hkXk7NY6c")]),
    minimum_votes=sp.nat(2),
    expiration_time=sp.nat(3)))
