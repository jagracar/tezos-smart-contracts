"""Unit tests for the MinterContract class.

"""

import smartpy as sp

# Import the extendedFa2Contract and minterContract modules
extendedFa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/extendedFa2Contract.py")
minterContract = sp.io.import_script_from_url(
    "file:python/contracts/minterContract.py")


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")

    # Initialize the extended FA2
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

    # Set the minter contract as the admin of the FA2 contract
    fa2.transfer_administrator(minter.address).run(sender=admin)
    minter.accept_fa2_administrator().run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "fa2": fa2,
        "minter": minter}

    return testEnvironment


@sp.add_test(name="Test mint")
def test_mint():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]

    # Check that a normal user can mint
    editions = 5
    metadata = {"": sp.utils.bytes_of_string("ipfs://aaa")}
    data = {}
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.supply[0] == editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata[""])
    scenario.verify(sp.len(fa2.data.token_data[0]) == 0)
    scenario.verify(fa2.data.token_royalties[0].minter.address == user1.address)
    scenario.verify(fa2.data.token_royalties[0].minter.royalties == 0)
    scenario.verify(fa2.data.token_royalties[0].creator.address == user1.address)
    scenario.verify(fa2.data.token_royalties[0].creator.royalties == royalties)

    # Check that trying to mint a token with zero editions fails
    minter.mint(
        editions=0,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Check that trying to set very hight royalties fails
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=300).run(valid=False, sender=user1)

    # Mint another token
    new_editions = 10
    new_metadata = {"": sp.utils.bytes_of_string("ipfs://bbb")}
    new_data = {"code": sp.utils.bytes_of_string("print('hello world')")}
    new_royalties = 150
    minter.mint(
        editions=new_editions,
        metadata=new_metadata,
        data=new_data,
        royalties=new_royalties).run(sender=user2)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == new_editions)
    scenario.verify(fa2.data.supply[0] == editions)
    scenario.verify(fa2.data.supply[1] == new_editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata[""])
    scenario.verify(fa2.data.token_metadata[1].token_id == 1)
    scenario.verify(fa2.data.token_metadata[1].token_info[""] == new_metadata[""])
    scenario.verify(sp.len(fa2.data.token_data[0]) == 0)
    scenario.verify(fa2.data.token_data[1]["code"] == new_data["code"])
    scenario.verify(fa2.token_royalties(0).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(0).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(1).minter.address == user2.address)
    scenario.verify(fa2.token_royalties(1).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(0).creator.address == user1.address)
    scenario.verify(fa2.token_royalties(0).creator.royalties == royalties)
    scenario.verify(fa2.token_royalties(1).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(1).creator.royalties == new_royalties)


@sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    minter = testEnvironment["minter"]

    # Check the original administrator
    scenario.verify(minter.data.administrator == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = user1.address
    minter.transfer_administrator(new_administrator).run(valid=False, sender=user1)
    minter.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(minter.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    minter.accept_administrator().run(valid=False, sender=admin)
    minter.accept_administrator().run(sender=user1)

    # Check that the administrator is updated
    scenario.verify(minter.data.administrator == new_administrator)
    scenario.verify(~minter.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = user2.address
    minter.transfer_administrator(new_administrator).run(valid=False, sender=admin)
    minter.transfer_administrator(new_administrator).run(sender=user1)

    # Check that the proposed administrator is updated
    scenario.verify(minter.data.proposed_administrator.open_some() == new_administrator)


@sp.add_test(name="Test transfer and accept FA2 administrator")
def test_transfer_and_accept_fa2_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]

    # Initialize a new minter contract and add it to the test scenario
    new_minter = minterContract.MinterContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        fa2=fa2.address)
    scenario += new_minter

    # Check the original FA2 token administrator
    scenario.verify(fa2.data.administrator == minter.address)

    # Propose the new FA2 token contract administrator
    minter.transfer_fa2_administrator(new_minter.address).run(valid=False, sender=user1)
    minter.transfer_fa2_administrator(new_minter.address).run(sender=admin)

    # Accept the new FA2 token contract administrator responsabilities
    new_minter.accept_fa2_administrator().run(valid=False, sender=user1)
    new_minter.accept_fa2_administrator().run(sender=admin)

    # Check that the administrator has been updated
    scenario.verify(fa2.data.administrator == new_minter.address)

    # Check that minting with the old minter fails
    editions = 5
    metadata = {"": sp.utils.bytes_of_string("ipfs://aaa")}
    data = {}
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Check that it's possible to mint with the new minter
    new_minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)


@sp.add_test(name="Test set pause")
def test_set_pause():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    minter = testEnvironment["minter"]

    # Pause the contract
    minter.set_pause(True).run(valid=False, sender=user1)
    minter.set_pause(True).run(sender=admin)

    # Check that the contract is paused
    scenario.verify(minter.data.paused)
    scenario.verify(minter.is_paused())

    # Check that minting fails
    editions = 5
    metadata = {"": sp.utils.bytes_of_string("ipfs://aaa")}
    data = {}
    royalties = 100
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Unpause the contract
    minter.set_pause(False).run(valid=False, sender=user1)
    minter.set_pause(False).run(sender=admin)

    # Check that the contract is not paused
    scenario.verify(~minter.data.paused)
    scenario.verify(~minter.is_paused())

    # Check that minting is possible again
    minter.mint(
        editions=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=user1)
