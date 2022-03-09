"""Unit tests for the MarketplaceContract class.

"""

import os
import smartpy as sp

# Import the extendedFa2Contract, minterContract and marketplaceContract modules
extendedFa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/extendedFa2Contract.py")
minterContract = sp.io.import_script_from_url(
    "file:python/contracts/minterContract.py")
marketplaceContract = sp.io.import_script_from_url(
    "file:python/contracts/marketplaceContract.py")


class RecipientContract(sp.Contract):
    """This contract simulates a user that can recive tez transfers.

    It should only be used to test that tez transfers are sent correctly.

    """

    def __init__(self):
        """Initializes the contract.

        """
        self.init()

    @sp.entry_point
    def default(self, unit):
        """Default entrypoint that allows receiving tez transfers in the same
        way as one would do with a normal tz wallet.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Do nothing, just receive tez
        pass


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    collector1 = sp.test_account("collector1")
    collector2 = sp.test_account("collector2")

    # Initialize the artists contracts that will receive the royalties
    artist1 = RecipientContract()
    artist2 = RecipientContract()
    scenario += artist1
    scenario += artist2

    # Initialize the organization contracts that will receive the donations
    org1 = RecipientContract()
    org2 = RecipientContract()
    scenario += org1
    scenario += org2

    # Initialize the extended FA2 contract
    fa2 = extendedFa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += fa2

    # Initialize the minter contract
    minter = minterContract.MinterContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"),
        fa2=fa2.address)
    scenario += minter

    # Initialize the marketplace contract
    marketplace = marketplaceContract.MarketplaceContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        fa2=fa2.address,
        fee=sp.nat(25))
    scenario += marketplace

    # Initialize the fee recipient contract
    fee_recipient = RecipientContract()
    scenario += fee_recipient

    # Set the minter contract as the admin of the FA2 contract
    fa2.transfer_administrator(minter.address).run(sender=admin)
    minter.accept_fa2_administrator().run(sender=admin)

    # Change the marketplace fee recipient
    marketplace.update_fee_recipient(fee_recipient.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "artist1": artist1,
        "artist2": artist2,
        "collector1": collector1,
        "collector2": collector2,
        "org1": org1,
        "org2": org2,
        "fa2": fa2,
        "minter": minter,
        "marketplace": marketplace,
        "fee_recipient": fee_recipient}

    return testEnvironment


@sp.add_test(name="Test swap and collect")
def test_swap_and_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    org1 = testEnvironment["org1"]
    org2 = testEnvironment["org2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    # Mint a token
    minted_editions = 100
    royalties = 100
    minter.mint(
        editions=minted_editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist2.address)

    # Transfer some of the editions to the first artist
    editions = 50
    fa2.transfer([
        sp.record(
            from_=artist2.address,
            txs=[sp.record(to_=artist1.address, token_id=0, amount=editions)])
        ]).run(sender=artist2.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Check that there are no swaps in the marketplace
    scenario.verify(~marketplace.data.swaps.contains(0))
    scenario.verify(~marketplace.has_swap(0))
    scenario.verify(marketplace.data.counter == 0)
    scenario.verify(marketplace.get_swaps_counter() == 0)

    # Check that tez transfers are not allowed when swapping
    swapped_editions = 40
    price = sp.mutez(1000000)
    donations = [sp.record(address=org1.address, donation=100),
                 sp.record(address=org2.address, donation=300)]
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(valid=False, sender=artist1.address, amount=sp.tez(3))

    # Swap the token on the marketplace contract
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(artist1.address, token_id)] == editions - swapped_editions)
    scenario.verify(fa2.data.ledger[(artist2.address, token_id)] == minted_editions - editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, token_id)] == swapped_editions)

    # Check that the swaps big map is correct
    scenario.verify(marketplace.data.swaps.contains(0))
    scenario.verify(marketplace.data.swaps[0].issuer == artist1.address)
    scenario.verify(marketplace.data.swaps[0].token_id == token_id)
    scenario.verify(marketplace.data.swaps[0].editions == swapped_editions)
    scenario.verify(marketplace.data.swaps[0].price == price)
    scenario.verify(sp.len(marketplace.data.swaps[0].donations) == 2)
    scenario.verify(marketplace.data.counter == 1)

    # Check that the on-chain views work
    scenario.verify(marketplace.has_swap(0))
    scenario.verify(marketplace.get_swap(0).issuer == artist1.address)
    scenario.verify(marketplace.get_swap(0).token_id == token_id)
    scenario.verify(marketplace.get_swap(0).editions == swapped_editions)
    scenario.verify(marketplace.get_swap(0).price == price)
    scenario.verify(sp.len(marketplace.get_swap(0).donations) == 2)
    scenario.verify(marketplace.get_swaps_counter() == 1)

    # Check that collecting fails if the collector is the swap issuer
    marketplace.collect(0).run(valid=False, sender=artist1.address, amount=price)

    # Check that collecting fails if the exact tez amount is not provided
    marketplace.collect(0).run(valid=False, sender=collector1, amount=(price - sp.mutez(1)))
    marketplace.collect(0).run(valid=False, sender=collector1, amount=(price + sp.mutez(1)))

    # Collect the token with two different collectors
    marketplace.collect(0).run(sender=collector1, amount=price)
    marketplace.collect(0).run(sender=collector2, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(fee_recipient.balance == sp.mul(2, sp.split_tokens(price, 25, 1000)))
    scenario.verify(org1.balance == sp.mul(2, sp.split_tokens(price, 100, 1000)))
    scenario.verify(org2.balance == sp.mul(2, sp.split_tokens(price, 300, 1000)))
    scenario.verify(artist2.balance == sp.mul(2, sp.split_tokens(price, royalties, 1000)))
    scenario.verify(artist1.balance == sp.mul(2, price - 
                                              sp.split_tokens(price, 25, 1000) - 
                                              sp.split_tokens(price, 100, 1000) - 
                                              sp.split_tokens(price, 300, 1000) - 
                                              sp.split_tokens(price, royalties, 1000)))
    scenario.verify(marketplace.data.swaps[0].editions == swapped_editions - 2)
    scenario.verify(marketplace.get_swap(0).editions == swapped_editions - 2)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(artist1.address, token_id)] == editions - swapped_editions)
    scenario.verify(fa2.data.ledger[(artist2.address, token_id)] == minted_editions - editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, token_id)] == swapped_editions - 2)
    scenario.verify(fa2.data.ledger[(collector1.address, token_id)] == 1)
    scenario.verify(fa2.data.ledger[(collector2.address, token_id)] == 1)

    # Check that only the swapper can cancel the swap
    marketplace.cancel_swap(0).run(valid=False, sender=collector1)
    marketplace.cancel_swap(0).run(valid=False, sender=artist1.address, amount=sp.tez(3))
    marketplace.cancel_swap(0).run(sender=artist1.address)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(artist1.address, token_id)] == editions - 2)
    scenario.verify(fa2.data.ledger[(artist2.address, token_id)] == minted_editions - editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, token_id)] == 0)
    scenario.verify(fa2.data.ledger[(collector1.address, token_id)] == 1)
    scenario.verify(fa2.data.ledger[(collector2.address, token_id)] == 1)

    # Check that the swaps big map has been updated
    scenario.verify(~marketplace.data.swaps.contains(0))
    scenario.verify(~marketplace.has_swap(0))
    scenario.verify(marketplace.get_swaps_counter() == 1)

    # Check that the swap cannot be cancelled twice
    marketplace.cancel_swap(0).run(valid=False, sender=artist1.address)


@sp.add_test(name="Test free collect")
def test_free_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    org1 = testEnvironment["org1"]
    org2 = testEnvironment["org2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    # Mint a token
    editions = 100
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap the token in the marketplace contract for a price of 0 tez
    swapped_editions = 50
    price = sp.mutez(0)
    donations = [sp.record(address=org1.address, donation=100),
                 sp.record(address=org2.address, donation=300)]
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Collect the token
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(fee_recipient.balance == sp.mutez(0))
    scenario.verify(org1.balance == sp.mutez(0))
    scenario.verify(org2.balance == sp.mutez(0))
    scenario.verify(artist1.balance == sp.mutez(0))
    scenario.verify(marketplace.data.swaps[0].editions == swapped_editions - 1)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(artist1.address, token_id)] == editions - swapped_editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, token_id)] == swapped_editions - 1)
    scenario.verify(fa2.data.ledger[(collector1.address, token_id)] == 1)


@sp.add_test(name="Test very cheap collect")
def test_very_cheap_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    org1 = testEnvironment["org1"]
    org2 = testEnvironment["org2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    # Mint a token
    editions = 100
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap the token in the marketplace contract for a very cheap price
    swapped_editions = 50
    price = sp.mutez(2)
    donations = [sp.record(address=org1.address, donation=100),
                 sp.record(address=org2.address, donation=300)]
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Collect the token
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplace.balance == sp.mutez(0))
    scenario.verify(fee_recipient.balance == sp.mutez(0))
    scenario.verify(org1.balance == sp.mutez(0))
    scenario.verify(org2.balance == sp.mutez(0))
    scenario.verify(artist1.balance == price)
    scenario.verify(marketplace.data.swaps[0].editions == swapped_editions - 1)

    # Check that the token ledger information is correct
    scenario.verify(fa2.data.ledger[(artist1.address, token_id)] == editions - swapped_editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, token_id)] == swapped_editions - 1)
    scenario.verify(fa2.data.ledger[(collector1.address, token_id)] == 1)


@sp.add_test(name="Test update fee")
def test_update_fee():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    marketplace = testEnvironment["marketplace"]

    # Check the original fee
    scenario.verify(marketplace.data.fee == 25)
    scenario.verify(marketplace.get_fee() == 25)

    # Check that only the admin can update the fees
    new_fee = 100
    marketplace.update_fee(new_fee).run(valid=False, sender=artist1.address)
    marketplace.update_fee(new_fee).run(valid=False, sender=admin, amount=sp.tez(3))
    marketplace.update_fee(new_fee).run(sender=admin)

    # Check that the fee is updated
    scenario.verify(marketplace.data.fee == new_fee)
    scenario.verify(marketplace.get_fee() == new_fee)

    # Check that if fails if we try to set a fee that its too high
    new_fee = 500
    marketplace.update_fee(new_fee).run(valid=False, sender=admin)


@sp.add_test(name="Test update fee recipient")
def test_update_fee_recipient():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplace = testEnvironment["marketplace"]
    fee_recipient = testEnvironment["fee_recipient"]

    # Check the original fee recipient
    scenario.verify(marketplace.data.fee_recipient == fee_recipient.address)
    scenario.verify(marketplace.get_fee_recipient() == fee_recipient.address)

    # Check that only the admin can update the fee recipient
    new_fee_recipient = artist1.address
    marketplace.update_fee_recipient(new_fee_recipient).run(valid=False, sender=artist1.address)
    marketplace.update_fee_recipient(new_fee_recipient).run(valid=False, sender=admin, amount=sp.tez(3))
    marketplace.update_fee_recipient(new_fee_recipient).run(sender=admin)

    # Check that the fee recipient is updated
    scenario.verify(marketplace.data.fee_recipient == new_fee_recipient)
    scenario.verify(marketplace.get_fee_recipient() == new_fee_recipient)

    # Check that the fee recipient cannot update the fee recipient
    new_fee_recipient = artist2.address
    marketplace.update_fee_recipient(new_fee_recipient).run(valid=False, sender=artist1.address)


@sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_manager():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplace = testEnvironment["marketplace"]

    # Check the original administrator
    scenario.verify(marketplace.data.administrator == admin.address)
    scenario.verify(marketplace.get_administrator() == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = artist1.address
    marketplace.transfer_administrator(new_administrator).run(valid=False, sender=artist1.address)
    marketplace.transfer_administrator(new_administrator).run(valid=False, sender=admin, amount=sp.tez(3))
    marketplace.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(marketplace.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    marketplace.accept_administrator().run(valid=False, sender=admin)
    marketplace.accept_administrator().run(valid=False, sender=artist1.address, amount=sp.tez(3))
    marketplace.accept_administrator().run(sender=artist1.address)

    # Check that the administrator is updated
    scenario.verify(marketplace.data.administrator == new_administrator)
    scenario.verify(marketplace.get_administrator() == new_administrator)
    scenario.verify(~marketplace.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = artist2.address
    marketplace.transfer_administrator(new_administrator).run(valid=False, sender=admin)
    marketplace.transfer_administrator(new_administrator).run(sender=artist1.address)

    # Check that the proposed administrator is updated
    scenario.verify(marketplace.data.proposed_administrator.open_some() == new_administrator)


@sp.add_test(name="Test set pause swaps")
def test_set_pause_swaps():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    # Mint a token
    editions = 100
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap one token in the marketplace contract
    swapped_editions = 10
    price = sp.mutez(1000000)
    donations = []
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Collect the token
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Pause the swaps and make sure only the admin can do it
    marketplace.set_pause_swaps(True).run(valid=False, sender=collector1)
    marketplace.set_pause_swaps(True).run(valid=False, sender=admin, amount=sp.tez(3))
    marketplace.set_pause_swaps(True).run(sender=admin)

    # Check that only the swaps are paused
    scenario.verify(marketplace.data.swaps_paused)
    scenario.verify(~marketplace.data.collects_paused)

    # Check that swapping is not allowed
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(valid=False, sender=artist1.address)

    # Check that collecting is still allowed
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Check that cancel swaps are still allowed
    marketplace.cancel_swap(0).run(sender=artist1.address)

    # Unpause the swaps again
    marketplace.set_pause_swaps(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)
    marketplace.collect(1).run(sender=collector1, amount=price)
    marketplace.cancel_swap(1).run(sender=artist1.address)


@sp.add_test(name="Test set pause collects")
def test_set_pause_collects():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    # Mint a token
    editions = 100
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Swap one token in the marketplace contract
    swapped_editions = 10
    price = sp.mutez(1000000)
    donations = []
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Collect the OBJKT
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Pause the collects and make sure only the admin can do it
    marketplace.set_pause_collects(True).run(valid=False, sender=collector1)
    marketplace.set_pause_collects(True).run(valid=False, sender=admin, amount=sp.tez(3))
    marketplace.set_pause_collects(True).run(sender=admin)

    # Check that only the collects are paused
    scenario.verify(~marketplace.data.swaps_paused)
    scenario.verify(marketplace.data.collects_paused)

    # Check that collecting is not allowed
    marketplace.collect(0).run(valid=False, sender=collector1, amount=price)

    # Check that swapping is still allowed
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Check that cancel swaps are still allowed
    marketplace.cancel_swap(0).run(sender=artist1.address)

    # Unpause the collects again
    marketplace.set_pause_collects(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    marketplace.swap(
        token_id=token_id,
        editions=swapped_editions,
        price=price,
        donations=donations).run(sender=artist1.address)
    marketplace.collect(2).run(sender=collector1, amount=price)
    marketplace.cancel_swap(2).run(sender=artist1.address)


@sp.add_test(name="Test swap failure conditions")
def test_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    org1 = testEnvironment["org1"]
    org2 = testEnvironment["org2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    # Mint a token
    editions = 1
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Trying to swap more editions than are available must fail
    price = sp.mutez(1000000)
    donations = []
    marketplace.swap(
        token_id=token_id,
        editions=editions + 1,
        price=price,
        donations=donations).run(valid=False, sender=artist1.address)

    # Trying to swap a token for which one doesn't have any editions must fail,
    # even for the admin
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=donations).run(valid=False, sender=admin)

    # Cannot swap 0 items
    marketplace.swap(
        token_id=token_id,
        editions=0,
        price=price,
        donations=donations).run(valid=False, sender=artist1.address)

    # Trying to give too many donations must fail
    too_many_donations = [sp.record(address=org1.address, donation=500),
                          sp.record(address=org2.address, donation=501)]
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=too_many_donations).run(valid=False, sender=artist1.address)

    # Successfully swap
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(0))
    scenario.verify(~marketplace.data.swaps.contains(1))
    scenario.verify(marketplace.data.counter == 1)

    # Second swap should now fail because all avaliable editions have beeen swapped
    marketplace.swap(
        token_id=token_id,
        editions=1,
        price=price,
        donations=donations).run(valid=False, sender=artist1.address)

    # Mint a multi edition from a second OBJKT
    editions = 10
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist2.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 1
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist2.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist2.address)

    # Fail to swap second objkt as second artist when too many editions
    price = sp.mutez(12000)
    marketplace.swap(
        token_id=token_id,
        editions=editions + 10,
        price=price,
        donations=donations).run(valid=False, sender=artist2.address)

    # Successfully swap the second objkt
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=donations).run(sender=artist2.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(0))
    scenario.verify(marketplace.data.swaps.contains(1))
    scenario.verify(~marketplace.data.swaps.contains(2))
    scenario.verify(marketplace.data.counter == 2)

    # Check that is not possible to swap the second objkt because all editions
    # were swapped before
    marketplace.swap(
        token_id=token_id,
        editions=1,
        price=price,
        donations=donations).run(valid=False, sender=artist2.address)


@sp.add_test(name="Test cancel swap failure conditions")
def test_cancel_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    # Mint a token
    editions = 1
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Successfully swap
    price = sp.mutez(10000)
    donations = []
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Check that the swap was added
    scenario.verify(marketplace.data.swaps.contains(0))
    scenario.verify(~marketplace.data.swaps.contains(1))
    scenario.verify(marketplace.data.counter == 1)

    # Check that cancelling a nonexistent swap fails
    marketplace.cancel_swap(1535).run(valid=False, sender=artist1.address)

    # Check that cancelling someone elses swap fails
    marketplace.cancel_swap(0).run(valid=False, sender=artist2.address)

    # Check that even the admin cannot cancel the swap
    marketplace.cancel_swap(0).run(valid=False, sender=admin)

    # Check that cancelling own swap works
    marketplace.cancel_swap(0).run(sender=artist1.address)

    # Check that the swap is gone
    scenario.verify(~marketplace.data.swaps.contains(0))
    scenario.verify(~marketplace.data.swaps.contains(1))

    # Check that the swap counter is still incremented
    scenario.verify(marketplace.data.counter == 1)


@sp.add_test(name="Test collect swap failure conditions")
def test_collect_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]
    marketplace = testEnvironment["marketplace"]

    # Mint a token
    editions = 1
    royalties = 100
    minter.mint(
        editions=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
        data={},
        royalties=royalties).run(sender=artist1.address)

    # Add the marketplace contract as an operator to be able to swap it
    token_id = 0
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=artist1.address,
        operator=marketplace.address,
        token_id=token_id))]).run(sender=artist1.address)

    # Successfully swap
    price = sp.mutez(100)
    donations = []
    marketplace.swap(
        token_id=token_id,
        editions=editions,
        price=price,
        donations=donations).run(sender=artist1.address)

    # Check that trying to collect a nonexistent swap fails
    marketplace.collect(100).run(valid=False, sender=collector1, amount=price)

    # Check that trying to collect own swap fails
    marketplace.collect(0).run(valid=False, sender=artist1.address, amount=price)

    # Check that providing the wrong tez amount fails
    marketplace.collect(0).run(valid=False, sender=collector1, amount=price + sp.mutez(1))

    # Collect the token
    marketplace.collect(0).run(sender=collector1, amount=price)

    # Check that the swap entry still exists
    scenario.verify(marketplace.data.swaps.contains(0))

    # Check that there are no edition left for that swap
    scenario.verify(marketplace.data.swaps[0].editions == 0)
    scenario.verify(marketplace.data.counter == 1)

    # Check that trying to collect the swap fails
    marketplace.collect(0).run(valid=False, sender=collector1, amount=price)
