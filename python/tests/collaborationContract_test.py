"""Unit tests for the CollaborationContract class.

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
    lambdas_provider = sp.test_account("lambdas_provider")
    user = sp.test_account("user")

    # Initialize the artists contracts that will receive the shares
    artist1 = RecipientContract()
    artist2 = RecipientContract()
    artist3 = RecipientContract()

    # Initialize the collaboration contract
    collaboration = collaborationContract.CollaborationContract(
        metadata=sp.utils.metadata_of_url("ipfs://aaa"),
        collaborators={
            artist1.address: sp.record(id=0, share=200),
            artist2.address: sp.record(id=1, share=500),
            artist3.address: sp.record(id=2, share=300)},
        lambdas_provider=lambdas_provider.address)

    # Add the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += artist1
    scenario += artist2
    scenario += artist3
    scenario += collaboration

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario": scenario,
        "lambdas_provider": lambdas_provider,
        "user": user,
        "artist1": artist1,
        "artist2": artist2,
        "artist3": artist3,
        "collaboration": collaboration}

    return testEnvironment


@sp.add_test(name="Test transfer funds")
def test_transfer_funds():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    user = testEnvironment["user"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    artist3 = testEnvironment["artist3"]
    collaboration = testEnvironment["collaboration"]

    # Send some funds to the collaboration
    funds = sp.mutez(100)
    scenario += collaboration.default().run(sender=user, amount=funds)

    # Transfer the funds
    scenario += collaboration.transfer_funds().run(sender=artist1.address)

    # Check that all the funds have been transferred
    scenario.verify(collaboration.balance == sp.mutez(0))
    scenario.verify(artist1.balance - sp.split_tokens(funds, 200, 1000) <= sp.mutez(1))
    scenario.verify(artist2.balance - sp.split_tokens(funds, 500, 1000) <= sp.mutez(1))
    scenario.verify(artist3.balance - sp.split_tokens(funds, 300, 1000) <= sp.mutez(1))
    scenario.verify(funds == (artist1.balance + artist2.balance + artist3.balance))
