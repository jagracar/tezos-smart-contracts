import smartpy as sp


class CollaborationContract(sp.Contract):
    """A basic artists collaboration contract.

    """

    COLLABORATOR_TYPE = sp.TRecord(
        # The collaborator id
        id=sp.TNat,
        # The collaborator share
        share=sp.TNat).layout(
            ("id", "share"))

    PROPOSAL_TYPE = sp.TRecord(
        # Flag to indicate if the proposal has been already executed
        executed=sp.TBool,
        # The number of collaborator approvals
        approvals=sp.TNat,
        # The proposal lambda code in the lambda provider contract
        code=sp.TNat,
        # The proposal parameters
        parameters=sp.TBytes).layout(
            ("executed", ("approvals", ("code", "parameters"))))

    def __init__(self, metadata, collaborators, lambdas_provider):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The collaborators information (id, shares)
            collaborators=sp.TMap(
                sp.TAddress, CollaborationContract.COLLABORATOR_TYPE),
            # The collaboration proposals
            proposals=sp.TBigMap(sp.TNat, CollaborationContract.PROPOSAL_TYPE),
            # The collaborators proposal approvals
            approvals=sp.TBigMap(sp.TPair(sp.TNat, sp.TNat), sp.TBool),
            # The proposals bigmap counter
            counter=sp.TNat,
            # The lambda provider contract address
            lambdas_provider=sp.TAddress))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            collaborators=collaborators,
            proposals=sp.big_map(),
            approvals=sp.big_map(),
            counter=0,
            lambdas_provider=lambdas_provider)

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
                    sp.balance, collaborator.value.share, 1000)
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
            code=sp.TNat,
            parameters=sp.TBytes).layout(("code", "parameters")))

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            executed=False,
            approvals=1,
            code=params.code,
            parameters=params.parameters)

        # Assume that the collaborator approves their own proposal
        self.data.approvals[
            (self.data.counter, self.data.collaborators[sp.sender].id)] = True

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
        approval_key = sp.pair(
            params.proposal_id, self.data.collaborators[sp.sender].id)
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
        # except for cancel_swap and burn proposals
        proposal = sp.local("proposal", self.data.proposals[proposal_id])

        with sp.if_(proposal.value.code >= 10):
            sp.verify(
                proposal.value.approvals == sp.len(self.data.collaborators),
                message="COLLAB_NOT_APPROVED")

        # Get the lambda funtion to execute from the lambda provider contract
        lambda_function = sp.view(
            name="collab_lambda",
            address=self.data.lambdas_provider,
            param=proposal.value.code,
            t=sp.TLambda(sp.TBytes, sp.TList(sp.TOperation))).open_some()

        # Execute the proposal
        lambda_function(proposal.value.parameters)

        # Set the proposal as executed
        self.data.proposals[proposal_id].executed = True


sp.add_compilation_target("Collaboration", CollaborationContract(
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    collaborators={
        sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcaa"): sp.record(id=0, share=200),
        sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcbb"): sp.record(id=0, share=500),
        sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbccc"): sp.record(id=0, share=300)},
    lambdas_provider=sp.address("KT1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcDr")))
