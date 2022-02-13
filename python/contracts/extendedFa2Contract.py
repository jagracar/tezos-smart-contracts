import smartpy as sp


class FA2(sp.Contract):
    """This contract tries to simplify and exented the FA2 contract template
    example in smartpy.io v0.9.0.

    The FA2 template was originally developed by Seb Mondet:
    https://gitlab.com/smondet/fa2-smartpy

    The contract follows the FA2 standard specification:
    https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/tzip-12.md

    """

    LEDGER_KEY_TYPE = sp.TPair(
        # The owner of the token editions
        sp.TAddress,
        # The token id
        sp.TNat)

    TOKEN_METADATA_VALUE_TYPE = sp.TRecord(
        # The token id
        token_id=sp.TNat,
        # The map with the token metadata information
        token_info=sp.TMap(sp.TString, sp.TBytes)).layout(
            ("token_id", "token_info"))

    USER_TYPE = sp.TRecord(
        # The user address
        address=sp.TAddress,
        # The user royalties in per mille (100 is 10%)
        royalties=sp.TNat).layout(
            ("address", "royalties"))

    MINT_PARAMETERS_VALUE_TYPE = sp.TRecord(
        # The token original minter
        minter=USER_TYPE,
        # The token creators
        creators=sp.TList(USER_TYPE),
        # The token donations
        donations=sp.TList(USER_TYPE)).layout(
            ("minter", ("creators", "donations")))

    OPERATOR_KEY_TYPE = sp.TRecord(
        # The owner of the token editions
        owner=sp.TAddress,
        # The operator allowed by the owner to transfer the token editions
        operator=sp.TAddress,
        # The token id
        token_id=sp.TNat).layout(
            ("owner", ("operator", "token_id")))

    def __init__(self, administrator, metadata):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract administrador
            administrator=sp.TAddress,
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The ledger bigmap where the tokens owners are listed
            ledger=sp.TBigMap(FA2.LEDGER_KEY_TYPE, sp.TNat),
            # The tokens total supply
            total_supply=sp.TBigMap(sp.TNat, sp.TNat),
            # The tokens metadata big map
            token_metadata=sp.TBigMap(sp.TNat, FA2.TOKEN_METADATA_VALUE_TYPE),
            # The token mint parameters (minter, creators, royalties)
            mint_parameters=sp.TBigMap(sp.TNat, FA2.MINT_PARAMETERS_VALUE_TYPE),
            # The tokens operators big map
            operators=sp.TBigMap(FA2.OPERATOR_KEY_TYPE, sp.TUnit),
            # A counter that tracks the total number of tokens minted so far
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            ledger=sp.big_map(),
            total_supply=sp.big_map(),
            token_metadata=sp.big_map(),
            mint_parameters=sp.big_map(),
            operators=sp.big_map(),
            counter=0)

        # Adds some flags and optimization levels
        self.add_flag("initial-cast")
        self.exception_optimization_level = "default-line"

        # Build the TZIP-016 contract metadata
        # This is helpful to get the off-chain views code in json format
        contract_metadata = {
            "name": "Extended FA2 template contract",
            "description" : "This contract tries to simplify and extend the "
                "FA2 contract template example in smartpy.io v0.9.0",
            "version": "v1.0.0",
            "authors": ["Javier Gracia Carpio <https://twitter.com/jagracar>"],
            "homepage": "https://github.com/jagracar/tezos-smart-contracts",
            "source": {
                "tools": ["SmartPy 0.9.0"],
                "location": "https://github.com/jagracar/tezos-smart-contracts/blob/main/python/contracts/extendedFa2Contract.py"
            },
            "interfaces": ["TZIP-012", "TZIP-016"],
            "views": [
                self.get_balance,
                self.does_token_exist,
                self.count_tokens,
                self.all_tokens,
                self.total_supply,
                self.is_operator],
            "permissions": {
                "operator": "owner-or-operator-transfer",
                "receiver": "owner-no-hook",
                "sender": "owner-no-hook"
            }
        }

        self.init_metadata("contract_metadata", contract_metadata)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator, message="FA2_NOT_ADMIN")

    def check_is_owner(self, owner):
        """Checks that the address that called the entry point is the owner of
        the token editions.

        """
        sp.verify(sp.sender == owner, message="FA2_SENDER_IS_NOT_OWNER")

    def check_is_operator(self, owner, token_id):
        """Checks that the address that called the entry point is allowed to
        transfer the token.

        """
        sp.verify((sp.sender == owner) | 
                  (self.data.operators.contains(sp.record(
                      owner=owner, operator=sp.sender, token_id=token_id))),
                  message="FA2_NOT_OPERATOR")

    def check_token_exists(self, token_id):
        """Checks that the given token exists.

        """
        sp.verify(token_id < self.data.counter, message="FA2_TOKEN_UNDEFINED")

    def check_sufficient_balance(self, owner, token_id, amount):
        """Checks that the owner has enough editions of the given token.

        """
        sp.verify(self.data.ledger[(owner, token_id)] >= amount,
                  message="FA2_INSUFFICIENT_BALANCE")

    @sp.entry_point
    def mint(self, params):
        """Mints a new token.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            amount=sp.TNat,
            metadata=sp.TMap(sp.TString, sp.TBytes),
            minter=FA2.USER_TYPE,
            creators=sp.TList(FA2.USER_TYPE),
            donations=sp.TList(FA2.USER_TYPE)).layout(
                ("amount", ("metadata", ("minter", ("creators", "donations"))))))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that the number of editions is not zero
        sp.verify(params.amount != 0, message="FA2_ZERO_EDITIONS")

        # Check that there is at least one creator
        sp.verify(sp.len(params.creators) > 0, message="FA2_NO_CREATORS")

        # Update the big maps
        token_id = self.data.counter
        self.data.ledger[(params.minter.address, token_id)] = params.amount
        self.data.total_supply[token_id] = params.amount
        self.data.token_metadata[token_id] = sp.record(
            token_id=token_id,
            token_info=params.metadata)
        self.data.mint_parameters[token_id] = sp.record(
            minter=params.minter,
            creators=params.creators,
            donations=params.donations)

        # Increase the tokens counter
        self.data.counter += 1

    @sp.entry_point
    def transfer(self, params):
        """Executes a list of token transfers.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TRecord(
            from_=sp.TAddress,
            txs=sp.TList(sp.TRecord(
                to_=sp.TAddress,
                token_id=sp.TNat,
                amount=sp.TNat).layout(("to_", ("token_id", "amount"))))).layout(
                        ("from_", "txs"))))

        # Loop over the list of transfers
        with sp.for_("transfer", params) as transfer:
            with sp.for_("tx", transfer.txs) as tx:
                # Check that the sender is one of the token operators
                self.check_is_operator(transfer.from_, tx.token_id)

                # Check that the token exists
                self.check_token_exists(tx.token_id)

                # Only do something if the token amount is larger than zero
                with sp.if_(tx.amount > 0):
                    # Check that the owner has enough editions of the token
                    self.check_sufficient_balance(transfer.from_, tx.token_id, tx.amount)

                    # Remove the token amount from the owner
                    owner_key = sp.pair(transfer.from_, tx.token_id)
                    self.data.ledger[owner_key] = sp.as_nat(
                        self.data.ledger[owner_key] - tx.amount)

                    # Add the token amount to the new owner
                    new_owner_key = sp.pair(tx.to_, tx.token_id)

                    with sp.if_(self.data.ledger.contains(new_owner_key)):
                        self.data.ledger[new_owner_key] += tx.amount
                    with sp.else_():
                         self.data.ledger[new_owner_key] = tx.amount

    @sp.entry_point
    def balance_of(self, params):
        """Requests information about a list of token balances.

        """
        # Define the input parameter data type
        request_type = sp.TRecord(
            owner=sp.TAddress,
            token_id=sp.TNat).layout(("owner", "token_id"))
        sp.set_type(params, sp.TRecord(
            requests=sp.TList(request_type),
            callback=sp.TContract(sp.TList(sp.TRecord(
                request=request_type,
                balance=sp.TNat).layout(("request", "balance"))))).layout(
                    ("requests", "callback")))

        def process_request(request):
            # Check that the token exists
            self.check_token_exists(request.token_id)

            # Check if the owner has the token or had it in the past
            ledger_key = sp.pair(request.owner, request.token_id)

            with sp.if_(self.data.ledger.contains(ledger_key)):
                sp.result(sp.record(
                    request=sp.record(
                        owner=request.owner,
                        token_id=request.token_id),
                    balance=self.data.ledger[ledger_key]))
            with sp.else_():
                sp.result(sp.record(
                    request=sp.record(
                        owner=request.owner,
                        token_id=request.token_id),
                    balance=0))

        responses = sp.local("responses", params.requests.map(process_request))
        sp.transfer(responses.value, sp.mutez(0), params.callback)

    @sp.entry_point
    def update_operators(self, params):
        """Updates a list of operators.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TVariant(
            add_operator=FA2.OPERATOR_KEY_TYPE,
            remove_operator=FA2.OPERATOR_KEY_TYPE)))

        # Loop over the list of update operators
        with sp.for_("update_operator", params) as update_operator:
            with update_operator.match_cases() as arg:
                with arg.match("add_operator") as operator_key:
                    # Check that the sender is the token owner
                    self.check_is_owner(operator_key.owner)

                    # Add the new operator to the operators big map
                    self.data.operators[operator_key] = sp.unit
                with arg.match("remove_operator") as operator_key:
                    # Check that the sender is the token owner
                    self.check_is_owner(operator_key.owner)

                    # Remove the operator from the operators big map
                    del self.data.operators[operator_key]

    @sp.entry_point
    def set_administrator(self, administrator):
        """Sets a new contract administrator.

        """
        # Define the input parameter data type
        sp.set_type(administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Set the new administrator
        self.data.administrator = administrator

    @sp.entry_point
    def set_metadata(self, params):
        """Updates the contract metadata.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            k=sp.TString,
            v=sp.TBytes).layout(("k", "v")))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Update the contract metadata
        self.data.metadata[params.k] = params.v

    @sp.onchain_view(pure=True)
    def get_balance(self, params):
        """Returns the owner token balance.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            owner=sp.TAddress,
            token_id=sp.TNat).layout(("owner", "token_id")))

        # Check that the token exists
        self.check_token_exists(params.token_id)

        # Return the owner token balance
        sp.result(self.data.ledger[(params.owner, params.token_id)])

    @sp.onchain_view(pure=True)
    def does_token_exist(self, token_id):
        """Checks if the token exists.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return true if the token exists
        sp.result(token_id < self.data.counter)

    @sp.onchain_view(pure=True)
    def count_tokens(self):
        """Returns how many tokens are in this FA2 contract.

        """
        sp.result(self.data.counter)

    @sp.onchain_view(pure=True)
    def all_tokens(self):
        """Returns a list with all the token ids.

        """
        sp.result(sp.range(0, self.data.counter))

    @sp.onchain_view(pure=True)
    def total_supply(self, token_id):
        """Returns the total supply for a given token id.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return the token total supply
        sp.result(self.data.total_supply[token_id])

    @sp.onchain_view(pure=True)
    def is_operator(self, params):
        """Checks if a given token operator exists.

        """
        # Define the input parameter data type
        sp.set_type(params, FA2.OPERATOR_KEY_TYPE)

        # Return true if the token operator exists
        sp.result(self.data.operators.contains(params))

    @sp.onchain_view(pure=True)
    def get_mint_parameters(self, token_id):
        """Returns the token mint parameters.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return the token mint parameters
        sp.result(self.data.mint_parameters[token_id])


sp.add_compilation_target("ExtendedFA2", FA2(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa")))
