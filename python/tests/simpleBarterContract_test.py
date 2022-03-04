"""Unit tests for the SimpleBarterContract class.

"""

import smartpy as sp

# Import the simpleBarterContract and fa2Contract modules
simpleBarterContract = sp.io.import_script_from_url(
    "file:python/contracts/simpleBarterContract.py")
fa2Contract = sp.io.import_script_from_url(
    "file:python/templates/fa2Contract.py")


def get_test_environment():
    # Create the test accounts
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")
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
    barter = simpleBarterContract.SimpleBarterContract(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"))

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
        "user3" : user3,
        "fa2_admin" : fa2_admin,
        "fa2_1" : fa2_1,
        "fa2_2" : fa2_2,
        "barter" : barter}

    return testEnvironment


@sp.add_test(name="Test trade with second user")
def test_trade_with_second_user():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    fa2_2 = testEnvironment["fa2_2"]
    barter = testEnvironment["barter"]

    # Mint some tokens
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
    fa2_2.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)
    fa2_2.mint(
        address=user2.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Transfer some tokens to the first and third user
    fa2_2.transfer(sp.list([sp.record(
        from_=user2.address,
        txs=sp.list([
            sp.record(to_=user1.address, token_id=1, amount=30),
            sp.record(to_=user3.address, token_id=1, amount=30)]))])).run(sender=user2)

    # Add the barter contract as operator for the tokens
    fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user2.address,
            operator=barter.address,
            token_id=1))]).run(sender=user2)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user3.address,
            operator=barter.address,
            token_id=1))]).run(sender=user3)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 30)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 40)
    scenario.verify(fa2_2.data.ledger[(user3.address, 1)].balance == 30)

    # Propose a trade with the second user
    barter.propose_trade(
        tokens=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2)),
            sp.record(fa2=fa2_2.address, id=sp.nat(0), amount=sp.nat(2))]),
        for_tokens=sp.list([
            sp.record(fa2=fa2_2.address, id=sp.nat(1), amount=sp.nat(10))]),
        with_user=sp.some(user2.address)).run(valid=False, sender=user1, amount=sp.tez(3))
    barter.propose_trade(
        tokens=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2)),
            sp.record(fa2=fa2_2.address, id=sp.nat(0), amount=sp.nat(2))]),
        for_tokens=sp.list([
            sp.record(fa2=fa2_2.address, id=sp.nat(1), amount=sp.nat(10))]),
        with_user=sp.some(user2.address)).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 30)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 40)
    scenario.verify(fa2_2.data.ledger[(user3.address, 1)].balance == 30)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 2)

    # Check that the first and third users cannot accept the trade because they
    # are not the assigned second user
    barter.accept_trade(0).run(valid=False, sender=user1)
    barter.accept_trade(0).run(valid=False, sender=user3)

    # The second user accepts the trade
    barter.accept_trade(0).run(valid=False, sender=user2, amount=sp.tez(3))
    barter.accept_trade(0).run(sender=user2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 30 + 10)
    scenario.verify(fa2_1.data.ledger[(user2.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(user2.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 40 - 10)
    scenario.verify(fa2_2.data.ledger[(user3.address, 1)].balance == 30)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 0)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 0)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 0)

    # Check that the second user cannot accept twice the trade
    barter.accept_trade(0).run(valid=False, sender=user2)


@sp.add_test(name="Test trade without second user")
def test_trade_without_second_user():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    fa2_2 = testEnvironment["fa2_2"]
    barter = testEnvironment["barter"]

    # Mint some tokens
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
    fa2_2.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)
    fa2_2.mint(
        address=user2.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Add the barter contract as operator for the tokens
    fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user2.address,
            operator=barter.address,
            token_id=1))]).run(sender=user2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100)

    # Propose a trade with no specific second user
    barter.propose_trade(
        tokens=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2)),
            sp.record(fa2=fa2_2.address, id=sp.nat(0), amount=sp.nat(2))]),
        for_tokens=sp.list([
            sp.record(fa2=fa2_2.address, id=sp.nat(1), amount=sp.nat(10))]),
        with_user=sp.none).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 2)

    # Check that the first and third users cannot accept the trade because they
    # don't own the requested token
    barter.accept_trade(0).run(valid=False, sender=user1)
    barter.accept_trade(0).run(valid=False, sender=user3)

    # The second user accepts the trade
    barter.accept_trade(0).run(sender=user2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 10)
    scenario.verify(fa2_1.data.ledger[(user2.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(user2.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100 - 10)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 0)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 0)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 0)

    # Check that the second user cannot accept twice the trade
    barter.accept_trade(0).run(valid=False, sender=user2)


@sp.add_test(name="Test trade same user")
def test_trade_same_user():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    fa2_2 = testEnvironment["fa2_2"]
    barter = testEnvironment["barter"]

    # Mint some tokens
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
    fa2_2.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)
    fa2_2.mint(
        address=user1.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Add the barter contract as operator for the tokens
    fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 100)

    # Propose a trade with no specific second user
    barter.propose_trade(
        tokens=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2)),
            sp.record(fa2=fa2_2.address, id=sp.nat(0), amount=sp.nat(2))]),
        for_tokens=sp.list([
            sp.record(fa2=fa2_2.address, id=sp.nat(1), amount=sp.nat(10))]),
        with_user=sp.none).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 2)

    # The first user accepts its own trade
    barter.accept_trade(0).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 0)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 0)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 0)

    # Check that the first user cannot accept twice the trade
    barter.accept_trade(0).run(valid=False, sender=user1)

@sp.add_test(name="Test cancel trade")
def test_cancel_trade():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2_admin = testEnvironment["fa2_admin"]
    fa2_1 = testEnvironment["fa2_1"]
    fa2_2 = testEnvironment["fa2_2"]
    barter = testEnvironment["barter"]

    # Mint some tokens
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
    fa2_2.mint(
        address=user1.address,
        token_id=sp.nat(0),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)
    fa2_2.mint(
        address=user2.address,
        token_id=sp.nat(1),
        amount=sp.nat(100),
        metadata={"" : sp.utils.bytes_of_string("ipfs://eee")}).run(sender=fa2_admin)

    # Add the barter contract as operator for the tokens
    fa2_1.update_operators(
        [sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0)),
        sp.variant("add_operator", fa2_1.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=1))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user1.address,
            operator=barter.address,
            token_id=0))]).run(sender=user1)
    fa2_2.update_operators(
        [sp.variant("add_operator", fa2_2.operator_param.make(
            owner=user2.address,
            operator=barter.address,
            token_id=1))]).run(sender=user2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100)

    # Propose a trade with the second user
    barter.propose_trade(
        tokens=sp.list([
            sp.record(fa2=fa2_1.address, id=sp.nat(0), amount=sp.nat(1)),
            sp.record(fa2=fa2_1.address, id=sp.nat(1), amount=sp.nat(2)),
            sp.record(fa2=fa2_2.address, id=sp.nat(0), amount=sp.nat(2))]),
        for_tokens=sp.list([
            sp.record(fa2=fa2_2.address, id=sp.nat(1), amount=sp.nat(10))]),
        with_user=sp.some(user2.address)).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100 - 1)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100 - 2)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 1)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 2)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 2)

    # Check that the second user cannot cancel the trade
    barter.cancel_trade(0).run(valid=False, sender=user2)

    # Cancel the trade
    barter.cancel_trade(0).run(valid=False, sender=user1, amount=sp.tez(3))
    barter.cancel_trade(0).run(sender=user1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(fa2_1.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(user1.address, 1)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user1.address, 0)].balance == 100)
    scenario.verify(fa2_2.data.ledger[(user2.address, 1)].balance == 100)
    scenario.verify(fa2_1.data.ledger[(barter.address, 0)].balance == 0)
    scenario.verify(fa2_1.data.ledger[(barter.address, 1)].balance == 0)
    scenario.verify(fa2_2.data.ledger[(barter.address, 0)].balance == 0)

    # Check that the first user cannot cancel the trade again
    barter.cancel_trade(0).run(valid=False, sender=user1)
