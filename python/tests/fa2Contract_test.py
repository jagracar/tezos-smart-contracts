"""Unit tests for the FA2 class.

"""

import smartpy as sp

# Import the fa2Contract module
fa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/fa2Contract.py")


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
    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")

    # Initialize the FA2 contract
    fa2 = fa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += fa2

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "admin" : admin,
        "user1" : user1,
        "user2" : user2,
        "user3" : user3,
        "fa2" : fa2}

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

    # Check that a normal user cannot mint
    address = user1.address
    editions = 5
    metadata = {"": sp.pack("ipfs://fff")}
    token_id = 0
    fa2.mint(
        address=address,
        amount=editions,
        metadata=metadata,
        token_id=token_id).run(valid=False, sender=user1)

    # Check that the admin can mint
    fa2.mint(
        address=address,
        amount=editions,
        metadata=metadata,
        token_id=token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(address, token_id)].balance == editions)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.data.token_metadata[token_id].token_id == token_id)
    scenario.verify(fa2.data.token_metadata[token_id].token_info[""] == metadata[""])
    scenario.verify(fa2.data.all_tokens == token_id + 1)
    scenario.verify(fa2.count_tokens() == token_id + 1)
    scenario.verify(fa2.does_token_exist(token_id))
    scenario.verify(~fa2.does_token_exist(token_id + 1))
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(fa2.total_supply(token_id) == editions)

    # Check that it's possible to mint again the same token id
    new_metadata = {"": sp.pack("ipfs://zzz")}
    fa2.mint(
        address=address,
        amount=editions,
        metadata=new_metadata,
        token_id=token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(address, token_id)].balance == 2 * editions)
    scenario.verify(fa2.data.total_supply[token_id] == 2 * editions)
    scenario.verify(fa2.total_supply(token_id) == 2 * editions)

    # Check that it still contrains the old token metadata and the number of
    # tokens didn't increase
    scenario.verify(fa2.data.token_metadata[token_id].token_info[""] == metadata[""])
    scenario.verify(fa2.data.all_tokens == token_id + 1)
    scenario.verify(fa2.count_tokens() == token_id + 1)
    scenario.verify(fa2.does_token_exist(token_id))
    scenario.verify(sp.len(fa2.all_tokens()) == 1)

    # Check that it's possible to mint again the same token id with another address
    new_address = user2.address
    fa2.mint(
        address=new_address,
        amount=editions,
        metadata=new_metadata,
        token_id=token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(address, token_id)].balance == 2 * editions)
    scenario.verify(fa2.data.ledger[(new_address, token_id)].balance == editions)
    scenario.verify(fa2.data.total_supply[token_id] == 3 * editions)
    scenario.verify(fa2.data.token_metadata[token_id].token_info[""] == metadata[""])
    scenario.verify(fa2.data.all_tokens == token_id + 1)
    scenario.verify(fa2.count_tokens() == token_id + 1)
    scenario.verify(fa2.does_token_exist(token_id))
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(fa2.total_supply(token_id) == 3 * editions)

    # Check that minting doesn't fail if the number of editions is zero
    fa2.mint(
        address=address,
        amount=0,
        metadata=new_metadata,
        token_id=token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(address, token_id)].balance == 2 * editions)
    scenario.verify(fa2.data.ledger[(new_address, token_id)].balance == editions)
    scenario.verify(fa2.data.total_supply[token_id] == 3 * editions)
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(fa2.total_supply(token_id) == 3 * editions)

    # Check that minting fails if the token ids are not consecutive
    fa2.mint(
        address=address,
        amount=0,
        metadata=new_metadata,
        token_id=token_id + 4).run(valid=False, sender=admin)

    # Mint the next token
    new_editions = 20
    new_token_id = token_id + 1
    fa2.mint(
        address=new_address,
        amount=new_editions,
        metadata=new_metadata,
        token_id=new_token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(address, token_id)].balance == 2 * editions)
    scenario.verify(fa2.data.ledger[(new_address, token_id)].balance == editions)
    scenario.verify(fa2.data.ledger[(new_address, new_token_id)].balance == new_editions)
    scenario.verify(fa2.data.total_supply[token_id] == 3 * editions)
    scenario.verify(fa2.data.total_supply[new_token_id] == new_editions)
    scenario.verify(fa2.data.token_metadata[token_id].token_id == token_id)
    scenario.verify(fa2.data.token_metadata[token_id].token_info[""] == metadata[""])
    scenario.verify(fa2.data.token_metadata[new_token_id].token_id == new_token_id)
    scenario.verify(fa2.data.token_metadata[new_token_id].token_info[""] == new_metadata[""])
    scenario.verify(fa2.data.all_tokens == new_token_id + 1)
    scenario.verify(fa2.count_tokens() == new_token_id + 1)
    scenario.verify(fa2.does_token_exist(new_token_id))
    scenario.verify(sp.len(fa2.all_tokens()) == 2)
    scenario.verify(fa2.total_supply(token_id) == 3 * editions)
    scenario.verify(fa2.total_supply(new_token_id) == new_editions)


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
    metadata = {"": sp.pack("ipfs://fff")}
    token_id = 0
    fa2.mint(
        address=user1.address,
        amount=editions,
        metadata=metadata,
        token_id=token_id).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, token_id)].balance == editions)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.data.token_metadata[token_id].token_id == token_id)
    scenario.verify(fa2.total_supply(token_id) == editions)

    # Check that another user cannot transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=token_id, amount=3)])
        ]).run(valid=False, sender=user2)

    # Check that the owner can transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=token_id, amount=3)])
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, token_id)].balance == editions - 3)
    scenario.verify(fa2.data.ledger[(user3.address, token_id)].balance == 3)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.total_supply(token_id) == editions)

    # Check that the admin can transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=token_id, amount=3)])
        ]).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, token_id)].balance == editions - 6)
    scenario.verify(fa2.data.ledger[(user2.address, token_id)].balance == 3)
    scenario.verify(fa2.data.ledger[(user3.address, token_id)].balance == 3)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.total_supply(token_id) == editions)

    # Check that the owner or the admin cannot transfer more tokens that the owner has
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=token_id, amount=30)])
        ]).run(valid=False, sender=admin)
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=token_id, amount=30)])
        ]).run(valid=False, sender=user1)

    # Check that an owner cannot transfer other owners editions
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=token_id, amount=1)])
        ]).run(valid=False, sender=user2)

    # Check that the owner can transfer their own editions
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=token_id, amount=1)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, token_id)].balance == editions - 6)
    scenario.verify(fa2.data.ledger[(user2.address, token_id)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, token_id)].balance == 4)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.total_supply(token_id) == editions)

    # Make the second user as operator of the first user token
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=token_id))]).run(sender=user1)

    # Check that the second user now can transfer the user1 editions
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=token_id, amount=5)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, token_id)].balance == editions - 6 - 5)
    scenario.verify(fa2.data.ledger[(user2.address, token_id)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, token_id)].balance == 4 + 5)
    scenario.verify(fa2.data.total_supply[token_id] == editions)
    scenario.verify(fa2.total_supply(token_id) == editions)


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
        address=user1.address,
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        token_id=0).run(sender=admin)
    fa2.mint(
        address=user2.address,
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        token_id=1).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 10)
    scenario.verify(fa2.data.ledger[(user2.address, 1)].balance == 20)
    scenario.verify(fa2.data.total_supply[0] == 10)
    scenario.verify(fa2.data.total_supply[1] == 20)

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
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 10 - 2 - 3)
    scenario.verify(fa2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)].balance == 3)
    scenario.verify(fa2.data.ledger[(user2.address, 1)].balance == 20)

    # Check that the admin can transfer whatever token they want
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=5)])
        ]).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 10 - 2 - 3 - 1)
    scenario.verify(fa2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)].balance == 4)
    scenario.verify(fa2.data.ledger[(user2.address, 1)].balance == 20 - 5)
    scenario.verify(fa2.data.ledger[(user3.address, 1)].balance == 5)

    # Check that owners can transfer tokens to themselves
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[
                sp.record(to_=user2.address, token_id=0, amount=1),
                sp.record(to_=user2.address, token_id=0, amount=2),
                sp.record(to_=user2.address, token_id=1, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 10 - 2 - 3 - 1)
    scenario.verify(fa2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)].balance == 4)
    scenario.verify(fa2.data.ledger[(user2.address, 1)].balance == 20 - 5)
    scenario.verify(fa2.data.ledger[(user3.address, 1)].balance == 5)

    # Make the second user as operator of the first user token
    fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=0))]).run(sender=user1)

    # Check that the second user can transfer their tokens and the fist user token
    fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=1)]),
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)].balance == 10 - 2 - 3 - 1 - 2)
    scenario.verify(fa2.data.ledger[(user2.address, 0)].balance == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)].balance == 4 + 2)
    scenario.verify(fa2.data.ledger[(user2.address, 1)].balance == 20 - 5 - 1)
    scenario.verify(fa2.data.ledger[(user3.address, 1)].balance == 5 + 1)


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
        address=user1.address,
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        token_id=0).run(sender=admin)
    fa2.mint(
        address=user2.address,
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        token_id=1).run(sender=admin)
    fa2.mint(
        address=user3.address,
        amount=5,
        metadata={"": sp.pack("ipfs://ccc")},
        token_id=1).run(sender=admin)

    # Check the balances using the off-chain view
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)
    scenario.verify(fa2.get_balance(sp.record(owner=user3.address, token_id=1)) == 5)

    # Check that it fails if there is not row for that information in the ledger
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user2.address, token_id=0))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user3.address, token_id=0))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user1.address, token_id=1))))
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
    scenario.verify(dummyContract.data.balances[(user3.address, 1)] == 5)

    # Pause the contract
    fa2.set_pause(True).run(sender=admin)

    # Ceck that now asking for the token balances fails
    fa2.balance_of(sp.record(
        requests=[
            sp.record(owner=user1.address, token_id=0),
            sp.record(owner=user2.address, token_id=0),
            sp.record(owner=user3.address, token_id=0),
            sp.record(owner=user1.address, token_id=1),
            sp.record(owner=user2.address, token_id=1),
            sp.record(owner=user3.address, token_id=1)],
        callback=c)).run(valid=False, sender=user3)


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
        address=user1.address,
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        token_id=0).run(sender=admin)
    fa2.mint(
        address=user2.address,
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        token_id=1).run(sender=admin)

    # Check that the operators information is empty
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))

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

    # Check that the admin can add operators
    fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))

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
            token_id=10)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=10)))

    # Check that adding and removing operators works at the same time
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0)),
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=10)),
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=10)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=10)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=10)))

    # Check that removing an operator that doesn't exist works
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=100)))
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=100)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=100)))

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

    # Check that the admin can remove operators
    fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))


@sp.add_test(name="Test set administrator")
def test_set_administrator():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]

    # Check the original administrator
    scenario.verify(fa2.data.administrator == admin.address)

    # Check that only the admin can set the new administrator
    new_administrator = user1.address
    fa2.set_administrator(new_administrator).run(valid=False, sender=user1)
    fa2.set_administrator(new_administrator).run(sender=admin)

    # Check that the administrator has been updated
    scenario.verify(fa2.data.administrator == new_administrator)


@sp.add_test(name="Test set metadata")
def test_set_metadata():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    fa2 = testEnvironment["fa2"]

    # Check that only the admin can update the metadata
    new_metadata = sp.record(k="", v=sp.pack("ipfs://zzzz"))
    fa2.set_metadata(new_metadata).run(valid=False, sender=user1)
    fa2.set_metadata(new_metadata).run(sender=admin)

    # Check that the metadata is updated
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)

    # Add some extra metadata
    extra_metadata = sp.record(k="aaa", v=sp.pack("ipfs://ffff"))
    fa2.set_metadata(extra_metadata).run(sender=admin)

    # Check that the two metadata entries are present
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)
    scenario.verify(fa2.data.metadata[extra_metadata.k] == extra_metadata.v)


@sp.add_test(name="Test set pause")
def test_set_pause():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    fa2 = testEnvironment["fa2"]

    # Mint a token
    fa2.mint(
        address=user1.address,
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        token_id=0).run(sender=admin)

    # Check that the owner can transfer the token
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(sender=user1)

    # Check that the user cannot pause the contract
    fa2.set_pause(True).run(valid=False, sender=user1)

    # Pause the contract
    fa2.set_pause(True).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.paused)

    # Check that now is not possible to transfer tokens
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=user1)

    # Check that it's still possible to mint
    fa2.mint(
        address=user1.address,
        amount=10,
        metadata={"": sp.pack("ipfs://bbb")},
        token_id=1).run(sender=admin)

    # Unpause the contract
    fa2.set_pause(False).run(sender=admin)

    # Check that it's possible to transfer tokens again
    fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(sender=user1)
