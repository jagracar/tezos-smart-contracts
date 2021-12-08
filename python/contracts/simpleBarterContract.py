import smartpy as sp


class SimpleBarterContract(sp.Contract):
    """This contract implements a simple barter contract where users can trade
    FA2 tokens for other FA2 tokens.

    """

    TOKEN_LIST_TYPE = sp.TList(sp.TRecord(
        # The FA2 token contract address
        fa2=sp.TAddress,
        # The FA2 token id
        id=sp.TNat,
        # The number of editions to trade
        amount=sp.TNat).layout(("fa2", ("id", "amount"))))

    TRADE_TYPE = sp.TRecord(
        # Flag to indicate if the trade has been exectuded
        executed=sp.TBool,
        # Flag to indicate if the trade has been cancelled
        cancelled=sp.TBool,
        # The first user involved in the trade
        user1=sp.TAddress,
        # The second user involved in the trade
        user2=sp.TOption(sp.TAddress),
        # The first user tokens to trade
        tokens1=TOKEN_LIST_TYPE,
        # The second user tokens to trade
        tokens2=TOKEN_LIST_TYPE).layout(
            ("executed", ("cancelled", ("user1", ("user2", ("tokens1", "tokens2"))))))

    def __init__(self, metadata):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            trades=sp.TBigMap(sp.TNat, SimpleBarterContract.TRADE_TYPE),
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            trades=sp.big_map(),
            counter=0)

    def check_no_tez_transfer(self):
        """Checks that no tez were transferred in the operation.

        """
        sp.verify(sp.amount == sp.tez(0),
                  message="The operation does not need tez transfers")

    def check_trade_still_open(self, trade_id):
        """Checks that the trade id corresponds to an existing trade and that
        the trade is still open (not executed and not cancelled).

        """
        # Check that the trade id is present in the trades big map
        sp.verify(self.data.trades.contains(trade_id),
                  message="The provided trade id doesn't exist")

        # Check that the trade was not executed
        sp.verify(~self.data.trades[trade_id].executed,
                  message="The trade was executed")

        # Check that the trade was not cancelled
        sp.verify(~self.data.trades[trade_id].cancelled,
                  message="The trade was cancelled")

    @sp.entry_point
    def propose_trade(self, trade_proposal):
        """Proposes a trade between two users.

        """
        # Define the input parameter data type
        sp.set_type(trade_proposal, sp.TRecord(
            tokens=SimpleBarterContract.TOKEN_LIST_TYPE,
            for_tokens=SimpleBarterContract.TOKEN_LIST_TYPE,
            with_user=sp.TOption(sp.TAddress)).layout(
                ("tokens", ("for_tokens", "with_user"))))

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the trade will involve at least one edition of each token
        sp.for token in trade_proposal.tokens:
            sp.verify(token.amount >= 0,
                      message="At least one token edition needs to be traded")

        sp.for token in trade_proposal.for_tokens:
            sp.verify(token.amount >= 0,
                      message="At least one token edition needs to be traded")

        # Transfer the proposed tokens to the barter account
        self.transfer_tokens(
            from_=sp.sender,
            to_=sp.self_address,
            tokens=trade_proposal.tokens)

        # Update the trades bigmap with the new trade information
        self.data.trades[self.data.counter] = sp.record(
            executed=False,
            cancelled=False,
            user1=sp.sender,
            user2=trade_proposal.with_user,
            tokens1=trade_proposal.tokens,
            tokens2=trade_proposal.for_tokens)

        # Increase the trades counter
        self.data.counter += 1

    @sp.entry_point
    def accept_trade(self, trade_id):
        """Accepts and executes a trade.

        """
        # Define the input parameter data type
        sp.set_type(trade_id, sp.TNat)

        # Check that the trade is still open
        self.check_trade_still_open(trade_id)

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the sender is the trade second user
        trade = self.data.trades[trade_id]

        sp.if trade.user2.is_some():
            sp.verify(sp.sender == trade.user2.open_some(),
                      message="Only user2 can accept the trade")
        sp.else:
            # Set the sender as the trade second user
            trade.user2 = sp.some(sp.sender)

        # Set the trade as executed
        trade.executed = True

        # Transfer the second user tokens to the first user
        self.transfer_tokens(
            from_=sp.sender,
            to_=trade.user1,
            tokens=trade.tokens2)

        # Transfer the first user tokens to the second user
        self.transfer_tokens(
            from_=sp.self_address,
            to_=sp.sender,
            tokens=trade.tokens1)

    @sp.entry_point
    def cancel_trade(self, trade_id):
        """Cancels a proposed trade.

        """
        # Define the input parameter data type
        sp.set_type(trade_id, sp.TNat)

        # Check that the trade is still open
        self.check_trade_still_open(trade_id)

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the sender is the trade first user
        trade = self.data.trades[trade_id]
        sp.verify(sp.sender == trade.user1,
                  message="Only user1 can cancel the trade")

        # Set the trade as cancelled
        trade.cancelled = True

        # Transfer the tokens back to the sender
        self.transfer_tokens(
            from_=sp.self_address,
            to_=sp.sender,
            tokens=trade.tokens1)

    def transfer_tokens(self, from_, to_, tokens):
        """Transfers a list of FA2 tokens between two addresses.

        """
        sp.for token in tokens:
            self.fa2_transfer(
                fa2=token.fa2,
                from_=from_,
                to_=to_,
                token_id=token.id,
                token_amount=token.amount)

    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
        """Transfers a number of editions of a FA2 token between two addresses.

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


# Add a compilation target
sp.add_compilation_target("simpleBarter", SimpleBarterContract(
        metadata=sp.utils.metadata_of_url("ipfs://QmVg6rZq5e4JiFZKGyAFLZxwUC6B3edyJvEqatbA5o5Q5R")))
