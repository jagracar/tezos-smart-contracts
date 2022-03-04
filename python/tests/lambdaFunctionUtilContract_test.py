"""Unit tests for the LambdaFunctionUtilContract class.

"""

import smartpy as sp

# Import the lambdaFunctionUtilContract module
lambdaFunctionUtilContract = sp.io.import_script_from_url(
    "file:python/contracts/lambdaFunctionUtilContract.py")


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


@sp.add_test(name="Test lambda function")
def test_lambda_function():
    # Create the test account
    user = sp.test_account("user")

    # Initialize the dummy contract and the lambda function util contract
    dummyContract = DummyContract()
    lambdaFunctionUtil = lambdaFunctionUtilContract.LambdaFunctionUtilContract()

    # Add the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += dummyContract
    scenario += lambdaFunctionUtil

    # Define the lambda function that will update the dummy contract
    def lambda_function(params):
        sp.set_type(params, sp.TUnit)
        contractHandle = sp.contract(sp.TNat, dummyContract.address, "update_x").open_some()
        sp.result([sp.transfer_operation(sp.nat(2), sp.mutez(0), contractHandle)])

    # Update and execute the lambda function
    lambdaFunctionUtil.update_and_execute_lambda(lambda_function).run(sender=user)

    # Check that the dummy contract storage has been updated to the correct vale
    scenario.verify(dummyContract.data.x == 2)
    scenario.verify(dummyContract.data.y == 0)
