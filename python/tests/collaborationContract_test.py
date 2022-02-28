"""Unit tests for the CollaborationContract classes.

"""

import smartpy as sp

# Import the collaborationContract module
collaborationContract = sp.io.import_script_from_url(
    "file:python/contracts/collaborationContract.py")


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
    # Create the test accounts
    admin = sp.test_account("admin")
    user = sp.test_account("user")

    # Initialize the artists contracts that will receive the shares
    artist1 = RecipientContract()
    artist2 = RecipientContract()
    artist3 = RecipientContract()

    # Initialize the collaboration originator contract
    originator = collaborationContract.CollabOriginatorContract(
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))

    # Initialize the lambda provider contract
    lambda_provider = collaborationContract.LambdaProviderContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"))

    # Add the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += artist1
    scenario += artist2
    scenario += artist3
    scenario += originator
    scenario += lambda_provider

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "admin": admin,
        "user": user,
        "artist1": artist1,
        "artist2": artist2,
        "artist3": artist3,
        "originator": originator,
        "lambda_provider": lambda_provider}

    return testEnvironment


@sp.add_test(name="Test origination")
def test_origination():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user = testEnvironment["user"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    artist3 = testEnvironment["artist3"]
    originator = testEnvironment["originator"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Check that creating a collaboration with a single collaborator fails
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        collaborators={artist1.address: 1000},
        lambda_provider=lambda_provider.address)).run(valid=False, sender=artist1.address)

    # Check that creating a collaboration with wrong shares fails
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        collaborators={artist1.address: 200,
                       artist2.address: 500,
                       artist3.address: 301},
        lambda_provider=lambda_provider.address)).run(valid=False, sender=artist1.address)

    # Check that the collaboration can only be created by one of the collaborators
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        collaborators={artist1.address: 200,
                       artist2.address: 500,
                       artist3.address: 300},
        lambda_provider=lambda_provider.address)).run(valid=False, sender=user)

    # Create a collaboration contract
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        collaborators={artist1.address: 200,
                       artist2.address: 500,
                       artist3.address: 300},
        lambda_provider=lambda_provider.address)).run(sender=artist1.address)

    # Check that the contract information is correct
    scenario.verify(originator.data.metadata[""] == sp.utils.bytes_of_string("ipfs://aaa"))
    scenario.verify(originator.data.collaborations.contains(0))
    scenario.verify(originator.data.counter == 1)

    # Get the collaboration contract
    scenario.register(originator.contract)
    collab0 = scenario.dynamic_contract(0, originator.contract)

    # Check that the contract addresses are correct
    scenario.verify(collab0.address == originator.data.collaborations[0])

    # Check that the collaboration information is correct
    scenario.verify(collab0.data.metadata[""] == sp.utils.bytes_of_string("ipfs://ccc"))
    scenario.verify(sp.len(collab0.data.collaborators) == 3)
    scenario.verify(collab0.data.collaborators[artist1.address] == 200)
    scenario.verify(collab0.data.collaborators[artist2.address] == 500)
    scenario.verify(collab0.data.collaborators[artist3.address] == 300)
    scenario.verify(collab0.data.counter == 0)

    # Create another collaboration contract
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ddd"),
        collaborators={artist1.address: 400,
                       artist2.address: 600},
        lambda_provider=lambda_provider.address)).run(sender=artist1.address)

    # Check that the contract information is correct
    scenario.verify(originator.data.collaborations.contains(0))
    scenario.verify(originator.data.collaborations.contains(1))
    scenario.verify(originator.data.counter == 2)

    # Get the collaboration contract
    collab1 = scenario.dynamic_contract(1, originator.contract)

    # Check that the contract addresses are correct
    scenario.verify(collab1.address == originator.data.collaborations[1])

    # Check that the collaboration information is correct
    scenario.verify(collab1.data.metadata[""] == sp.utils.bytes_of_string("ipfs://ddd"))
    scenario.verify(sp.len(collab1.data.collaborators) == 2)
    scenario.verify(collab1.data.collaborators[artist1.address] == 400)
    scenario.verify(collab1.data.collaborators[artist2.address] == 600)
    scenario.verify(collab1.data.counter == 0)


@sp.add_test(name="Test transfer funds")
def test_transfer_funds():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user = testEnvironment["user"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    artist3 = testEnvironment["artist3"]
    originator = testEnvironment["originator"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Create a collaboration contract
    originator.create_collaboration(sp.record(
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        collaborators={artist1.address: 200,
                       artist2.address: 500,
                       artist3.address: 300},
        lambda_provider=lambda_provider.address)).run(sender=artist1.address)

    # Get the collaboration contract
    scenario.register(originator.contract)
    collaboration = scenario.dynamic_contract(0, originator.contract)

    # Send some funds to the collaboration
    funds = sp.mutez(100)
    collaboration.call("default", sp.unit).run(sender=user, amount=funds)

    # Check that the funds arrived to the collaboration contract
    scenario.verify(collaboration.balance == sp.mutez(100))

    # Check that only the collaborators can transfer the funds
    collaboration.call("transfer_funds", sp.unit).run(valid=False, sender=user)

    # Transfer the funds
    collaboration.call("transfer_funds", sp.unit).run(sender=artist1.address)

    # Check that all the funds have been transferred
    scenario.verify(collaboration.balance == sp.mutez(0))
    scenario.verify(artist1.balance - sp.split_tokens(funds, 200, 1000) <= sp.mutez(1))
    scenario.verify(artist2.balance - sp.split_tokens(funds, 500, 1000) <= sp.mutez(1))
    scenario.verify(artist3.balance - sp.split_tokens(funds, 300, 1000) <= sp.mutez(1))
    scenario.verify(funds == (artist1.balance + artist2.balance + artist3.balance))

    # Check that the transfer funds entry point doesn't fail in there are no tez
    collaboration.call("transfer_funds", sp.unit).run(sender=artist1.address)
