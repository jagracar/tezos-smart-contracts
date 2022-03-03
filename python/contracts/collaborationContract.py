import smartpy as sp


class CollaborationContract(sp.Contract):
    """A basic artists collaboration contract.

    """

    PROPOSAL_TYPE = sp.TRecord(
        # Flag to indicate if the proposal has been already executed
        executed=sp.TBool,
        # The number of collaborator approvals
        approvals=sp.TNat,
        # The proposal lambda function id in the lambda provider contract
        lambda_id=sp.TNat,
        # The proposal lambda function parameters
        parameters=sp.TBytes).layout(
            ("executed", ("approvals", ("lambda_id", "parameters"))))

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The collaborators and their share in the collaboration
            collaborators=sp.TMap(sp.TAddress, sp.TNat),
            # The lambda provider contract address
            lambda_provider=sp.TAddress,
            # The collaboration proposals
            proposals=sp.TBigMap(sp.TNat, CollaborationContract.PROPOSAL_TYPE),
            # The collaborators proposal approvals
            approvals=sp.TBigMap(sp.TPair(sp.TNat, sp.TAddress), sp.TBool),
            # The proposals bigmap counter
            counter=sp.TNat))

    def check_is_collaborator(self):
        """Checks that the address that called the entry point is one of the
        collaboration members.

        """
        sp.verify(self.data.collaborators.contains(sp.sender),
                  message="COLLAB_NOT_COLLABORATOR")

    def check_proposal_is_valid(self, proposal_id):
        """Checks that the proposal_id is from a valid proposal.

        """
        # Check that the proposal id is present in the proposals big map
        sp.verify(self.data.proposals.contains(proposal_id),
                  message="COLLAB_INEXISTENT_PROPOSAL")

        # Check that the proposal has not been executed
        sp.verify(~self.data.proposals[proposal_id].executed,
                  message="COLLAB_EXECUTED_PROPOSAL")

    @sp.entry_point
    def default(self, unit):
        """Default entrypoint that allows receiving tez transfers in the same
        way as one would do with a normal tz wallet.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Do nothing, just receive tez
        pass

    @sp.entry_point
    def transfer_funds(self, unit):
        """Transfers all the existing funds to the collaborators.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Distribute the funds
        transfer_amount = sp.local("transfer_amount", sp.mutez(0))
        transferred_amount = sp.local("transferred_amount", sp.mutez(0))
        counter = sp.local("counter", sp.len(self.data.collaborators))

        with sp.for_("collaborator", self.data.collaborators.items()) as collaborator:
            # Calculate the amount to transfer to the collaborator
            with sp.if_(counter.value > 1):
                transfer_amount.value = sp.split_tokens(
                    sp.balance, collaborator.value, 1000)
            with sp.else_():
                transfer_amount.value = sp.balance - transferred_amount.value

            # Transfer the mutez to the collaborator
            sp.send(collaborator.key, transfer_amount.value)

            # Update the counters
            transferred_amount.value += transfer_amount.value
            counter.value = sp.as_nat(counter.value - 1)

    @sp.entry_point
    def add_proposal(self, params):
        """Adds a new proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            lambda_id=sp.TNat,
            parameters=sp.TBytes).layout(("lambda_id", "parameters")))

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Check that the lambda function exists in the lambda provider contract
        sp.verify(
            sp.view(
                name="has_lambda",
                address=self.data.lambda_provider,
                param=params.lambda_id,
                t=sp.TBool).open_some(),
            message="COLLAB_INEXISTENT_LAMBDA")

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            executed=False,
            approvals=1,
            lambda_id=params.lambda_id,
            parameters=params.parameters)

        # Assume that the collaborator approves their own proposal
        self.data.approvals[(self.data.counter, sp.sender)] = True

        # Increase the proposals counter
        self.data.counter += 1

    @sp.entry_point
    def approve(self, params):
        """Approves or not a collaboration proposal.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            proposal_id=sp.TNat,
            approval=sp.TBool).layout(("proposal_id", "approval")))

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Check that is a valid proposal
        self.check_proposal_is_valid(params.proposal_id)

        # Check if the collaborator approved the proposal before and remove
        # their approval from the proposal approvals counter
        approval_key = sp.pair(params.proposal_id, sp.sender)
        proposal = self.data.proposals[params.proposal_id]

        with sp.if_(self.data.approvals.get(approval_key, default_value=False)):
            proposal.approvals = sp.as_nat(proposal.approvals - 1)

        # Add the approval to the proposal approvals counter if it's positive
        with sp.if_(params.approval):
            proposal.approvals += 1

        # Add or update the collaborator approval
        self.data.approvals[approval_key] = params.approval

    @sp.entry_point
    def execute_proposal(self, proposal_id):
        """Executes a given proposal.

        """
        # Define the input parameter data type
        sp.set_type(proposal_id, sp.TNat)

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Check that is a valid proposal
        self.check_proposal_is_valid(proposal_id)

        # Check that the proposal received all the collaborator approvals,
        # except for special lambdas (lambda_id < 10)
        proposal = sp.local("proposal", self.data.proposals[proposal_id])

        with sp.if_(proposal.value.lambda_id >= 10):
            sp.verify(
                proposal.value.approvals == sp.len(self.data.collaborators),
                message="COLLAB_NOT_APPROVED")
        with sp.else_():
            sp.verify(
                proposal.value.approvals >= 1,
                message="COLLAB_NOT_APPROVED")

        # Set the proposal as executed
        self.data.proposals[proposal_id].executed = True

        # Get the lambda function to execute from the lambda provider contract
        lambda_function = sp.view(
            name="get_lambda",
            address=self.data.lambda_provider,
            param=proposal.value.lambda_id,
            t=LambdaProviderContract.LAMBDA_FUNCTION_TYPE).open_some()

        # Execute the proposal
        operations = lambda_function(proposal.value.parameters)
        sp.add_operations(operations)


class CollabOriginatorContract(sp.Contract):
    """A contract used to originate the artists collaboration contracts.

    """

    def __init__(self, metadata):
        """Initializes the contract.

        """
        # Initialize the collaboration contract
        self.contract = CollaborationContract()

        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The big map with all the originated collaborations
            collaborations=sp.TBigMap(sp.TNat, sp.TAddress),
            # The collaborations bigmap counter
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            collaborations=sp.big_map(),
            counter=0)

    @sp.entry_point
    def create_collaboration(self, params):
        """Creates a new collaboration contract.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            collaborators=sp.TMap(sp.TAddress, sp.TNat),
            lambda_provider=sp.TAddress).layout(
                ("metadata", ("collaborators", "lambda_provider"))))

        # Check that there is at least two collaborators
        sp.verify(sp.len(params.collaborators) > 1,
                  message="ORIGINATOR_FEW_COLLABORATORS")

        # Check that the collaboration is initiated by one of the collaborators
        sp.verify(params.collaborators.contains(sp.sender),
                  message="ORIGINATOR_NO_COLLABORATOR")

        # Check that the collaborators shares add to a total of 1000
        total_shares = sp.local("total_shares", sp.nat(0))

        with sp.for_("share", params.collaborators.values()) as share:
            total_shares.value += share

        sp.verify(total_shares.value == 1000, message="ORIGINATOR_WRONG_SHARES")

        # Create the new contract and add it to the collaborations big map
        self.data.collaborations[self.data.counter] = sp.create_contract(
            contract=self.contract,
            storage=sp.record(
                metadata=params.metadata,
                collaborators=params.collaborators,
                lambda_provider=params.lambda_provider,
                proposals=sp.big_map(
                    tkey=sp.TNat, tvalue=CollaborationContract.PROPOSAL_TYPE),
                approvals=sp.big_map(
                    tkey=sp.TPair(sp.TNat, sp.TAddress), tvalue=sp.TBool),
                counter=sp.nat(0)),
            amount=sp.mutez(0))

        # Increase the collaborations counter
        self.data.counter += 1


class LambdaProviderContract(sp.Contract):
    """A proxy contract that is used by the artists collaboration contract to
    call other contracts.

    """

    LAMBDA_FUNCTION_TYPE = sp.TLambda(sp.TBytes, sp.TList(sp.TOperation))

    LAMBDA_RECORD_TYPE = sp.TRecord(
        # Flag to indicate if the lambda function is enabled or disabled
        enabled=sp.TBool,
        # The lambda function alias (e.g mint_objkt, swap_teia)
        alias=sp.TString,
        # The lambda function
        lambda_function=LAMBDA_FUNCTION_TYPE).layout(
            ("enabled", ("alias", "lambda_function")))

    def __init__(self, administrator, metadata):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract administrador
            administrator=sp.TAddress,
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The big map with all the lambda functions
            lambdas=sp.TBigMap(
                sp.TNat, LambdaProviderContract.LAMBDA_RECORD_TYPE),
            # The proposed new administrator address
            proposed_administrator=sp.TOption(sp.TAddress)))

        # Initialize the contract storage
        self.init(
            administrator=administrator,
            metadata=metadata,
            lambdas=sp.big_map(),
            proposed_administrator=sp.none)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contract
        administrator.

        """
        sp.verify(sp.sender == self.data.administrator,
                  message="PROXY_NOT_ADMIN")

    def check_lambda_exists(self, lambda_id):
        """Checks that the lambda id is from an existing lambda function.

        """
        sp.verify(self.data.lambdas.contains(lambda_id),
                  message="PROXY_INEXISTENT_LAMBDA")

    @sp.entry_point
    def add_lambda(self, params):
        """Adds a new lambda function.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            lambda_id=sp.TNat,
            alias=sp.TString,
            lambda_function=LambdaProviderContract.LAMBDA_FUNCTION_TYPE).layout(
                ("lambda_id", ("alias", "lambda_function"))))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that the lambda id doesn't exist already
        sp.verify(~self.data.lambdas.contains(params.lambda_id),
                  message="PROXY_EXISTENT_LAMBDA")

        # Add the new lambda function
        self.data.lambdas[params.lambda_id] = sp.record(
            enabled=True,
            alias=params.alias,
            lambda_function=params.lambda_function)

    @sp.entry_point
    def enable_lambda(self, params):
        """Enables or disables an existing lambda function.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            lambda_id=sp.TNat,
            enabled=sp.TBool).layout(("lambda_id", "enabled")))

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that the lambda function is present in the lambdas big map
        self.check_lambda_exists(params.lambda_id)

        # Enable or disable the lambda function
        self.data.lambdas[params.lambda_id].enabled = params.enabled

    @sp.onchain_view()
    def has_lambda(self, lambda_id):
        """Returns true if the lambda function exists.

        """
        # Define the input parameter data type
        sp.set_type(lambda_id, sp.TNat)

        # Return true if the lambda function exists
        sp.result(self.data.lambdas.contains(lambda_id))

    @sp.onchain_view()
    def get_lambda(self, lambda_id):
        """Returns an existing lambda function.

        """
        # Define the input parameter data type
        sp.set_type(lambda_id, sp.TNat)

        # Check that the lambda function is present in the lambdas big map
        self.check_lambda_exists(lambda_id)

        # Check that the lambda function is enabled
        sp.verify(self.data.lambdas[lambda_id].enabled,
                  message="PROXY_DISABLED_LAMBDA")

        # Return the lambda function
        sp.result(self.data.lambdas[lambda_id].lambda_function)

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contract administrator to another address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contract administrator
        responsabilities.

        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="PROXY_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="PROXY_NOT_PROPOSED_ADMIN")

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none


sp.add_compilation_target("Collaboration", CollaborationContract())

sp.add_compilation_target("CollabOriginator", CollabOriginatorContract(
    metadata=sp.utils.metadata_of_url("ipfs://aaa")))

sp.add_compilation_target("LambdaProvider", LambdaProviderContract(
    administrator=sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr"),
    metadata=sp.utils.metadata_of_url("ipfs://bbb")))
