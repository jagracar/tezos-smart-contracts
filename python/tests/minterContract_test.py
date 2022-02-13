"""Unit tests for the MinterContract class.

"""

import smartpy as sp

# Import the extendedFa2Contract and minterContract modules
extendedFa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/extendedFa2Contract.py")
minterContract = sp.io.import_script_from_url(
    "file:python/contracts/minterContract.py")


def get_test_environment():
    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")
    ngo1 = sp.test_account("ngo1")
    ngo2 = sp.test_account("ngo2")

    # Initialize extended FA2 and minter contracts
    fa2 = extendedFa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    minter = minterContract.MinterContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"),
        fa2=fa2.address)

    # Add the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += fa2
    scenario += minter

    # Set the minter contract as the admin of the FA2 contract
    scenario += fa2.set_administrator(minter.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "ngo1": ngo1,
        "ngo2": ngo2,
        "fa2": fa2,
        "minter": minter}

    return testEnvironment


@sp.add_test(name="Test single creator mint")
def test_single_creator_mint():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    ngo1 = testEnvironment["ngo1"]
    ngo2 = testEnvironment["ngo2"]
    fa2 = testEnvironment["fa2"]
    minter = testEnvironment["minter"]

    # Check that a normal user can mint
    editions = 5
    metadata = sp.pack("ipfs://aaa")
    royalties = 100
    donations = []
    scenario += minter.single_creator_mint(
        editions=editions,
        metadata=metadata,
        royalties=royalties,
        donations=donations).run(sender=user1)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata)
    scenario.verify(fa2.get_mint_parameters(0).minter.address == user1.address)
    scenario.verify(fa2.get_mint_parameters(0).minter.royalties == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).creators) == 1)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).donations) == 0)

    # Check that trying to mint a token with zero editions fails
    scenario += minter.single_creator_mint(
        editions=0,
        metadata=metadata,
        royalties=royalties,
        donations=donations).run(valid=False, sender=user1)

    # Check that trying to set very hight royalties fails
    scenario += minter.single_creator_mint(
        editions=editions,
        metadata=metadata,
        royalties=300,
        donations=donations).run(valid=False, sender=user1)

    # Check that providing more than 5 donation destinations fails
    scenario += minter.single_creator_mint(
        editions=editions,
        metadata=metadata,
        royalties=royalties,
        donations=[
            sp.record(address=ngo1.address, royalties=10),
            sp.record(address=ngo2.address, royalties=10),
            sp.record(address=ngo1.address, royalties=20),
            sp.record(address=ngo2.address, royalties=20),
            sp.record(address=ngo1.address, royalties=30),
            sp.record(address=ngo2.address, royalties=30)]).run(valid=False, sender=user1)

    # Check that providing more 75% percent of donation royalties fails
    scenario += minter.single_creator_mint(
        editions=editions,
        metadata=metadata,
        royalties=royalties,
        donations=[
            sp.record(address=ngo1.address, royalties=450),
            sp.record(address=ngo2.address, royalties=301)]).run(valid=False, sender=user1)

    # Mint another token
    new_editions = 10
    new_metadata = sp.pack("ipfs://bbb")
    new_royalties = 150
    new_donations = [sp.record(address=ngo1.address, royalties=100),
                     sp.record(address=ngo2.address, royalties=200)]
    scenario += minter.single_creator_mint(
        editions=new_editions,
        metadata=new_metadata,
        royalties=new_royalties,
        donations=new_donations).run(sender=user2)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == new_editions)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.data.total_supply[1] == new_editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata)
    scenario.verify(fa2.data.token_metadata[1].token_id == 1)
    scenario.verify(fa2.data.token_metadata[1].token_info[""] == new_metadata)
    scenario.verify(fa2.get_mint_parameters(0).minter.address == user1.address)
    scenario.verify(fa2.get_mint_parameters(0).minter.royalties == 0)
    scenario.verify(fa2.get_mint_parameters(1).minter.address == user2.address)
    scenario.verify(fa2.get_mint_parameters(1).minter.royalties == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).creators) == 1)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).donations) == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(1).creators) == 1)
    scenario.verify(sp.len(fa2.get_mint_parameters(1).donations) == 2)
