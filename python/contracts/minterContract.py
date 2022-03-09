import smartpy as sp


class MinterContract(sp.Contract):
    """A basic minter contract for the extended FA2 token contract.

    """

    USER_ROYALTIES_TYPE = sp.TRecord(
        # The user address
        address=sp.TAddress,
        # The user royalties in per mille (100 is 10%)
        royalties=sp.TNat).layout(
            ("address", "royalties"))

    def __init__(self, administrator, metadata, fa2):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract administrador
            administrator=sp.TAddress,
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The FA2 token contract address
            fa2=sp.TAddress,
            # The proposed new administrator address
            proposed_administrator=sp.TOption(sp.TAddress),
            # Flag to indicate if the contract is paused or not
            paused=sp.TBool))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            fa2=fa2,
            proposed_administrator=sp.none,
            paused=False)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator,
                  message="MINTER_NOT_ADMIN")

    @sp.entry_point
    def mint(self, params):
        """Mints a new FA2 token. The minter and the creator are assumed to be
        the same person.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            editions=sp.TNat,
            metadata=sp.TMap(sp.TString, sp.TBytes),
            data=sp.TMap(sp.TString, sp.TBytes),
            royalties=sp.TNat).layout(
                ("editions", ("metadata", ("data", "royalties")))))

        # Check that the contract is not paused
        sp.verify(~self.data.paused, message="MINT_PAUSED")

        # Check that the number of editions is not zero
        sp.verify(params.editions != 0, message="MINT_ZERO_EDITIONS")

        # Check that the creator royalties are less than 25%
        sp.verify(params.royalties <= 250, message="MINT_INVALID_ROYALTIES")

        # Get a handle on the FA2 contract mint entry point
        fa2_mint_handle = sp.contract(
            t=sp.TRecord(
                amount=sp.TNat,
                metadata=sp.TMap(sp.TString, sp.TBytes),
                data=sp.TMap(sp.TString, sp.TBytes),
                royalties=sp.TRecord(
                    minter=MinterContract.USER_ROYALTIES_TYPE,
                    creator=MinterContract.USER_ROYALTIES_TYPE).layout(
                        ("minter", "creator"))).layout(
                            ("amount", ("metadata", ("data", "royalties")))),
            address=self.data.fa2,
            entry_point="mint").open_some()

        # Mint the token
        sp.transfer(
            arg=sp.record(
                amount=params.editions,
                metadata=params.metadata,
                data=params.data,
                royalties=sp.record(
                    minter=sp.record(address=sp.sender, royalties=0),
                    creator=sp.record(address=sp.sender, royalties=params.royalties))),
            amount=sp.mutez(0),
            destination=fa2_mint_handle)

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsabilities.

        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="MINTER_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="MINTER_NOT_PROPOSED_ADMIN")

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def transfer_fa2_administrator(self, proposed_fa2_administrator):
        """Proposes to transfer the FA2 token contract administator to another
        minter contract.

        """
        # Define the input parameter data type
        sp.set_type(proposed_fa2_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Get a handle on the FA2 contract transfer_administator entry point
        fa2_transfer_administrator_handle = sp.contract(
            t=sp.TAddress,
            address=self.data.fa2,
            entry_point="transfer_administrator").open_some()

        # Propose to transfer the FA2 token contract administrator
        sp.transfer(
            arg=proposed_fa2_administrator,
            amount=sp.mutez(0),
            destination=fa2_transfer_administrator_handle)

    @sp.entry_point
    def accept_fa2_administrator(self):
        """Accepts the FA2 contract administrator responsabilities.

        """
        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Get a handle on the FA2 contract accept_administator entry point
        fa2_accept_administrator_handle = sp.contract(
            t=sp.TUnit,
            address=self.data.fa2,
            entry_point="accept_administrator").open_some()

        # Accept the FA2 token contract administrator responsabilities
        sp.transfer(
            arg=sp.unit,
            amount=sp.mutez(0),
            destination=fa2_accept_administrator_handle)

    @sp.entry_point
    def set_pause(self, pause):
        """Pause or not minting with the contract.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Pause or unpause the mints
        self.data.paused = pause

    @sp.onchain_view(pure=True)
    def is_paused(self):
        """Checks if the contract is paused.

        """
        # Return true if the contract is paused
        sp.result(self.data.paused)


sp.add_compilation_target("Minter", MinterContract(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("KT1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr")))
