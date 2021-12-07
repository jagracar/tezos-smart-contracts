"""Unit tests for the BarterContract class.

"""

import smartpy as sp

# Import the simpleBarterContract and fa2Contract module
simpleBarterContract = sp.io.import_script_from_url(
    "file:python/contracts/simpleBarterContract.py")
fa2Contract = sp.io.import_script_from_url(
    "file:python/templates/fa2Contract.py")


def get_test_environment():
    # Create the test accounts
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    fa2_admin = sp.test_account("fa2_admin")

    # Initialize the two FA2 contracts
    fa2_1 = fa2Contract.FA2(
        config=fa2Contract.FA2_config(),
        admin=fa2_admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    fa2_2 = fa2Contract.FA2(
        config=fa2Contract.FA2_config(),
        admin=fa2_admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"))

    # Initialize the simple barter contract
    barter = simpleBarterContract.SimpleBarterContract()

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += fa2_1
    scenario += fa2_2
    scenario += barter

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "user1" : user1,
        "user2" : user2,
        "fa2_admin" : fa2_admin,
        "fa2_1" : fa2_1,
        "fa2_2" : fa2_2,
        "barter" : barter}

    return testEnvironment


@sp.add_test(name="Test propose trade")
def test_propose_trade():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2_1 = testEnvironment["fa2_1"]
    fa2_2 = testEnvironment["fa2_2"]
    barter = testEnvironment["barter"]

    # Propose a trade that involves only fa2_1 tokens
    scenario += barter.propose_trade(
        user1=user1.address,
        user2=user2.address,
        tokens1=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(2), amount=sp.nat(2))]),
        tokens2=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(3), amount=sp.nat(100))])).run(sender=user1)

    # Propose a trade that also involves fa2_2 tokens and check that it doesn't fail
    scenario += barter.propose_trade(
        user1=user1.address,
        user2=user2.address,
        tokens1=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(1)),
            sp.record(fa2=fa2_2.address, id=sp.nat(2), amount=sp.nat(2))]),
        tokens2=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(3), amount=sp.nat(100))])).run(sender=user2)


@sp.add_test(name="Test execute trade")
def test_execute_trade():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    barter = testEnvironment["barter"]

    # Mint some tokens for the involved users
    fa2_1.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://ccc")}).run(sender=fa2_admin)
    fa2_1.mint(
        address=user1.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://ddd")}).run(sender=fa2_admin)
    fa2_1.mint(
        address=user2.address,
        token_id=sp.nat(2),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Add the barter contract as operator for the tokens
    scenario += fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    scenario += fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user2.address,
            operator=barter.address,
            token_id=2))]).run(sender=user2)

    # Propose a trade
    scenario += barter.propose_trade(
        user1=user1.address,
        user2=user2.address,
        tokens1=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2))]),
        tokens2=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(2), amount=sp.nat(100))])).run(sender=user1)

    # Accept the trade
    scenario += barter.accept_trade(0).run(sender=user1)
    scenario += barter.accept_trade(0).run(sender=user2)

    # Execute the trade
    scenario += barter.execute_trade(0).run(sender=user2)


@sp.add_test(name="Test cancel trade")
def test_cancel_trade():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    barter = testEnvironment["barter"]

    # Mint some tokens for the involved users
    fa2_1.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://ccc")}).run(sender=fa2_admin)
    fa2_1.mint(
        address=user1.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://ddd")}).run(sender=fa2_admin)
    fa2_1.mint(
        address=user2.address,
        token_id=sp.nat(2),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Add the barter contract as operator for the tokens
    scenario += fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    scenario += fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user2.address,
            operator=barter.address,
            token_id=2))]).run(sender=user2)

    # Propose a trade
    scenario += barter.propose_trade(
        user1=user1.address,
        user2=user2.address,
        tokens1=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2))]),
        tokens2=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(2), amount=sp.nat(100))])).run(sender=user1)

    # Accept the trade
    scenario += barter.accept_trade(0).run(sender=user1)
    scenario += barter.accept_trade(0).run(sender=user2)

    # Cancel the trade
    scenario += barter.cancel_trade(0).run(sender=user1)
    scenario += barter.cancel_trade(0).run(sender=user2)
