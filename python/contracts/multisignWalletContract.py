import smartpy as sp


class MultisignWalletContract(sp.Contract):
    """This contract implements a basic multisign wallet.

    Users of the wallet can add their own proposals and vote proposals added by
    other users. The proposals can be executed when the number of minimum
    positive votes is reached.

    The contract implements the following types of proposals:

        - Transfer tez from the wallet to another account.
        - Transfer FA2 tokens from the wallet to another account.
        - Change the minimum votes parameter.
        - Add a new user to the wallet.
        - Remove one user from the wallet.

    TBD:
        Add a proposal to execute another contract entrypoint. This could be
        used to collect an OBJKT using the collect entrypoint from the H=N
        marketplace contract. The required tez would be taken from the wallet
        and the OBJKT would be transferred to the multisign wallet contract.

    """

    def __init__(self, users, minimum_votes):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            users=sp.TSet(sp.TAddress),
            proposals=sp.TBigMap(sp.TNat, sp.TRecord(
                type=sp.TString,
                issuer=sp.TAddress,
                tez_amount=sp.TOption(sp.TMutez),
                token_contract=sp.TOption(sp.TAddress),
                token_id=sp.TOption(sp.TNat),
                token_amount=sp.TOption(sp.TNat),
                destination=sp.TOption(sp.TAddress),
                minimum_votes=sp.TOption(sp.TNat),
                user=sp.TOption(sp.TAddress),
                executed=sp.TBool)),
            votes=sp.TBigMap(sp.TPair(sp.TNat, sp.TAddress), sp.TBool),
            minimum_votes=sp.TNat,
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            users=sp.set(users),
            proposals=sp.big_map(),
            votes=sp.big_map(),
            minimum_votes=minimum_votes,
            counter=0)

    def check_is_user(self):
        """Checks that the address that called the entry point is one of the
        wallet users.

        """
        sp.verify(self.data.users.contains(sp.sender),
                  message="This can only be executed by one of the wallet users.")

    @sp.entry_point
    def transfer_tez_proposal(self, params):
        """Adds a new transfer tez proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            tez_amount=sp.TMutez,
            destination=sp.TAddress))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type="transfer_tez",
            issuer=sp.sender,
            tez_amount=sp.some(params.tez_amount),
            token_contract=sp.none,
            token_id=sp.none,
            token_amount=sp.none,
            destination=sp.some(params.destination),
            minimum_votes=sp.none,
            user=sp.none,
            executed=False)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def transfer_token_proposal(self, params):
        """Adds a new transfer token proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            token_contract=sp.TAddress,
            token_id=sp.TNat,
            token_amount=sp.TNat,
            destination=sp.TAddress))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type="transfer_token",
            issuer=sp.sender,
            tez_amount=sp.none,
            token_contract=sp.some(params.token_contract),
            token_id=sp.some(params.token_id),
            token_amount=sp.some(params.token_amount),
            destination=sp.some(params.destination),
            minimum_votes=sp.none,
            user=sp.none,
            executed=False)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def minimum_votes_proposal(self, params):
        """Adds a new minimum votes proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposed minimum votes makes sense
        sp.verify(params > 0,
                  message="The minimum_votes parameter should be higher than 0.")
        sp.verify(params <= sp.len(self.data.users.elements()),
                  message="The minimum_votes parameter cannot be higher than the number of users.")

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type="minimum_votes",
            issuer=sp.sender,
            tez_amount=sp.none,
            token_contract=sp.none,
            token_id=sp.none,
            token_amount=sp.none,
            destination=sp.none,
            minimum_votes=sp.some(params),
            user=sp.none,
            executed=False)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def add_user_proposal(self, params):
        """Adds a new add user proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the new user is not in the users list
        sp.verify(~self.data.users.contains(params),
                  message="The proposed address is in the users list.")

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type="add_user",
            issuer=sp.sender,
            tez_amount=sp.none,
            token_contract=sp.none,
            token_id=sp.none,
            token_amount=sp.none,
            destination=sp.none,
            minimum_votes=sp.none,
            user=sp.some(params),
            executed=False)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def remove_user_proposal(self, params):
        """Adds a new remove user proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the user to remove is in the users list
        sp.verify(self.data.users.contains(params),
                  message="The proposed address is not in the users list.")

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            type="remove_user",
            issuer=sp.sender,
            tez_amount=sp.none,
            token_contract=sp.none,
            token_id=sp.none,
            token_amount=sp.none,
            destination=sp.none,
            minimum_votes=sp.none,
            user=sp.some(params),
            executed=False)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def vote_proposal(self, params):
        """Adds one vote for a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            approval=sp.TBool))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(params.proposal_id),
                  message="The provided proposal id doesn't exist.")

        # Check that the proposal has not been executed
        sp.verify(~self.data.proposals[params.proposal_id].executed,
                  message="The provided proposal has been executed.")

        # Add or update the users vote
        self.data.votes[(params.proposal_id, sp.sender)] = params.approval

    @sp.entry_point
    def execute_proposal(self, params):
        """Executes a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(params),
                  message="The provided proposal id doesn't exist.")

        # Check that the proposal has not been executed
        proposal = self.data.proposals[params]

        sp.verify(~proposal.executed,
                  message="The provided proposal has already been executed.")

        # Count the proposal total number of positive votes
        totalVotes = sp.local("totalVotes", 0, sp.TNat)

        sp.for user in self.data.users.elements():
            sp.if self.data.votes.get((params, user), default_value=False):
                totalVotes.value += 1

        # Check that the proposal received enough positive votes
        sp.verify(totalVotes.value >= self.data.minimum_votes,
                  message="The proposal didn't receive enough positive votes to be executed.")

        # Execute the proposal
        sp.if proposal.type == "transfer_tez":
            sp.send(proposal.destination.open_some(),
                    proposal.tez_amount.open_some())

        sp.if proposal.type == "transfer_token":
            self.fa2_transfer(
                fa2=proposal.token_contract.open_some(),
                from_=sp.self_address,
                to_=proposal.destination.open_some(),
                token_id=proposal.token_id.open_some(),
                token_amount=proposal.token_amount.open_some())

        sp.if proposal.type == "minimum_votes":
            self.data.minimum_votes = proposal.minimum_votes.open_some()

        sp.if proposal.type == "add_user":
            self.data.users.add(proposal.user.open_some())

        sp.if proposal.type == "remove_user":
            self.data.users.remove(proposal.user.open_some())

            # Update the minimum votes parameter if necessary
            sp.if self.data.minimum_votes > sp.len(self.data.users.elements()):
                self.data.minimum_votes = sp.as_nat(self.data.minimum_votes - 1)

        # Set the proposal as executed
        proposal.executed = True

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
    users={sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicUser1"),
           sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicUser2"),
           sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicUser3"),
           sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicUser4")},
    minimum_votes=sp.nat(3)))
