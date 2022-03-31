"""Unit tests for the extended FA2 class.

"""

import smartpy as sp

# Import the extendedFa2Contract module
extendedFa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/extendedFa2Contract.py")


class DummyContract(sp.Contract):
    """This dummy contract implements a callback method to receive the token
    balance information.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            balances=sp.TBigMap(sp.TPair(sp.TAddress, sp.TNat), sp.TNat)))

        # Initialize the contract storage
        self.init(balances=sp.big_map())

    @sp.entry_point
    def receive_balances(self, params):
        """Callback entry point that receives the token balance information.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TList(sp.TRecord(
                request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(("owner", "token_id")),
                balance=sp.TNat).layout(("request", "balance"))))

        # Save the returned information in the balances big map
        with sp.for_("balance_info", params) as balance_info:
            request = balance_info.request
            self.data.balances[
                (request.owner, request.token_id)] = balance_info.balance


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")

    # Initialize the extended FA2 contract
    fa2 = extendedFa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += fa2

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "fa2": fa2}

    return testEnvironment


@sp.add_test(name="Test mint")
def test_mint():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]

    # Check that the admin can mint
    editions = 5
    metadata = {"": sp.utils.bytes_of_string("ipfs://aaa")}
    data = {"code": sp.utils.bytes_of_string("print('hello world')")}
    royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=0),
        creator=sp.record(address=user2.address, royalties=50))
    fa2.mint(
        amount=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)
    scenario.verify(fa2.token_metadata(0).token_info[""] == metadata[""])
    scenario.verify(fa2.token_data(0)["code"] == data["code"])
    scenario.verify(fa2.token_royalties(0).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(0).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(0).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(0).creator.royalties == 50)
    scenario.verify(fa2.token_exists(0))
    scenario.verify(~fa2.token_exists(1))
    scenario.verify(fa2.count_tokens() == 1)
    scenario.verify(sp.len(fa2.all_tokens()) == 1)

    # Check that a normal user cannot mint
    fa2.mint(
        amount=editions,
        metadata=metadata,
        data=data,
        royalties=royalties).run(valid=False, sender=user1)

    # Check that minting fails if the total royalties exceed 100%
    wrong_royalties = sp.record(
        minter=sp.record(address=user1.address, royalties=500),
        creator=sp.record(address=user2.address, royalties=501))
    fa2.mint(
        amount=editions,
        metadata=metadata,
        data=data,
        royalties=wrong_royalties).run(valid=False, sender=admin)

    # Mint the next token
    new_editions = 5
    new_metadata = {"": sp.utils.bytes_of_string("ipfs://bbb")}
    new_data = {"description": sp.utils.bytes_of_string("my token description")}
    new_royalties = sp.record(
        minter=sp.record(address=user2.address, royalties=10),
        creator=sp.record(address=user2.address, royalties=100))
    fa2.mint(
        amount=new_editions,
        metadata=new_metadata,
        data=new_data,
        royalties=new_royalties).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == new_editions)
    scenario.verify(fa2.total_supply(0) == editions)
    scenario.verify(fa2.total_supply(1) == new_editions)
    scenario.verify(fa2.token_metadata(0).token_info[""] == metadata[""])
    scenario.verify(fa2.token_metadata(1).token_info[""] == new_metadata[""])
    scenario.verify(fa2.token_data(0)["code"] == data["code"])
    scenario.verify(fa2.token_data(1)["description"] == new_data["description"])
    scenario.verify(fa2.token_royalties(0).minter.address == user1.address)
    scenario.verify(fa2.token_royalties(0).minter.royalties == 0)
    scenario.verify(fa2.token_royalties(0).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(0).creator.royalties == 50)
    scenario.verify(fa2.token_royalties(1).minter.address == user2.address)
    scenario.verify(fa2.token_royalties(1).minter.royalties == 10)
    scenario.verify(fa2.token_royalties(1).creator.address == user2.address)
    scenario.verify(fa2.token_royalties(1).creator.royalties == 100)
    scenario.verify(fa2.token_exists(0))
    scenario.verify(fa2.token_exists(1))
    scenario.verify(~fa2.token_exists(2))
    scenario.verify(fa2.count_tokens() == 2)
    scenario.verify(sp.len(fa2.all_tokens()) == 2)


@sp.add_test(name="Test transfer")
def test_transfer():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint a token
    editions = 15
    fa2.mint(
        amount=editions,
        metadata={"": sp.utils.bytes_of_string("ipfs://aaa")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user1.address, royalties=0),
            creator=sp.record(address=user2.address, royalties=50))
        ).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that the creator cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=user2)

    # Check that another user cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=user3)

    # Check that the admin cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=admin)

    # Check that the owner can transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions - 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that the owner cannot transfer more tokens than the ones they have
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=30)])
        ]).run(valid=False, sender=user1)

    # Check that an owner cannot transfer other owners editions
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)])
        ]).run(valid=False, sender=user3)

    # Check that the new owner can transfer their own editions
    fa2.transfer([
        sp.record(
            from_=user3.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=1)])
        ]).run(sender=user3)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions - 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3 - 1)
    scenario.verify(fa2.total_supply(0) == editions)

    # Make the second user as operator of the first user token
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=0))]).run(sender=user1)

    # Check that the second user now can transfer the user1 editions
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=5)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == editions - 3 - 5)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 1)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3 - 1 + 5)
    scenario.verify(fa2.total_supply(0) == editions)


@sp.add_test(name="Test complex transfer")
def test_complex_transfer():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint two tokens
    fa2.mint(
        amount=10,
        metadata={"": sp.utils.bytes_of_string("ipfs://aaa")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user1.address, royalties=0),
            creator=sp.record(address=user1.address, royalties=100))
        ).run(sender=admin)
    fa2.mint(
        amount=20,
        metadata={"": sp.utils.bytes_of_string("ipfs://bbb")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user2.address, royalties=0),
            creator=sp.record(address=user2.address, royalties=100))
        ).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)
    scenario.verify(fa2.total_supply(0) == 10)
    scenario.verify(fa2.total_supply(1) == 20)

    # Check that users can only transfer tokens they own
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=3)])
        ]).run(valid=False, sender=user1)

    # Check that the owner can transfer the token to several users
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[
                sp.record(to_=user2.address, token_id=0, amount=2),
                sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10 - 2 - 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 2)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)

    # Check that the admin cannot transfer whatever token they want
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=5)])
        ]).run(valid=False, sender=admin)

    # Check that owners can transfer tokens to themselves
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[
                sp.record(to_=user2.address, token_id=0, amount=1),
                sp.record(to_=user2.address, token_id=0, amount=0),
                sp.record(to_=user2.address, token_id=1, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10 - 2 - 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 2)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)

    # Make the second user as operator of the first user token
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=0))]).run(sender=user1)

    # Check that the second user can transfer their tokens and the first user token
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=1)]),
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10 - 2 - 3 - 2)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 2)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 3 + 2)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20 - 1)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=1)) == 1)


@sp.add_test(name="Test balance of")
def test_balance_of():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Intialize the dummy contract and add it to the test scenario
    dummyContract = DummyContract()
    scenario += dummyContract

    # Get the contract handler to the receive_balances entry point
    c = sp.contract(
            t=sp.TList(sp.TRecord(
                request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(("owner", "token_id")),
                balance=sp.TNat).layout(("request", "balance"))),
            address=dummyContract.address,
            entry_point="receive_balances").open_some()

    # Mint two tokens
    fa2.mint(
        amount=10,
        metadata={"": sp.utils.bytes_of_string("ipfs://aaa")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user1.address, royalties=0),
            creator=sp.record(address=user1.address, royalties=100))
        ).run(sender=admin)
    fa2.mint(
        amount=20,
        metadata={"": sp.utils.bytes_of_string("ipfs://bbb")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user2.address, royalties=0),
            creator=sp.record(address=user2.address, royalties=100))
        ).run(sender=admin)

    # Check the balances using the on-chain view
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)

    # Check that it doesn't fail if there is not row for that information in the ledger
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=0)) == 0)
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=1)) == 0)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=1)) == 0)

    # Check that it fails if the token doesn't exist
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user1.address, token_id=10))))

    # Check that asking for the token balances fails if the token doesn't exist
    fa2.balance_of(sp.record(
        requests=[sp.record(owner=user1.address, token_id=10)],
        callback=c)).run(valid=False, sender=user3)

    # Ask for the token balances
    fa2.balance_of(sp.record(
        requests=[
            sp.record(owner=user1.address, token_id=0),
            sp.record(owner=user2.address, token_id=0),
            sp.record(owner=user3.address, token_id=0),
            sp.record(owner=user1.address, token_id=1),
            sp.record(owner=user2.address, token_id=1),
            sp.record(owner=user3.address, token_id=1)],
        callback=c)).run(sender=user3)

    # Check that the returned balances are correct
    scenario.verify(dummyContract.data.balances[(user1.address, 0)] == 10)
    scenario.verify(dummyContract.data.balances[(user2.address, 0)] == 0)
    scenario.verify(dummyContract.data.balances[(user3.address, 0)] == 0)
    scenario.verify(dummyContract.data.balances[(user1.address, 1)] == 0)
    scenario.verify(dummyContract.data.balances[(user2.address, 1)] == 20)
    scenario.verify(dummyContract.data.balances[(user3.address, 1)] == 0)


@sp.add_test(name="Test update operators")
def test_update_operators():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    fa2 = testEnvironment["fa2"]

    # Mint two tokens
    fa2.mint(
        amount=10,
        metadata={"": sp.utils.bytes_of_string("ipfs://aaa")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user1.address, royalties=0),
            creator=sp.record(address=user1.address, royalties=100))
        ).run(sender=admin)
    fa2.mint(
        amount=20,
        metadata={"": sp.utils.bytes_of_string("ipfs://bbb")},
        data={},
        royalties=sp.record(
            minter=sp.record(address=user2.address, royalties=0),
            creator=sp.record(address=user2.address, royalties=100))
        ).run(sender=admin)

    # Check that the operators information is empty
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user2.address, operator=user1.address, token_id=1)))

    # Check that is not possible to change the operators if one is not the owner
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user3)

    # Check that the admin cannot add operators
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)

    # Check that the user can change the operators of token they own or might
    # own in the future
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=1)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=1))
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=1)))

    # Check that adding and removing operators works at the same time
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=1)),
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=1)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=1)))

    # Check that removing an operator that doesn't exist works
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))

    # Check operators cannot change the operators of editions that they don't own
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0))]).run(valid=False, sender=user2)
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)

    # Check that the admin cannot remove operators
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)


@sp.add_test(name="Test transfer and accept administrator")
def test_transfer_and_accept_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]

    # Check the original administrator
    scenario.verify(fa2.data.administrator == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = user1.address
    fa2.transfer_administrator(new_administrator).run(valid=False, sender=user1)
    fa2.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(fa2.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    fa2.accept_administrator().run(valid=False, sender=admin)
    fa2.accept_administrator().run(sender=user1)

    # Check that the administrator is updated
    scenario.verify(fa2.data.administrator == new_administrator)
    scenario.verify(~fa2.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = user2.address
    fa2.transfer_administrator(new_administrator).run(valid=False, sender=admin)
    fa2.transfer_administrator(new_administrator).run(sender=user1)

    # Check that the proposed administrator is updated
    scenario.verify(fa2.data.proposed_administrator.open_some() == new_administrator)


@sp.add_test(name="Test set metadata")
def test_set_metadata():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]

    # Check that only the admin can update the metadata
    new_metadata = sp.record(k="", v=sp.utils.bytes_of_string("ipfs://zzzz"))
    fa2.set_metadata(new_metadata).run(valid=False, sender=user1)
    fa2.set_metadata(new_metadata).run(sender=admin)

    # Check that the metadata is updated
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)

    # Add some extra metadata
    extra_metadata = sp.record(k="aaa", v=sp.utils.bytes_of_string("ipfs://ffff"))
    fa2.set_metadata(extra_metadata).run(sender=admin)

    # Check that the two metadata entries are present
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)
    scenario.verify(fa2.data.metadata[extra_metadata.k] == extra_metadata.v)
