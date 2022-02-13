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
    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")
    ngo1 = sp.test_account("ngo1")
    ngo2 = sp.test_account("ngo2")

    # Initialize the extended FA2 contract
    fa2 = extendedFa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += fa2

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "ngo1": ngo1,
        "ngo2": ngo2,
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
    ngo1 = testEnvironment["ngo1"]
    ngo2 = testEnvironment["ngo2"]
    fa2 = testEnvironment["fa2"]

    # Check that a normal user cannot mint
    editions = 5
    metadata = {"": sp.pack("ipfs://aaa")}
    minter = sp.record(address=user1.address, royalties=0)
    creators = [sp.record(address=user1.address, royalties=50),
                sp.record(address=user2.address, royalties=100)]
    donations = []
    scenario += fa2.mint(
        amount=editions,
        metadata=metadata,
        minter=minter,
        creators=creators,
        donations=donations).run(valid=False, sender=user1)

    # Check that the admin can mint
    scenario += fa2.mint(
        amount=editions,
        metadata=metadata,
        minter=minter,
        creators=creators,
        donations=donations).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(minter.address, 0)] == editions)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata[""])
    scenario.verify(fa2.get_mint_parameters(0).minter.address == user1.address)
    scenario.verify(fa2.get_mint_parameters(0).minter.royalties == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).creators) == 2)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).donations) == 0)
    scenario.verify(fa2.data.counter == 1)
    scenario.verify(fa2.does_token_exist(0))
    scenario.verify(~fa2.does_token_exist(1))
    scenario.verify(fa2.count_tokens() == 1)
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that minting fails if the number of editions is zero
    scenario += fa2.mint(
        amount=0,
        metadata=metadata,
        minter=minter,
        creators=creators,
        donations=donations).run(valid=False, sender=admin)

    # Check that minting fails if the creators is zero
    scenario += fa2.mint(
        amount=editions,
        metadata=metadata,
        minter=minter,
        creators=[],
        donations=donations).run(valid=False, sender=admin)

    # Mint the next token
    new_editions = 5
    new_metadata = {"": sp.pack("ipfs://bbb")}
    new_minter = sp.record(address=user2.address, royalties=0)
    new_creators = [sp.record(address=user2.address, royalties=50)]
    new_donations = [sp.record(address=ngo1.address, royalties=100),
                     sp.record(address=ngo2.address, royalties=100)]
    scenario += fa2.mint(
        amount=new_editions,
        metadata=new_metadata,
        minter=new_minter,
        creators=new_creators,
        donations=new_donations).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(minter.address, 0)] == editions)
    scenario.verify(fa2.data.ledger[(new_minter.address, 1)] == new_editions)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.data.total_supply[1] == new_editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == metadata[""])
    scenario.verify(fa2.data.token_metadata[1].token_id == 1)
    scenario.verify(fa2.data.token_metadata[1].token_info[""] == new_metadata[""])
    scenario.verify(fa2.get_mint_parameters(0).minter.address == user1.address)
    scenario.verify(fa2.get_mint_parameters(0).minter.royalties == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).creators) == 2)
    scenario.verify(sp.len(fa2.get_mint_parameters(0).donations) == 0)
    scenario.verify(fa2.get_mint_parameters(1).minter.address == user2.address)
    scenario.verify(fa2.get_mint_parameters(1).minter.royalties == 0)
    scenario.verify(sp.len(fa2.get_mint_parameters(1).creators) == 1)
    scenario.verify(sp.len(fa2.get_mint_parameters(1).donations) == 2)
    scenario.verify(fa2.data.counter == 2)
    scenario.verify(fa2.does_token_exist(0))
    scenario.verify(fa2.does_token_exist(1))
    scenario.verify(~fa2.does_token_exist(2))
    scenario.verify(fa2.count_tokens() == 2)
    scenario.verify(sp.len(fa2.all_tokens()) == 2)
    scenario.verify(fa2.total_supply(0) == editions)
    scenario.verify(fa2.total_supply(1) == new_editions)


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
    metadata = {"": sp.pack("ipfs://aaa")}
    minter = sp.record(address=user1.address, royalties=0)
    creators = [sp.record(address=user1.address, royalties=50)]
    donations = []
    scenario += fa2.mint(
        amount=editions,
        metadata=metadata,
        minter=minter,
        creators=creators,
        donations=donations).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.data.token_metadata[0].token_id == 0)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that another user cannot transfer the token
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=user2)

    # Check that the admin cannot transfer the token
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=3)])
        ]).run(valid=False, sender=admin)

    # Check that the owner can transfer the token
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions - 3)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Check that the owner cannot transfer more tokens than the ones they have
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=30)])
        ]).run(valid=False, sender=user1)

    # Check that an owner cannot transfer other owners editions
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)])
        ]).run(valid=False, sender=user2)

    # Check that the new owner can transfer their own editions
    scenario += fa2.transfer([
        sp.record(
            from_=user3.address,
            txs=[sp.record(to_=user2.address, token_id=0, amount=1)])
        ]).run(sender=user3)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions - 3)
    scenario.verify(fa2.data.ledger[(user2.address, 0)] == 1)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3 - 1)
    scenario.verify(fa2.data.total_supply[0] == editions)
    scenario.verify(fa2.total_supply(0) == editions)

    # Make the second user as operator of the first user token
    scenario += fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=0))]).run(sender=user1)

    # Check that the second user now can transfer the user1 editions
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=5)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == editions - 3 - 5)
    scenario.verify(fa2.data.ledger[(user2.address, 0)] == 1)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3 - 1 + 5)
    scenario.verify(fa2.data.total_supply[0] == editions)
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
    scenario += fa2.mint(
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        minter=sp.record(address=user1.address, royalties=0),
        creators=[sp.record(address=user1.address, royalties=100)],
        donations=[]).run(sender=admin)
    scenario += fa2.mint(
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        minter=sp.record(address=user2.address, royalties=0),
        creators=[sp.record(address=user2.address, royalties=100)],
        donations=[]).run(sender=admin)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == 10)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == 20)
    scenario.verify(fa2.data.total_supply[0] == 10)
    scenario.verify(fa2.data.total_supply[1] == 20)

    # Check that users can only transfer tokens they own
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=3)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=3)])
        ]).run(valid=False, sender=user1)

    # Check that the owner can transfer the token to several users
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[
                sp.record(to_=user2.address, token_id=0, amount=2),
                sp.record(to_=user3.address, token_id=0, amount=3)])
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == 10 - 2 - 3)
    scenario.verify(fa2.data.ledger[(user2.address, 0)] == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == 20)

    # Check that the admin cannot transfer whatever token they want
    scenario += fa2.transfer([
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=1)]),
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=5)])
        ]).run(valid=False, sender=admin)

    # Check that owners can transfer tokens to themselves
    scenario += fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[
                sp.record(to_=user2.address, token_id=0, amount=1),
                sp.record(to_=user2.address, token_id=0, amount=2),
                sp.record(to_=user2.address, token_id=1, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == 10 - 2 - 3)
    scenario.verify(fa2.data.ledger[(user2.address, 0)] == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == 20)

    # Make the second user as operator of the first user token
    scenario += fa2.update_operators([sp.variant("add_operator", sp.record(
        owner=user1.address,
        operator=user2.address,
        token_id=0))]).run(sender=user1)

    # Check that the second user can transfer their tokens and the fist user token
    scenario += fa2.transfer([
        sp.record(
            from_=user2.address,
            txs=[sp.record(to_=user3.address, token_id=1, amount=1)]),
        sp.record(
            from_=user1.address,
            txs=[sp.record(to_=user3.address, token_id=0, amount=2)])
        ]).run(sender=user2)

    # Check that the contract information has been updated
    scenario.verify(fa2.data.ledger[(user1.address, 0)] == 10 - 2 - 3 - 2)
    scenario.verify(fa2.data.ledger[(user2.address, 0)] == 2)
    scenario.verify(fa2.data.ledger[(user3.address, 0)] == 3 + 2)
    scenario.verify(fa2.data.ledger[(user2.address, 1)] == 20 - 1)
    scenario.verify(fa2.data.ledger[(user3.address, 1)] == 1)


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
    scenario += fa2.mint(
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        minter=sp.record(address=user1.address, royalties=0),
        creators=[sp.record(address=user1.address, royalties=100)],
        donations=[]).run(sender=admin)
    scenario += fa2.mint(
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        minter=sp.record(address=user2.address, royalties=0),
        creators=[sp.record(address=user2.address, royalties=100)],
        donations=[]).run(sender=admin)

    # Check the balances using the off-chain view
    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 10)
    scenario.verify(fa2.get_balance(sp.record(owner=user2.address, token_id=1)) == 20)

    # Check that it fails if there is not row for that information in the ledger
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user2.address, token_id=0))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user3.address, token_id=0))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user1.address, token_id=1))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user3.address, token_id=1))))
    scenario.verify(sp.is_failing(fa2.get_balance(sp.record(owner=user1.address, token_id=10))))

    # Check that asking for the token balances fails if the token doesn't exist
    scenario += fa2.balance_of(sp.record(
        requests=[sp.record(owner=user1.address, token_id=10)],
        callback=c)).run(valid=False, sender=user3)

    # Ask for the token balances
    scenario += fa2.balance_of(sp.record(
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
    scenario += fa2.mint(
        amount=10,
        metadata={"": sp.pack("ipfs://aaa")},
        minter=sp.record(address=user1.address, royalties=0),
        creators=[sp.record(address=user1.address, royalties=100)],
        donations=[]).run(sender=admin)
    scenario += fa2.mint(
        amount=20,
        metadata={"": sp.pack("ipfs://bbb")},
        minter=sp.record(address=user2.address, royalties=0),
        creators=[sp.record(address=user2.address, royalties=100)],
        donations=[]).run(sender=admin)

    # Check that the operators information is empty
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=0)))

    # Check that is not possible to change the operators if one is not the owner
    scenario += fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)
    scenario += fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user3)

    # Check that the admin cannot add operators
    scenario += fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)

    # Check that the user can change the operators of token they own or might
    # own in the future
    scenario += fa2.update_operators([
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
        sp.record(owner=user1.address, operator=user3.address, token_id=0)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user2.address, token_id=1)))
    scenario.verify(fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=10)))

    # Check that adding and removing operators works at the same time
    scenario += fa2.update_operators([
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
    scenario += fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=100)),
        ]).run(sender=user1)

    # Check that the contract information has been updated
    scenario.verify(~fa2.is_operator(
        sp.record(owner=user1.address, operator=user3.address, token_id=100)))

    # Check operators cannot change the operators of editions that they don't own
    scenario += fa2.update_operators([
        sp.variant("add_operator", sp.record(
            owner=user1.address,
            operator=user3.address,
            token_id=0))]).run(valid=False, sender=user2)
    scenario += fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=user2)

    # Check that the admin cannot remove operators
    scenario += fa2.update_operators([
        sp.variant("remove_operator", sp.record(
            owner=user1.address,
            operator=user2.address,
            token_id=0))]).run(valid=False, sender=admin)


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
    scenario += fa2.set_administrator(new_administrator).run(valid=False, sender=user1)
    scenario += fa2.set_administrator(new_administrator).run(sender=admin)

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
    scenario += fa2.set_metadata(new_metadata).run(valid=False, sender=user1)
    scenario += fa2.set_metadata(new_metadata).run(sender=admin)

    # Check that the metadata is updated
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)

    # Add some extra metadata
    extra_metadata = sp.record(k="aaa", v=sp.pack("ipfs://ffff"))
    scenario += fa2.set_metadata(extra_metadata).run(sender=admin)

    # Check that the two metadata entries are present
    scenario.verify(fa2.data.metadata[new_metadata.k] == new_metadata.v)
    scenario.verify(fa2.data.metadata[extra_metadata.k] == extra_metadata.v)
