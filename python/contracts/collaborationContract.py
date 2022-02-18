import smartpy as sp


class CollaborationContract(sp.Contract):
    """A basic artists collaboration contract.

    """

    PROPOSAL_KIND_TYPE = sp.TVariant(
        # A mint proposal
        mint=sp.TUnit,
        # A swap proposal
        swap=sp.TUnit)

    PROPOSAL_TYPE = sp.TRecord(
        # The kind of proposal: mint or swap
        kind=PROPOSAL_KIND_TYPE,
        # Flag to indicate if the proposal has been already executed
        executed=sp.TBool,
        # The number of collaborator approvals
        approvals=sp.TNat,
        # The mint or swap parameters
        parameters=sp.TBytes).layout(
            ("kind", ("executed", ("approvals", "parameters"))))

    def __init__(self, metadata, shares):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The list of collaborators
            collaborators=sp.TSet(sp.TAddress),
            # The collaboration shares distribution
            shares=sp.TMap(sp.TAddress, sp.TNat),
            # The collaboration total shares
            total_shares=sp.TNat,
            # The collaboration proposals
            proposals=sp.TBigMap(sp.TNat, CollaborationContract.PROPOSAL_TYPE),
            # The collaborators proposal approvals
            approvals=sp.TBigMap(sp.TPair(sp.TNat, sp.TAddress), sp.TBool),
            # The proposals bigmap counter
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            collaborators=sp.set(shares.keys()),
            shares=shares,
            total_shares=sum(shares.values()),
            proposals=sp.big_map(),
            approvals=sp.big_map(),
            counter=0)

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
        counter = sp.local("counter", sp.len(self.data.shares))

        with sp.for_("share", self.data.shares.items()) as share:
            # Calculate the amount to transfer to the collaborator
            with sp.if_(counter.value > 1):
                transfer_amount.value = sp.split_tokens(
                    sp.balance, share.value, self.data.total_shares)
            with sp.else_():
                transfer_amount.value = sp.balance - transferred_amount.value

            # Transfer the mutez to the collaborator
            sp.send(share.key, transfer_amount.value)

            # Update the counters
            transferred_amount.value += transfer_amount.value
            counter.value = sp.as_nat(counter.value - 1)

    @sp.entry_point
    def add_proposal(self, params):
        """Adds a new proposal to the proposals big map.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            kind=CollaborationContract.PROPOSAL_KIND_TYPE,
            parameters=sp.TBytes).layout(("kind", "parameters")))

        # Check that one of the collaborators executed the entry point
        self.check_is_collaborator()

        # Update the proposals bigmap with the new proposal information
        self.data.proposals[self.data.counter] = sp.record(
            kind=params.kind,
            executed=False,
            approvals=1,
            parameters=params.parameters)

        # Add the collaborator approval for their submitted proposal
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
        proposal = self.data.proposals[params.proposal_id]

        with sp.if_(self.data.approvals.get((params.proposal_id, sp.sender), default_value=False)):
            proposal.approvals = sp.as_nat(proposal.approvals - 1)

        # Add the approval to the proposal approvals counter if it's positive
        with sp.if_(params.approval):
            proposal.approvals += 1

        # Add or update the collaborator approval
        self.data.approvals[(params.proposal_id, sp.sender)] = params.approval

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

        # Check that the proposal received all the collaborator approvals
        proposal = sp.local("proposal", self.data.proposals[proposal_id])
        sp.verify(proposal.value.approvals == sp.len(self.data.collaborators),
                  message="COLLAB_NOT_APPROVED")

        # Execute the proposal
        self.data.proposals[proposal_id].executed = True

        with sp.if_(proposal.value.kind.is_variant("mint")):
            pass

        with sp.if_(proposal.value.kind.is_variant("swap")):
            pass


sp.add_compilation_target("Collaboration", CollaborationContract(
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    shares={sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcaa"): 1000,
            sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbcbb"): 3000,
            sp.address("tz1M9CMEtsXm3QxA7FmMU2Qh7xzsuGXVbccc"): 2000}))
