
import smartpy as sp


class MarketplaceContract(sp.Contract):
    """A basic marketplace contract for the extended FA2 token contract.

    """

    USER_ROYALTIES_TYPE = sp.TRecord(
        # The user address
        address=sp.TAddress,
        # The user royalties in per mille (100 is 10%)
        royalties=sp.TNat).layout(
            ("address", "royalties"))

    ORG_DONATION_TYPE = sp.TRecord(
        # The organization address to donate to
        address=sp.TAddress,
        # The donation in per mille (100 is 10%)
        donation=sp.TNat).layout(
            ("address", "donation"))

    SWAP_TYPE = sp.TRecord(
        # The user that created the swap
        issuer=sp.TAddress,
        # The token id
        token_id=sp.TNat,
        # The number of swapped editions
        editions=sp.TNat,
        # The edition price in mutez
        price=sp.TMutez,
        # The list of donations to different organizations
        donations=sp.TList(ORG_DONATION_TYPE)).layout(
            ("issuer", ("token_id", ("editions", ("price", "donations")))))

    def __init__(self, administrator, metadata, fa2, fee):
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
            # The marketplace fee taken for each collect operation in per mille
            fee=sp.TNat,
            # The address that will receive the marketplace fees
            fee_recipient=sp.TAddress,
            # The big map with the swaps information
            swaps=sp.TBigMap(sp.TNat, MarketplaceContract.SWAP_TYPE),
            # The swaps counter
            counter=sp.TNat,
            # The proposed new administrator address
            proposed_administrator=sp.TOption(sp.TAddress),
            # A flag that indicates if the marketplace swaps are paused
            swaps_paused=sp.TBool,
            # A flag that indicates if the marketplace collects are paused
            collects_paused=sp.TBool))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            fa2=fa2,
            fee=fee,
            fee_recipient=administrator,
            swaps=sp.big_map(),
            counter=0,
            proposed_administrator=sp.none,
            swaps_paused=False,
            collects_paused=False)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator, message="MP_NOT_ADMIN")

    def check_no_tez_transfer(self):
        """Checks that no tez were transferred in the operation.

        """
        sp.verify(sp.amount == sp.tez(0), message="MP_TEZ_TRANSFER")

    @sp.entry_point
    def swap(self, params):
        """Swaps several editions of a token for a fixed price.

        Note that for this operation to work, the marketplace contract should
        be added before as an operator of the token by the swap issuer. 
        It's recommended to remove the marketplace operator rights after
        calling this entry point.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            token_id=sp.TNat,
            editions=sp.TNat,
            price=sp.TMutez,
            donations=sp.TList(MarketplaceContract.ORG_DONATION_TYPE)).layout(
                ("token_id", ("editions", ("price", "donations")))))

        # Check that swaps are not paused
        sp.verify(~self.data.swaps_paused, message="MP_SWAPS_PAUSED")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that at least one edition will be swapped
        sp.verify(params.editions > 0, message="MP_NO_SWAPPED_EDITIONS")

        # Check that the number of donations is not too large
        donations = sp.local("donations", params.donations)
        sp.verify(sp.len(donations.value) <= 5, message="MP_TOO_MANY_DONATIONS")

        # Check that royalties + donations + fee does not exceed 100%
        royalties = sp.local("royalties",
                             self.get_token_royalties(params.token_id))
        total = sp.local("total",
                         self.data.fee + 
                         royalties.value.minter.royalties + 
                         royalties.value.creator.royalties)

        with sp.for_("org_donation", donations.value) as org_donation:
            total.value += org_donation.donation

        sp.verify(total.value <= 1000, message="MP_TOO_HIGH_DONATIONS")

        # Transfer all the editions to the marketplace account
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.sender,
            to_=sp.self_address,
            token_id=params.token_id,
            token_amount=params.editions)

        # Update the swaps bigmap with the new swap information
        self.data.swaps[self.data.counter] = sp.record(
            issuer=sp.sender,
            token_id=params.token_id,
            editions=params.editions,
            price=params.price,
            donations=donations.value)

        # Increase the swaps counter
        self.data.counter += 1

    @sp.entry_point
    def collect(self, swap_id):
        """Collects one edition of a token that has already been swapped.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that collects are not paused
        sp.verify(~self.data.collects_paused, message="MP_COLLECTS_PAUSED")

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id), message="MP_WRONG_SWAP_ID")

        # Check that the collector is not the creator of the swap
        swap = sp.local("swap", self.data.swaps[swap_id])
        sp.verify(sp.sender != swap.value.issuer, message="MP_IS_SWAP_ISSUER")

        # Check that there is at least one edition available to collect
        sp.verify(swap.value.editions > 0, message="MP_SWAP_COLLECTED")

        # Check that the provided mutez amount is exactly the edition price
        sp.verify(sp.amount == swap.value.price, message="MP_WRONG_TEZ_AMOUNT")

        # Handle tez tranfers if the edition price is not zero
        with sp.if_(sp.amount != sp.mutez(0)):
            # Get the royalties information from the FA2 token contract
            royalties = sp.local(
                "royalties", self.get_token_royalties(swap.value.token_id))

            # Send the royalties to the token minter
            minter_royalties_amount = sp.local(
                "minter_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.minter.royalties, 1000))

            with sp.if_(minter_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.minter.address,
                        minter_royalties_amount.value)

            # Send the royalties to the token creator
            creator_royalties_amount = sp.local(
                "creator_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.creator.royalties, 1000))

            with sp.if_(creator_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.creator.address,
                        creator_royalties_amount.value)

            # Send the management fees
            fee_amount = sp.local(
                "fee_amount", sp.split_tokens(sp.amount, self.data.fee, 1000))

            with sp.if_(fee_amount.value > sp.mutez(0)):
                sp.send(self.data.fee_recipient, fee_amount.value)

            # Send the donations
            donation_amount = sp.local("donation_amount", sp.mutez(0))
            total_donations_amount = sp.local(
                "total_donations_amount", sp.mutez(0))

            with sp.for_("org_donation", swap.value.donations) as org_donation:
                donation_amount.value = sp.split_tokens(
                    sp.amount, org_donation.donation, 1000)

                with sp.if_(donation_amount.value > sp.mutez(0)):
                    sp.send(org_donation.address, donation_amount.value)
                    total_donations_amount.value += donation_amount.value

            # Send what is left to the swap issuer
            sp.send(swap.value.issuer,
                    sp.amount - 
                    minter_royalties_amount.value - 
                    creator_royalties_amount.value - 
                    fee_amount.value - 
                    total_donations_amount.value)

        # Transfer the token edition to the collector
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=swap.value.token_id,
            token_amount=1)

        # Update the number of editions available in the swaps big map
        self.data.swaps[swap_id].editions = sp.as_nat(swap.value.editions - 1)

    @sp.entry_point
    def cancel_swap(self, swap_id):
        """Cancels an existing swap.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id), message="MP_WRONG_SWAP_ID")

        # Check that the swap issuer is cancelling the swap
        swap = sp.local("swap", self.data.swaps[swap_id])
        sp.verify(sp.sender == swap.value.issuer, message="MP_NOT_SWAP_ISSUER")

        # Check that there is at least one swapped edition
        sp.verify(swap.value.editions > 0, message="MP_SWAP_COLLECTED")

        # Transfer the remaining token editions back to the owner
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=swap.value.token_id,
            token_amount=swap.value.editions)

        # Delete the swap entry in the the swaps big map
        del self.data.swaps[swap_id]

    @sp.entry_point
    def update_fee(self, new_fee):
        """Updates the marketplace management fees.

        """
        # Define the input parameter data type
        sp.set_type(new_fee, sp.TNat)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= 250, message="MP_WRONG_FEES")

        # Set the new management fee
        self.data.fee = new_fee

    @sp.entry_point
    def update_fee_recipient(self, new_fee_recipient):
        """Updates the marketplace management fee recipient address.

        """
        # Define the input parameter data type
        sp.set_type(new_fee_recipient, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new management fee recipient address
        self.data.fee_recipient = new_fee_recipient

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsabilities.

        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="MP_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="MP_NOT_PROPOSED_ADMIN")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def set_pause_swaps(self, pause):
        """Pause or not the swaps.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the swaps
        self.data.swaps_paused = pause

    @sp.entry_point
    def set_pause_collects(self, pause):
        """Pause or not the collects.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.collects_paused = pause

    @sp.onchain_view()
    def get_administrator(self):
        """Returns the marketplace administrator address.

        """
        sp.result(self.data.administrator)

    @sp.onchain_view()
    def has_swap(self, swap_id):
        """Check if a given swap id is present in the swaps big map.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Return True if the swap id is present in the swaps big map
        sp.result(self.data.swaps.contains(swap_id))

    @sp.onchain_view()
    def get_swap(self, swap_id):
        """Returns the complete information from a given swap id.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id), message="MP_WRONG_SWAP_ID")

        # Return the swap information
        sp.result(self.data.swaps[swap_id])

    @sp.onchain_view()
    def get_swaps_counter(self):
        """Returns the swaps counter.

        """
        sp.result(self.data.counter)

    @sp.onchain_view()
    def get_fee(self):
        """Returns the marketplace fee.

        """
        sp.result(self.data.fee)

    @sp.onchain_view()
    def get_fee_recipient(self):
        """Returns the marketplace fee recipient address.

        """
        sp.result(self.data.fee_recipient)

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

    def get_token_royalties(self, token_id):
        """Gets the token royalties information calling the FA2 contract
        on-chain view.

        """
        return sp.view(
            name="token_royalties",
            address=self.data.fa2,
            param=token_id,
            t=sp.TRecord(
                minter=MarketplaceContract.USER_ROYALTIES_TYPE,
                creator=MarketplaceContract.USER_ROYALTIES_TYPE).layout(
                        ("minter", "creator"))
            ).open_some()


sp.add_compilation_target("marketplace", MarketplaceContract(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("KT1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    fee=sp.nat(25)))
