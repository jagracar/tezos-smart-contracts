import smartpy as sp


class FA2(sp.Contract):
    """This contract tries to simplify the FA2 contract template example in
    smartpy.io v0.9.0.

    The FA2 template was originally developed by Seb Mondet:
    https://gitlab.com/smondet/fa2-smartpy

    The contract follows the FA2 standard specification:
    https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/tzip-12.md

    """

    LEDGER_KEY_TYPE = sp.TPair(
        # The token owner
        sp.TAddress,
        # The token id
        sp.TNat)

    LEDGER_VALUE_TYPE = sp.TRecord(
        # The number of token editions that the owner has
        balance=sp.TNat)

    TOKEN_METADATA_VALUE_TYPE = sp.TRecord(
        # The token id
        token_id=sp.TNat,
        # The map with the token metadata information
        token_info=sp.TMap(sp.TString, sp.TBytes)).layout(
            ("token_id", "token_info"))

    OPERATOR_KEY_TYPE = sp.TRecord(
        # The token owner
        owner=sp.TAddress,
        # The operator allowed by the owner to transfer the token
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
            # The ledger bigmap where the token owners are listed
            ledger=sp.TBigMap(FA2.LEDGER_KEY_TYPE, FA2.LEDGER_VALUE_TYPE),
            # The tokens total supply
            total_supply=sp.TBigMap(sp.TNat, sp.TNat),
            # The tokens metadata big map
            token_metadata=sp.TBigMap(sp.TNat, FA2.TOKEN_METADATA_VALUE_TYPE),
            # The token operators big map
            operators=sp.TBigMap(FA2.OPERATOR_KEY_TYPE, sp.TUnit),
            # The total number of tokens minted so far
            all_tokens=sp.TNat,
            # Flag to indicate if the contract is paused or not
            paused=sp.TBool))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            ledger=sp.big_map(),
            total_supply=sp.big_map(),
            token_metadata=sp.big_map(),
            operators=sp.big_map(),
            all_tokens=0,
            paused=False)

        # Adds some flags and optimization levels
        self.add_flag("initial-cast")
        self.exception_optimization_level = "default-line"

        # Build the TZIP-016 contract metadata
        # This is helpful to get the off-chain views code in json format
        contract_metadata = {
            "name": "Simplified FA2 template contract",
            "description" : "This contract tries to simplify the FA2 " + 
                "contract template example in smartpy.io v0.9.0",
            "version": "v1.0.0",
            "authors": [
                "Seb Mondet <https://seb.mondet.org>",
                "Javier Gracia Carpio <https://twitter.com/jagracar>"],
            "homepage": "https://github.com/jagracar/tezos-smart-contracts",
            "source": {
                "tools": ["SmartPy 0.9.0"],
                "location": "https://github.com/jagracar/tezos-smart-contracts/blob/main/python/contracts/fa2Contract.py"
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

    def check_is_administrator_or_owner(self, owner):
        """Checks that the address that called the entry point is either the
        contract administrator or the token owner.

        """
        sp.verify((sp.sender == self.data.administrator) | (sp.sender == owner),
                  message="FA2_NOT_ADMIN_OR_OPERATOR")

    def check_is_operator(self, owner, token_id):
        """Checks that the address that called the entry point is allowed to
        transfer the token.

        """
        sp.verify((sp.sender == self.data.administrator) | 
                  (sp.sender == owner) | 
                  (self.data.operators.contains(sp.record(
                      owner=owner, operator=sp.sender, token_id=token_id))),
                  message="FA2_NOT_OPERATOR")

    def check_token_exists(self, token_id):
        """Checks that the given token exists.

        """
        sp.verify(self.data.token_metadata.contains(token_id),
                  message="FA2_TOKEN_UNDEFINED")

    def check_sufficient_balance(self, owner, token_id, amount):
        """Checks that the owner has enough editions of the given token.

        """
        sp.verify(self.data.ledger[(owner, token_id)].balance >= amount,
                  message="FA2_INSUFFICIENT_BALANCE")

    def check_is_not_paused(self):
        """Checks that the contract is not paused.

        """
        sp.verify(~self.data.paused, message="FA2_PAUSED")

    @sp.entry_point
    def mint(self, params):
        """Mints a new token.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            address=sp.TAddress,
            amount=sp.TNat,
            metadata=sp.TMap(sp.TString, sp.TBytes),
            token_id=sp.TNat).layout(
                ("address", ("amount", ("metadata", "token_id")))))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Update the ledger big map
        ledger_key = sp.pair(params.address, params.token_id)

        with sp.if_(self.data.ledger.contains(ledger_key)):
            self.data.ledger[ledger_key].balance += params.amount
        with sp.else_():
            self.data.ledger[ledger_key] = sp.record(balance=params.amount)

        # Update the total supply and token metadata big maps
        with sp.if_(params.token_id < self.data.all_tokens):
            # Increase the token total supply
            self.data.total_supply[params.token_id] += params.amount
        with sp.else_():
            # Check that the token ids are consecutive
            sp.verify(self.data.all_tokens == params.token_id,
                      message="Token-IDs should be consecutive")

            # Add the new big map rows
            self.data.total_supply[params.token_id] = params.amount
            self.data.token_metadata[params.token_id] = sp.record(
                token_id=params.token_id,
                token_info=params.metadata)

            # Increase the all tokens counter
            self.data.all_tokens += 1

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

        # Checks that the contract is not paused
        self.check_is_not_paused()

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
                    self.data.ledger[owner_key].balance = sp.as_nat(
                        self.data.ledger[owner_key].balance - tx.amount)

                    # Add the token amount to the new owner
                    new_owner_key = sp.pair(tx.to_, tx.token_id)

                    with sp.if_(self.data.ledger.contains(new_owner_key)):
                        self.data.ledger[new_owner_key].balance += tx.amount
                    with sp.else_():
                         self.data.ledger[new_owner_key] = sp.record(balance=tx.amount)

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

        # Checks that the contract is not paused
        self.check_is_not_paused()

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
                    balance=self.data.ledger[ledger_key].balance))
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
                    # Check that the sender is the administrator or the token owner
                    self.check_is_administrator_or_owner(operator_key.owner)

                    # Add the new operator to the operators big map
                    self.data.operators[operator_key] = sp.unit
                with arg.match("remove_operator") as operator_key:
                    # Check that the sender is the administrator or the token owner
                    self.check_is_administrator_or_owner(operator_key.owner)

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

    @sp.entry_point
    def set_pause(self, pause):
        """Pauses or unpauses the contract.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Se the new paused state
        self.data.paused = pause

    @sp.offchain_view(pure=True)
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
        sp.result(self.data.ledger[(params.owner, params.token_id)].balance)

    @sp.offchain_view(pure=True)
    def does_token_exist(self, token_id):
        """Checks if the token exists.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return true if the token exists
        sp.result(self.data.token_metadata.contains(token_id))

    @sp.offchain_view(pure=True)
    def count_tokens(self):
        """Returns how many tokens are in this FA2 contract.

        """
        sp.result(self.data.all_tokens)

    @sp.offchain_view(pure=True)
    def all_tokens(self):
        """Returns a list with all the token ids.

        """
        sp.result(sp.range(0, self.data.all_tokens))

    @sp.offchain_view(pure=True)
    def total_supply(self, token_id):
        """Returns the total supply for a given token id.

        """
        # Define the input parameter data type
        sp.set_type(token_id, sp.TNat)

        # Return the token total supply
        sp.result(self.data.total_supply[token_id])

    @sp.offchain_view(pure=True)
    def is_operator(self, params):
        """Checks if a given token operator exists.

        """
        # Define the input parameter data type
        sp.set_type(params, FA2.OPERATOR_KEY_TYPE)

        # Return true if the token operator exists
        sp.result(self.data.operators.contains(params))


sp.add_compilation_target("FA2", FA2(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa")))
