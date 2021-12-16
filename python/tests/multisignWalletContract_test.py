"""Unit tests for the MultisignWalletContract class.

"""

import smartpy as sp

# Import the multisignWalletContract module
multisignWalletContract = sp.io.import_script_from_url(
    "file:python/contracts/multisignWalletContract.py")


class DummyContract(sp.Contract):
    """This is a dummy contract to be used only for test purposes.

    """

    def __init__(self):
        """Initializes the contract.

        """
        self.init(x=sp.nat(0), y=sp.nat(0))

    @sp.entry_point
    def update_x(self, x):
        """Updates the x value.

        """
        self.data.x = x

    @sp.entry_point
    def update_y(self, y):
        """Updates the y value.

        """
        self.data.y = y


def get_test_environment():
    # Create the test accounts
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")
    user4 = sp.test_account("user4")

    # Initialize the multisign wallet contract
    multisign = multisignWalletContract.MultisignWalletContract(
        metadata=sp.utils.metadata_of_url("ipfs://aaa"),
        users=sp.set([user1.address, user2.address, user3.address, user4.address]),
        minimum_votes=3,
        expiration_time=3)

    # Add some initial balance to the multisign wallet
    multisign.set_initial_balance(sp.tez(10))

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += multisign

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "user1" : user1,
        "user2" : user2,
        "user3" : user3,
        "user4" : user4,
        "multisign" : multisign}

    return testEnvironment


@sp.add_test(name="Test transter mutez proposal")
def test_transfer_mutez_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Create the account that will receive the tez transfer
    receptor = sp.test_account("receptor")

    # Add a transfer tez proposal
    scenario += multisign.transfer_mutez_proposal(sp.list([
        sp.record(amount=sp.tez(3), destination=receptor.address)])).run(sender=user1)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[0].executed)


@sp.add_test(name="Test transter token proposal")
def test_transfer_token_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Create the dummy token
    token = sp.test_account("token")

    # Create the account that will receive the tez transfer
    receptor = sp.test_account("receptor")

    # Add a transfer token proposal
    scenario += multisign.transfer_token_proposal(
        fa2=token.address,
        token_id=sp.nat(1),
        distribution=sp.list([sp.record(
            amount=sp.nat(5),
            destination=receptor.address)])).run(sender=user3)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[0].executed)


@sp.add_test(name="Test minimum votes proposal")
def test_minimum_votes_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Add a minimum votes proposal
    scenario += multisign.minimum_votes_proposal(2).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the minimum votes parameter has been updated
    scenario.verify(multisign.data.minimum_votes == 2)


@sp.add_test(name="Test expiration time proposal")
def test_expiration_time_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Add an expiration time proposal
    scenario += multisign.expiration_time_proposal(100).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the expiration time has been updated
    scenario.verify(multisign.data.expiration_time == 100)


@sp.add_test(name="Test add user proposal")
def test_add_user_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Create the new user account
    user5 = sp.test_account("user5")

    # Add a add user proposal
    scenario += multisign.add_user_proposal(user5.address).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[0].executed)

    # Check that now there is 5 users
    scenario.verify(sp.len(multisign.data.users.elements()) == 5)
    scenario.verify(multisign.data.users.contains(user5.address))


@sp.add_test(name="Test remove user proposal")
def test_remove_user_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Add a remove user proposal
    scenario += multisign.remove_user_proposal(user2.address).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[0].executed)

    # Check that now there is only 3 users and that the minimum votes were not changed
    scenario.verify(sp.len(multisign.data.users.elements()) == 3)
    scenario.verify(~multisign.data.users.contains(user2.address))
    scenario.verify(multisign.data.minimum_votes == 3)

    # Add another remove user proposal
    scenario += multisign.remove_user_proposal(user1.address).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(1).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[1].executed)

    # Check that now there is only 2 users
    scenario.verify(sp.len(multisign.data.users.elements()) == 2)
    scenario.verify(~multisign.data.users.contains(user1.address))

    # Check that the minimum votes parameter has been updated
    scenario.verify(multisign.data.minimum_votes == 2)


@sp.add_test(name="Test expired proposal")
def test_expired_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Create the account that will receive the tez transfer
    receptor = sp.test_account("receptor")

    # Add a transfer mutez proposal
    scenario += multisign.transfer_mutez_proposal(sp.list([
        sp.record(amount=sp.tez(3), destination=receptor.address)])).run(sender=user1, now=sp.timestamp(1000))

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)

    # Check that the vote fails if the proposal time has expired
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(
        valid=False, sender=user4, now=sp.timestamp(1000).add_days(4))

    # Add another transfer mutez proposal
    scenario += multisign.transfer_mutez_proposal(sp.list([
        sp.record(amount=sp.tez(3), destination=receptor.address)])).run(sender=user1, now=sp.timestamp(1000))

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=1, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=1, approval=True).run(sender=user4)

    # Check that the execution fails because the proposal time has expired
    scenario += multisign.execute_proposal(1).run(
        valid=False, sender=user3, now=sp.timestamp(1000).add_days(4))


@sp.add_test(name="Test lambda proposal")
def test_lambda_proposal():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    user3 = testEnvironment["user3"]
    user4 = testEnvironment["user4"]
    multisign = testEnvironment["multisign"]

    # Initialize the dummy contract and add it to the scenario
    dummyContract = DummyContract()
    scenario += dummyContract

    # Define the lambda function that will update the dummy contract
    def dummy_lambda_function(params):
        sp.set_type(params, sp.TUnit)
        dummyContractHandle = sp.contract(sp.TNat, dummyContract.address, "update_x").open_some()
        sp.result([sp.transfer_operation(sp.nat(2), sp.mutez(0), dummyContractHandle)])

    # Add a lambda proposal
    scenario += multisign.lambda_proposal(dummy_lambda_function).run(sender=user4)

    # Vote for the proposal
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user1)
    scenario += multisign.vote_proposal(proposal_id=0, approval=False).run(sender=user2)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user3)
    scenario += multisign.vote_proposal(proposal_id=0, approval=True).run(sender=user4)

    # Execute the proposal
    scenario += multisign.execute_proposal(0).run(sender=user3)

    # Check that the proposal is listed as executed
    scenario.verify(multisign.data.proposals[0].executed)

    # Check that the dummy contract storage has been updated to the correct vale
    scenario.verify(dummyContract.data.x == 2)
