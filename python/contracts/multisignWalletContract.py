"""A multisg / mini-DAO contract.

Users of the wallet can add their own proposals and vote proposals added by
other users. The proposals can be executed when the number of minimum positive
votes is reached.

The contract implements the following kinds of proposals:

    - Text submitted for approval and stored in ipfs.
    - Transfer mutez from the contract to other accounts.
    - Transfer a FA2 token from the contract to other accounts.
    - Change the minimum votes parameter.
    - Change the expiration time parameter.
    - Add a new user to the contract.
    - Remove one user from the contract.
    - Execute some arbitrary lambda function.


Error message codes:

    - MS_NOT_USER: The operation can only be executed by one of the multisig wallet users.
    - MS_INEXISTENT_PROPOSAL: The given proposal id doesn't exist.
    - MS_EXECUTED_PROPOSAL: The proposal has been executed and cannot be voted or executed anymore.
    - MS_EXPIRED_PROPOSAL: The proposal has expired and cannot be voted or executed anymore.
    - MS_WRONG_MINIMUM_VOTES: The minimum_votes parameter cannot be smaller than 1 or higher than the number of users.
    - MS_WRONG_EXPIRATION_TIME: The expiration_time parameter cannot be smaller than 1 day.
    - MS_ALREADY_USER: The proposed address is already a multsig user.
    - MS_WRONG_USER: The proposed address is not a multisig user.
    - MS_NOT_EXECUTABLE: The proposal didn't receive enough positive votes to be executed.
    - MS_LAST_USER: The last user cannot be removed.
    - MS_NO_USER_VOTE: The user didn't vote for the proposal.

"""

import smartpy as sp


class MultisigWalletContract(sp.Contract):
    """This contract implements a basic multisig wallet / mini-DAO.

    """

    PROPOSAL_KIND_TYPE = sp.TVariant(
        # A proposal in the form of text to be voted for
        text=sp.TUnit,
        # A proposal to transfer mutez from the contract to other accounts
        transfer_mutez=sp.TUnit,
        # A proposal to transfer a token from the contract to other accounts
        transfer_token=sp.TUnit,
        # A proposal to change the minimum votes parameter
        minimum_votes=sp.TUnit,
        # A proposal to change the expiration time parameter
        expiration_time=sp.TUnit,
        # A proposal to add a new user to the wallet
        add_user=sp.TUnit,
        # A proposal to remove a user from the wallet
        remove_user=sp.TUnit,
        # A proposal to execute a lambda function
        lambda_function=sp.TUnit)

    MUTEZ_TRANSFERS_TYPE = sp.TList(sp.TRecord(
        # The amount of mutez to transfer
        amount=sp.TMutez,
        # The transfer destination
        destination=sp.TAddress).layout(("amount", "destination")))

    TOKEN_TRANSFERS_TYPE = sp.TRecord(
        # The token contract address
        fa2=sp.TAddress,
        # The token id
        token_id=sp.TNat,
        # The token transfer distribution
        distribution=sp.TList(sp.TRecord(
            # The number of token editions to transfer
            amount=sp.TNat,
            # The transfer destination
            destination=sp.TAddress).layout(("amount", "destination")))).layout(
                ("fa2", ("token_id", "distribution")))

    LAMBDA_FUNCTION_TYPE = sp.TLambda(sp.TUnit, sp.TList(sp.TOperation))

    PROPOSAL_TYPE = sp.TRecord(
        # The kind of proposal: transfer_mutez, transfer_token, add_user, etc
        kind=PROPOSAL_KIND_TYPE,
        # Flag to indicate if the proposal has been already executed
        executed=sp.TBool,
        # The user that submitted the proposal
        issuer=sp.TAddress,
        # The time when the proposal was submitted
        timestamp=sp.TTimestamp,
        # The number of positive votes that the proposal has received
        positive_votes=sp.TNat,
        # The proposed text stored in an ipfs file
        text=sp.TOption(sp.TBytes),
        # The list of mutez transfers (only used in transfer_mutez proposals)
        mutez_transfers=sp.TOption(MUTEZ_TRANSFERS_TYPE),
        # The list of token transfers (only used in transfer_token proposals)
        token_transfers=sp.TOption(TOKEN_TRANSFERS_TYPE),
        # The minimum votes for executing a proposal (only used in minimum_votes proposals)
        minimum_votes=sp.TOption(sp.TNat),
        # The proposal expiration time in days (only used in expiration_time proposals)
        expiration_time=sp.TOption(sp.TNat),
        # The address of the user to add or remove (only used in add_user and remove_user proposals)
        user=sp.TOption(sp.TAddress),
        # The lambda function to execute (only used in lambda_function proposals)
        lambda_function=sp.TOption(LAMBDA_FUNCTION_TYPE)).layout((
            "kind", (
                "executed", (
                    "issuer", (
                        "timestamp", (
                            "text", (
                                "positive_votes", (
                                    "mutez_transfers", (
                                        "token_transfers", (
                                            "minimum_votes", (
                                                "expiration_time", (
                                                    "user", "lambda_function"))))))))))))

    FA2_TX_TYPE = sp.TRecord(
        # The token destination
        to_=sp.TAddress,
        # The token id
        token_id=sp.TNat,
        # The number of token editions
        amount=sp.TNat).layout(("to_", ("token_id", "amount")))


    def __init__(self, metadata, users, minimum_votes, expiration_time=sp.nat(5)):
        """Initializes the contract.

        Parameters
        ----------
        metadata: sp.TBigMap(sp.TString, sp.TBytes)
            The contract metadata big map. It should contain the IPFS path to
            the contract metadata json file.
        users: sp.TSet(sp.TAddress)
            The set of initial multisig user addresses.
        minimum_votes: sp.TNat
            The minimum number of positive votes required to execute a proposal.
        expiration_time: sp.TNat, optional
            The proposals expiration time in days. Default is 5 days.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata bigmap.
            # The metadata is stored as a json file in IPFS and the big map
            # contains the IPFS path.
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The multisig users that can propose, vote and execute proposals.
            users=sp.TSet(sp.TAddress),
            # The big map with the proposals information.
            proposals=sp.TBigMap(sp.TNat, MultisigWalletContract.PROPOSAL_TYPE),
            # The big map with the votes information.
            votes=sp.TBigMap(sp.TPair(sp.TNat, sp.TAddress), sp.TBool),
            # The minimum number of positive votes required to execute a
            # proposal.
            minimum_votes=sp.TNat,
            # The proposals expiration time in days.
            expiration_time=sp.TNat,
            # The proposals bigmap counter. It tracks the total number of
            # proposals in the proposals big map.
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
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
        sp.verify(self.data.users.contains(sp.sender), message="MS_NOT_USER")

    def check_proposal_is_valid(self, proposal_id):
        """Checks that the proposal_id is from a valid proposal.

        Parameters
        ----------
        proposal_id: sp.TNat
            The proposal id. It refers to the proposals big map key containing
            the proposal parameters.

        """
        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(proposal_id),
                  message="MS_INEXISTENT_PROPOSAL")

        # Check that the proposal has not been executed
        proposal = self.data.proposals[proposal_id]
        sp.verify(~proposal.executed, message="MS_EXECUTED_PROPOSAL")

        # Check that the proposal has not expired
        has_expired = sp.now > proposal.timestamp.add_days(sp.to_int(self.data.expiration_time))
        sp.verify(~has_expired, message="MS_EXPIRED_PROPOSAL")

    def add_proposal(self, kind, text=sp.none, mutez_transfers=sp.none,
                     token_transfers=sp.none, minimum_votes=sp.none,
                     expiration_time=sp.none, user=sp.none,
                     lambda_function=sp.none):
        """Adds a new proposal to the proposals big map.

        Parameters
        ----------
        kind: sp.TString
            The kind of proposal.
        text: sp.TOption(sp.TBytes), optional
            The proposed text stored in an ipfs file. Default is sp.none.
        mutez_transfers: sp.TOption(MUTEZ_TRANSFERS_TYPE), optional
            The list of mutez transfers. Default is sp.none.
        token_transfers: sp.TOption(TOKEN_TRANSFERS_TYPE), optional
            The list of token transfers. Default is sp.none.
        minimum_votes: sp.TOption(sp.TNat), optional
            The minimum votes for executing a proposal. Default is sp.none.
        expiration_time: sp.TOption(sp.TNat), optional
            The proposal expiration time in days. Default is sp.none.
        user: sp.TOption(sp.TAddress), optional
            The address of the user to add or remove. Default is sp.none.
        lambda_function: sp.TOption(LAMBDA_FUNCTION_TYPE), optional
            The lambda function to execute. Default is sp.none.

        """
        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            kind=sp.variant(kind, sp.unit),
            executed=False,
            issuer=sp.sender,
            timestamp=sp.now,
            positive_votes=0,
            text=text,
            mutez_transfers=mutez_transfers,
            token_transfers=token_transfers,
            minimum_votes=minimum_votes,
            expiration_time=expiration_time,
            user=user,
            lambda_function=lambda_function)

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def default(self, unit):
        """Default entrypoint that allows receiving tez transfers in the same
        way as one would do with a normal tz wallet.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Do nothing, just receive tez
        pass

    @sp.entry_point
    def text_proposal(self, text):
        """Adds a new text proposal to the proposals big map.

        Parameters
        ----------
        text: sp.TBytes
            The proposed text stored in an ipfs file.

        """
        # Define the input parameter data type
        sp.set_type(text, sp.TBytes)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("text", text=sp.some(text))

    @sp.entry_point
    def transfer_mutez_proposal(self, mutez_transfers):
        """Adds a new transfer mutez proposal to the proposals big map.

        Parameters
        ----------
        mutez_transfers: MUTEZ_TRANSFERS_TYPE
            The list of mutez transfers.

        """
        # Define the input parameter data type
        sp.set_type(mutez_transfers, MultisigWalletContract.MUTEZ_TRANSFERS_TYPE)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("transfer_mutez", mutez_transfers=sp.some(mutez_transfers))

    @sp.entry_point
    def transfer_token_proposal(self, token_transfers):
        """Adds a new transfer token proposal to the proposals big map.

        Parameters
        ----------
        token_transfers: TOKEN_TRANSFERS_TYPE
            The list of token transfers.

        """
        # Define the input parameter data type
        sp.set_type(token_transfers, MultisigWalletContract.TOKEN_TRANSFERS_TYPE)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("transfer_token", token_transfers=sp.some(token_transfers))

    @sp.entry_point
    def minimum_votes_proposal(self, minimum_votes):
        """Adds a new minimum votes proposal to the proposals big map.

        Parameters
        ----------
        minimum_votes: sp.TNat
            The minimum votes for executing a proposal.

        """
        # Define the input parameter data type
        sp.set_type(minimum_votes, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposed minimum votes are at least 1
        sp.verify(minimum_votes >= 1, message="MS_WRONG_MINIMUM_VOTES")

        # Add the proposal
        self.add_proposal("minimum_votes", minimum_votes=sp.some(minimum_votes))

    @sp.entry_point
    def expiration_time_proposal(self, expiration_time):
        """Adds a new expiration time proposal to the proposals big map.

        Parameters
        ----------
        expiration_time: sp.TNat
            The proposal expiration time in days.

        """
        # Define the input parameter data type
        sp.set_type(expiration_time, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the proposed expiration time is at least 1 day
        sp.verify(expiration_time >= 1, message="MS_WRONG_EXPIRATION_TIME")

        # Add the proposal
        self.add_proposal("expiration_time", expiration_time=sp.some(expiration_time))

    @sp.entry_point
    def add_user_proposal(self, user):
        """Adds a new add user proposal to the proposals big map.

        Parameters
        ----------
        user: sp.TAddress
            The address of the user to add.

        """
        # Define the input parameter data type
        sp.set_type(user, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the new user is not in the users list
        sp.verify(~self.data.users.contains(user), message="MS_ALREADY_USER")

        # Add the proposal
        self.add_proposal("add_user", user=sp.some(user))

    @sp.entry_point
    def remove_user_proposal(self, user):
        """Adds a new remove user proposal to the proposals big map.

        Parameters
        ----------
        user: sp.TAddress
            The address of the user to remove.

        """
        # Define the input parameter data type
        sp.set_type(user, sp.TAddress)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that the user to remove is in the users list
        sp.verify(self.data.users.contains(user), message="MS_WRONG_USER")

        # Add the proposal
        self.add_proposal("remove_user", user=sp.some(user))

    @sp.entry_point
    def lambda_function_proposal(self, lambda_function):
        """Adds a new lambda function proposal to the proposals big map.

        Parameters
        ----------
        lambda_function: LAMBDA_FUNCTION_TYPE
            The lambda function to execute.

        """
        # Define the input parameter data type
        sp.set_type(lambda_function, MultisigWalletContract.LAMBDA_FUNCTION_TYPE)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Add the proposal
        self.add_proposal("lambda_function", lambda_function=sp.some(lambda_function))

    @sp.entry_point
    def vote_proposal(self, vote):
        """Adds one vote for a given proposal.

        Parameters
        ----------
        vote: sp.TRecord
            The user vote information:
            - proposal_id: The proposal id. It refers to the proposals big map
              key containing the proposal parameters.
            - approval: true for a positive vote, false for a negative vote.

        """
        # Define the input parameter data type
        sp.set_type(vote, sp.TRecord(
            proposal_id=sp.TNat,
            approval=sp.TBool).layout(("proposal_id", "approval")))

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that is a valid proposal
        self.check_proposal_is_valid(vote.proposal_id)

        # Check if the user voted positive before and remove their previous vote
        # from the proposal positive votes counter
        proposal = self.data.proposals[vote.proposal_id]

        sp.if self.data.votes.get((vote.proposal_id, sp.sender), default_value=False):
            proposal.positive_votes = sp.as_nat(proposal.positive_votes - 1)

        # Add the vote to the proposal positive votes counter if it's positive
        sp.if vote.approval:
            proposal.positive_votes += 1

        # Add or update the users vote
        self.data.votes[(vote.proposal_id, sp.sender)] = vote.approval

    @sp.entry_point
    def execute_proposal(self, proposal_id):
        """Executes a given proposal.

        Note that in the case of executing a transfer token proposal, if the
        token is not owned by the multisig, the owner of the token should add
        the multisig as an operator of the token. It's recommended to remove
        the multisig operator rights after calling this entry point.

        Parameters
        ----------
        proposal_id: sp.TNat
            The proposal id. It refers to the proposals big map key containing
            the proposal parameters.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that one of the users executed the entry point
        self.check_is_user()

        # Check that is a valid proposal
        self.check_proposal_is_valid(proposal_id)

        # Check that the proposal received enough positive votes
        proposal = sp.local("proposal", self.data.proposals[proposal_id])
        sp.verify(proposal.value.positive_votes >= self.data.minimum_votes,
                  message="MS_NOT_EXECUTABLE")

        # Execute the proposal
        self.data.proposals[proposal_id].executed = True

        sp.if proposal.value.kind.is_variant("transfer_mutez"):
            sp.for mutez_transfer in proposal.value.mutez_transfers.open_some():
                sp.send(mutez_transfer.destination, mutez_transfer.amount)

        sp.if proposal.value.kind.is_variant("transfer_token"):
            txs = sp.local("txs", sp.list(t=MultisigWalletContract.FA2_TX_TYPE))
            token_transfers = proposal.value.token_transfers.open_some()

            sp.for distribution in token_transfers.distribution:
                txs.value.push(sp.record(
                    to_=distribution.destination,
                    token_id=token_transfers.token_id,
                    amount=distribution.amount))

            self.fa2_transfer(token_transfers.fa2, sp.self_address, txs.value)

        sp.if proposal.value.kind.is_variant("minimum_votes"):
            sp.verify(proposal.value.minimum_votes.open_some() <= sp.len(self.data.users.elements()),
                      message="MS_WRONG_MINIMUM_VOTES")
            self.data.minimum_votes = proposal.value.minimum_votes.open_some()

        sp.if proposal.value.kind.is_variant("expiration_time"):
            self.data.expiration_time = proposal.value.expiration_time.open_some()

        sp.if proposal.value.kind.is_variant("add_user"):
            self.data.users.add(proposal.value.user.open_some())

        sp.if proposal.value.kind.is_variant("remove_user"):
            sp.verify(sp.len(self.data.users.elements()) > 1,
                      message="MS_LAST_USER")
            self.data.users.remove(proposal.value.user.open_some())

            # Update the minimum votes parameter if necessary
            sp.if self.data.minimum_votes > sp.len(self.data.users.elements()):
                self.data.minimum_votes = sp.len(self.data.users.elements())

        sp.if proposal.value.kind.is_variant("lambda_function"):
            operations = proposal.value.lambda_function.open_some()(sp.unit)
            sp.add_operations(operations)

    @sp.onchain_view()
    def get_users(self):
        """Returns the multisig wallet users.

        Returns
        -------
        sp.TSet(sp.TAddress)
            The multisig wallet users.

        """
        sp.result(self.data.users)

    @sp.onchain_view()
    def is_user(self, user):
        """Checks if the given address is one of the multisig wallet users.

        Parameters
        ----------
        user: sp.TAddress
            The user address.

        Returns
        -------
        sp.TBool
            True, if the address is one of the multisig wallet users.

        """
        # Define the input parameter data type
        sp.set_type(user, sp.TAddress)

        # Return true if the user is part of the multisig wallet users
        sp.result(self.data.users.contains(user))

    @sp.onchain_view()
    def get_minimum_votes(self):
        """Returns the minimum votes parameter.

        Returns
        -------
        sp.TNat
            The multisig minimum votes parameter.

        """
        sp.result(self.data.minimum_votes)

    @sp.onchain_view()
    def get_expiration_time(self):
        """Returns the expiration time parameter.

        Returns
        -------
        sp.TNat
            The multisig proposals expiration time parameter in days.

        """
        sp.result(self.data.expiration_time)

    @sp.onchain_view()
    def get_proposal_count(self):
        """Returns the total number of proposals.

        Returns
        -------
        sp.TNat
            The total number of proposals.

        """
        sp.result(self.data.counter)

    @sp.onchain_view()
    def get_proposal(self, proposal_id):
        """Returns the complete information from a given proposal.

        Parameters
        ----------
        proposal_id: sp.TNat
            The proposal id. It refers to the proposals big map key containing
            the proposal parameters.

        Returns
        -------
        PROPOSAL_TYPE
            The proposal parameters.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(proposal_id),
                  message="MS_INEXISTENT_PROPOSAL")

        # Return the proposal information
        sp.result(self.data.proposals[proposal_id])

    @sp.onchain_view()
    def get_vote(self, vote):
        """Returns a user's vote.

        Parameters
        ----------
        vote: sp.TRecord
            The user vote information:
            - proposal_id: The proposal id. It refers to the proposals big map
              key containing the proposal parameters.
            - user: The user address.

        Returns
        -------
        sp.TBool
            True, if the user voted YES to the proposal. False, if the user
            voted NO to the proposal.

        """
        # Define the input parameter data type
        sp.set_type(vote, sp.TRecord(
            proposal_id=sp.TNat,
            user=sp.TAddress).layout(("proposal_id", "user")))

        # Check that the vote is present in the votes big map
        sp.verify(self.data.votes.contains((vote.proposal_id, vote.user)),
                  message="MS_NO_USER_VOTE")

        # Return the user's vote
        sp.result(self.data.votes[(vote.proposal_id, vote.user)])

    @sp.onchain_view()
    def has_voted(self, vote):
        """Returns true if the user has voted the given proposal.

        Parameters
        ----------
        vote: sp.TRecord
            The user vote information:
            - proposal_id: The proposal id. It refers to the proposals big map
              key containing the proposal parameters.
            - user: The user address.

        Returns
        -------
        sp.TBool
            True, if the user has voted the proposal. False, if the user didn't
            vote the proposal.

        """
        # Define the input parameter data type
        sp.set_type(vote, sp.TRecord(
            proposal_id=sp.TNat,
            user=sp.TAddress).layout(("proposal_id", "user")))

        # Return true if the user has voted the proposal
        sp.result(self.data.votes.contains((vote.proposal_id, vote.user)))

    def fa2_transfer(self, fa2, from_, txs):
        """Transfers a number of editions of a FA2 token to several wallets.

        Parameters
        ----------
        fa2: sp.TAddress
            The FA2 token contract address.
        from_: sp.TAddress
            The address from which the tokens will be transferred.
        txs: sp.TList(FA2_TX_TYPE)
            The list of transactions (to_, token_id, amount).

        """
        # Get a handle to the FA2 token transfer entry point
        c = sp.contract(
            t=sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(MultisigWalletContract.FA2_TX_TYPE))),
            address=fa2,
            entry_point="transfer").open_some()

        # Transfer the FA2 token editions to the new address
        sp.transfer(
            arg=sp.list([sp.record(from_=from_, txs=txs)]),
            amount=sp.mutez(0),
            destination=c)


# Add a compilation target initialized to a single user account
sp.add_compilation_target("multisig", MultisigWalletContract(
    metadata=sp.utils.metadata_of_url("ipfs://QmW9G5GXx6CtPUJFK9nKJNxdedehwqPVcqtPq5Tk6XMGEr"),
    users=sp.set([sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicV9rCx")]),
    minimum_votes=sp.nat(1),
    expiration_time=sp.nat(7)))
