import smartpy as sp


class LambdaFunctionUtilContract(sp.Contract):
    """This contract is an untility contract used to extract the michelson code
    from a given lambda function.

    The contract can be used to get the code needed to build a lambda proposal
    for the multisign wallet contract.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            lambda_function=sp.TOption(
                sp.TLambda(sp.TUnit, sp.TList(sp.TOperation)))))

        # Initialize the contract storage
        self.init(lambda_function=sp.none)

    @sp.entry_point
    def update_and_execute_lambda(self, lambda_function):
        """Updates and executes the contract lambda function.

        """
        # Define the input parameter data type
        sp.set_type(
            lambda_function, sp.TLambda(sp.TUnit, sp.TList(sp.TOperation)))

        # Save the lambda function in the contract storage
        self.data.lambda_function = sp.some(lambda_function)

        # Execute the lambda function
        operations = self.data.lambda_function.open_some()(sp.unit)

        # Add the lambda function operations
        sp.add_operations(operations)


# Add a compilation target
sp.add_compilation_target("lambdaFunctionUtil", LambdaFunctionUtilContract())
