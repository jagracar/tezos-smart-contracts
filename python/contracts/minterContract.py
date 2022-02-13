import smartpy as sp


class MinterContract(sp.Contract):
    """A basic minter contract for the extended FA2 token contract.

    """

    USER_TYPE = sp.TRecord(
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
            fa2=sp.TAddress))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            fa2=fa2)

    @sp.entry_point
    def single_creator_mint(self, params):
        """Mints a new FA2 token with only one creator.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            editions=sp.TNat,
            metadata=sp.TBytes,
            royalties=sp.TNat,
            donations=sp.TList(MinterContract.USER_TYPE)).layout(
                ("editions", ("metadata", ("royalties", "donations")))))

        # Check that the number of editions is not zero
        sp.verify(params.editions != 0, message="MINT_ZERO_EDITIONS")

        # Check that the creator royalties are less than 25%
        sp.verify(params.royalties <= 250,
                  message="MINT_WRONG_CREATOR_ROYALTIES")

        # Check that there are no more than 5 donation entries
        sp.verify(sp.len(params.donations) <= 5,
                  message="MINT_TOO_MANY_DONATIONS")

        # Check that the donations royalties are less than 75%
        total_royalties = sp.local("total_royalties", sp.nat(0))

        with sp.for_("donation", params.donations) as donation:
            total_royalties.value += donation.royalties

        sp.verify(total_royalties.value <= 750,
                  message="MINT_WRONG_DONATION_ROYALTIES")

        # Get a handle on the FA2 contract mint entry point
        fa2_mint_handle = sp.contract(
            t=sp.TRecord(
                amount=sp.TNat,
                metadata=sp.TMap(sp.TString, sp.TBytes),
                minter=MinterContract.USER_TYPE,
                creators=sp.TList(MinterContract.USER_TYPE),
                donations=sp.TList(MinterContract.USER_TYPE)).layout(
                    ("amount", ("metadata", ("minter", ("creators", "donations"))))),
            address=self.data.fa2,
            entry_point="mint").open_some()

        # Mint the token
        sp.transfer(
            arg=sp.record(
                amount=params.editions,
                metadata={"": params.metadata},
                minter=sp.record(address=sp.sender, royalties=0),
                creators=[sp.record(address=sp.sender, royalties=0)],
                donations=params.donations),
            amount=sp.mutez(0),
            destination=fa2_mint_handle)

sp.add_compilation_target("Minter", MinterContract(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("KT1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr")))
