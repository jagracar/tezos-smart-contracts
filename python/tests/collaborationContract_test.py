"""Unit tests for the CollaborationContract classes.

"""

import smartpy as sp

# Import the collaborationContract module
collaborationContract = sp.io.import_script_from_url(
    "file:python/contracts/collaborationContract.py")

# Import the extendedFa2Contract, minterContract and marketplaceContract modules
extendedFa2Contract = sp.io.import_script_from_url(
    "file:python/contracts/extendedFa2Contract.py")
minterContract = sp.io.import_script_from_url(
    "file:python/contracts/minterContract.py")
marketplaceContract = sp.io.import_script_from_url(
    "file:python/contracts/marketplaceContract.py")


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
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    user = sp.test_account("user")

    # Initialize the artists contracts that will receive the shares
    artist1 = RecipientContract()
    artist2 = RecipientContract()
    artist3 = RecipientContract()
    scenario += artist1
    scenario += artist2
    scenario += artist3

    # Initialize the collaboration originator contract
    originator = collaborationContract.CollabOriginatorContract(
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += originator

    # Initialize the lambda provider contract
    lambda_provider = collaborationContract.LambdaProviderContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"))
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
    scenario.verify(collab0.data.lambda_provider == lambda_provider.address)
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


@sp.add_test(name="Test lambda provider transfer and accept administrator")
def test_lambda_provider_transfer_and_accept_manager():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user = testEnvironment["user"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Check the original administrator
    scenario.verify(lambda_provider.data.administrator == admin.address)

    # Check that only the admin can transfer the administrator
    new_administrator = user.address
    lambda_provider.transfer_administrator(new_administrator).run(valid=False, sender=user)
    lambda_provider.transfer_administrator(new_administrator).run(sender=admin)

    # Check that the proposed administrator is updated
    scenario.verify(lambda_provider.data.proposed_administrator.open_some() == new_administrator)

    # Check that only the proposed administrator can accept the administrator position
    lambda_provider.accept_administrator().run(valid=False, sender=admin)
    lambda_provider.accept_administrator().run(sender=user)

    # Check that the administrator is updated
    scenario.verify(lambda_provider.data.administrator == new_administrator)
    scenario.verify(~lambda_provider.data.proposed_administrator.is_some())

    # Check that only the new administrator can propose a new administrator
    new_administrator = admin.address
    lambda_provider.transfer_administrator(new_administrator).run(valid=False, sender=admin)
    lambda_provider.transfer_administrator(new_administrator).run(sender=user)

    # Check that the proposed administrator is updated
    scenario.verify(lambda_provider.data.proposed_administrator.open_some() == new_administrator)


@sp.add_test(name="Test lambda provider add lambda")
def test_lambda_provider_add_lambda():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user = testEnvironment["user"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Initialize the dummy contract and add it to the test scenario
    dummyContract = DummyContract()
    scenario += dummyContract

    # Define the lambda functions that will update the dummy contract
    def update_x_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        new_x = sp.unpack(params, t=sp.TNat).open_some()
        dummyContractHandle = sp.contract(sp.TNat, dummyContract.address, "update_x").open_some()
        sp.result([sp.transfer_operation(new_x, sp.mutez(0), dummyContractHandle)])

    def update_y_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        new_y = sp.unpack(params, t=sp.TNat).open_some()
        dummyContractHandle = sp.contract(sp.TNat, dummyContract.address, "update_y").open_some()
        sp.result([sp.transfer_operation(new_y, sp.mutez(0), dummyContractHandle)])

    # Check that only the admin can add lambdas
    lambda_provider.add_lambda(sp.record(
        lambda_id=0,
        alias="update x",
        lambda_function=update_x_lambda_function)).run(valid=False, sender=user)
    lambda_provider.add_lambda(sp.record(
        lambda_id=0,
        alias="update x",
        lambda_function=update_x_lambda_function)).run(sender=admin)

    # Check that the contract information is correct
    scenario.verify(lambda_provider.data.lambdas.contains(0))
    scenario.verify(lambda_provider.has_lambda(0))
    scenario.verify(lambda_provider.data.lambdas[0].enabled)
    scenario.verify(lambda_provider.data.lambdas[0].alias == "update x")

    # Check that it's not possible to write over a previous lambda
    lambda_provider.add_lambda(sp.record(
        lambda_id=0,
        alias="update y",
        lambda_function=update_y_lambda_function)).run(valid=False, sender=admin)
    lambda_provider.add_lambda(sp.record(
        lambda_id=100,
        alias="update y",
        lambda_function=update_y_lambda_function)).run(sender=admin)

    # Check that the contract information is correct
    scenario.verify(lambda_provider.data.lambdas.contains(0))
    scenario.verify(lambda_provider.has_lambda(0))
    scenario.verify(lambda_provider.data.lambdas[0].enabled)
    scenario.verify(lambda_provider.data.lambdas[0].alias == "update x")
    scenario.verify(lambda_provider.data.lambdas.contains(100))
    scenario.verify(lambda_provider.has_lambda(100))
    scenario.verify(lambda_provider.data.lambdas[100].enabled)
    scenario.verify(lambda_provider.data.lambdas[100].alias == "update y")


@sp.add_test(name="Test collaboration")
def test_collaboration():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user = testEnvironment["user"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    artist3 = testEnvironment["artist3"]
    originator = testEnvironment["originator"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Initialize the dummy contract and add it to the test scenario
    dummyContract = DummyContract()
    scenario += dummyContract

    # Define the lambda function that will update the dummy contract
    def update_x_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        new_x = sp.unpack(params, t=sp.TNat).open_some()
        dummyContractHandle = sp.contract(sp.TNat, dummyContract.address, "update_x").open_some()
        sp.result([sp.transfer_operation(new_x, sp.mutez(0), dummyContractHandle)])

    # Add the lambda to the lambda provider
    lambda_provider.add_lambda(sp.record(
        lambda_id=200,
        alias="update x",
        lambda_function=update_x_lambda_function)).run(sender=admin)

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

    # Check that only collaborators can add proposals
    collaboration.call("add_proposal", sp.record(
        lambda_id=200,
        parameters=sp.pack(sp.nat(100)))).run(valid=False, sender=user)

    # Check that it fails if the lambda id doesn't exist
    collaboration.call("add_proposal", sp.record(
        lambda_id=199,
        parameters=sp.pack(sp.nat(100)))).run(valid=False, sender=artist1.address)

    # Add a proposal
    collaboration.call("add_proposal", sp.record(
        lambda_id=200,
        parameters=sp.pack(sp.nat(100)))).run(sender=artist1.address)

    # Check that the contract information is correct
    scenario.verify(collaboration.data.proposals.contains(0))
    scenario.verify(~collaboration.data.proposals[0].executed)
    scenario.verify(collaboration.data.proposals[0].approvals == 1)
    scenario.verify(collaboration.data.proposals[0].lambda_id == 200)
    scenario.verify(collaboration.data.proposals[0].parameters == sp.pack(sp.nat(100)))
    scenario.verify(collaboration.data.approvals[(0, artist1.address)] == True)

    # Check that it's not possible to execute the proposal without the other
    # collaborator approvals
    collaboration.call("execute_proposal", sp.nat(0)).run(valid=False, sender=artist1.address)

    # The other collaborators approve the proposal
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(sender=artist2.address)
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(sender=artist3.address)

    # Check that the contract information is correct
    scenario.verify(~collaboration.data.proposals[0].executed)
    scenario.verify(collaboration.data.proposals[0].approvals == 3)
    scenario.verify(collaboration.data.approvals[(0, artist1.address)] == True)
    scenario.verify(collaboration.data.approvals[(0, artist2.address)] == True)
    scenario.verify(collaboration.data.approvals[(0, artist3.address)] == True)

    # Check that only collaborators can approve proposals
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(valid=False, sender=user)

    # The second collaborator changes their mind
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=False)).run(sender=artist2.address)

    # Check that the contract information is correct
    scenario.verify(~collaboration.data.proposals[0].executed)
    scenario.verify(collaboration.data.proposals[0].approvals == 2)
    scenario.verify(collaboration.data.approvals[(0, artist1.address)] == True)
    scenario.verify(collaboration.data.approvals[(0, artist2.address)] == False)
    scenario.verify(collaboration.data.approvals[(0, artist3.address)] == True)

    # Check that it's not possible to execute the proposal
    collaboration.call("execute_proposal", sp.nat(0)).run(valid=False, sender=artist1.address)

    # The second collaborator approves the proposal again
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(sender=artist2.address)

    # Check that only collaborators can execute the proposal
    collaboration.call("execute_proposal", sp.nat(0)).run(valid=False, sender=user)

    # The third collaborator executes the proposal
    collaboration.call("execute_proposal", sp.nat(0)).run(sender=artist3.address)

    # Check that the contract information is correct
    scenario.verify(collaboration.data.proposals[0].executed)
    scenario.verify(collaboration.data.proposals[0].approvals == 3)
    scenario.verify(collaboration.data.approvals[(0, artist1.address)] == True)
    scenario.verify(collaboration.data.approvals[(0, artist2.address)] == True)
    scenario.verify(collaboration.data.approvals[(0, artist3.address)] == True)

    # Check that the dummy contract has been updated
    scenario.verify(dummyContract.data.x == 100)

    # Check that it's not possible to execute the proposal twice or change a
    # collaborator approval
    collaboration.call("execute_proposal", sp.nat(0)).run(valid=False, sender=artist3.address)
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=False)).run(valid=False, sender=artist2.address)

    # Add anoter proposal
    lambda_provider.add_lambda(sp.record(
        lambda_id=2,
        alias="second update x",
        lambda_function=update_x_lambda_function)).run(sender=admin)
    collaboration.call("add_proposal", sp.record(
        lambda_id=2,
        parameters=sp.pack(sp.nat(150)))).run(sender=artist2.address)

    # Check that the proposal can be exectuded with a single approval
    collaboration.call("execute_proposal", sp.nat(1)).run(sender=artist3.address)

    # Check that the contract information is correct
    scenario.verify(collaboration.data.proposals[1].executed)
    scenario.verify(collaboration.data.proposals[1].approvals == 1)
    scenario.verify(~collaboration.data.approvals.contains((1, artist1.address)))
    scenario.verify(collaboration.data.approvals[(1, artist2.address)] == True)
    scenario.verify(~collaboration.data.approvals.contains((1, artist3.address)))

    # Check that the dummy contract has been updated
    scenario.verify(dummyContract.data.x == 150)


@sp.add_test(name="Test full example")
def test_full_example():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    user = testEnvironment["user"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    artist3 = testEnvironment["artist3"]
    originator = testEnvironment["originator"]
    lambda_provider = testEnvironment["lambda_provider"]

    # Initialize the extended FA2 contract
    fa2 = extendedFa2Contract.FA2(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"))
    scenario += fa2

    # Initialize the minter contract
    minter = minterContract.MinterContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://bbb"),
        fa2=fa2.address)
    scenario += minter

    # Initialize the marketplace contract
    marketplace = marketplaceContract.MarketplaceContract(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        fa2=fa2.address,
        fee=sp.nat(25))
    scenario += marketplace

    # Set the minter contract as the admin of the FA2 contract
    fa2.transfer_administrator(minter.address).run(sender=admin)
    minter.accept_fa2_administrator().run(sender=admin)

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

    # Define the lambda functions for minting and swapping
    mint_params_type = sp.TRecord(
        editions=sp.TNat,
        metadata=sp.TMap(sp.TString, sp.TBytes),
        data=sp.TMap(sp.TString, sp.TBytes),
        royalties=sp.TNat).layout(
            ("editions", ("metadata", ("data", "royalties")))) 
    operators_params_type = sp.TList(sp.TVariant(
        add_operator=extendedFa2Contract.FA2.OPERATOR_KEY_TYPE,
        remove_operator=extendedFa2Contract.FA2.OPERATOR_KEY_TYPE))
    swap_params_type = sp.TRecord(
        token_id=sp.TNat,
        editions=sp.TNat,
        price=sp.TMutez,
        donations=sp.TList(
            marketplaceContract.MarketplaceContract.ORG_DONATION_TYPE)).layout(
                ("token_id", ("editions", ("price", "donations"))))
    combined_params_type = sp.TRecord(
        owner=sp.TAddress,
        swap_params=swap_params_type).layout(
            ("owner", "swap_params"))

    def cancel_swap_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        cancel_swap_params = sp.unpack(params, t=sp.TNat).open_some()
        marketplaceHandle = sp.contract(sp.TNat, marketplace.address, "cancel_swap").open_some()
        sp.result([sp.transfer_operation(cancel_swap_params, sp.mutez(0), marketplaceHandle)])

    def mint_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        mint_params = sp.unpack(params, t=mint_params_type).open_some()
        minterHandle = sp.contract(mint_params_type, minter.address, "mint").open_some()
        sp.result([sp.transfer_operation(mint_params, sp.mutez(0), minterHandle)])

    def swap_lambda_function(params):
        sp.set_type(params, sp.TBytes)
        params = sp.unpack(params, t=combined_params_type).open_some()
        add_operator_params = [sp.variant("add_operator", sp.record(
            owner=params.owner,
            operator=marketplace.address,
            token_id=params.swap_params.token_id))]
        remove_operator_params = [sp.variant("remove_operator", sp.record(
            owner=params.owner,
            operator=marketplace.address,
            token_id=params.swap_params.token_id))]
        fa2Handle = sp.contract(operators_params_type, fa2.address, "update_operators").open_some()
        marketplaceHandle = sp.contract(swap_params_type, marketplace.address, "swap").open_some()
        sp.result([
            sp.transfer_operation(add_operator_params, sp.mutez(0), fa2Handle),
            sp.transfer_operation(params.swap_params, sp.mutez(0), marketplaceHandle),
            sp.transfer_operation(remove_operator_params, sp.mutez(0), fa2Handle)
        ])

    # Add the lambdas to the lambda provider
    lambda_provider.add_lambda(sp.record(
        lambda_id=0,
        alias="cancel_swap",
        lambda_function=cancel_swap_lambda_function)).run(sender=admin)
    lambda_provider.add_lambda(sp.record(
        lambda_id=100,
        alias="mint",
        lambda_function=mint_lambda_function)).run(sender=admin)
    lambda_provider.add_lambda(sp.record(
        lambda_id=101,
        alias="swap",
        lambda_function=swap_lambda_function)).run(sender=admin)

    # Add a proposal to mint a token
    minted_editions = 100
    mint_parameters = sp.set_type_expr(
        sp.record(
            editions=minted_editions,
            metadata={"": sp.utils.bytes_of_string("ipfs://fff")},
            data={},
            royalties=200),
        t=mint_params_type)
    collaboration.call("add_proposal", sp.record(
        lambda_id=100,
        parameters=sp.pack(mint_parameters))).run(sender=artist1.address)

    # The other collaborators approve the proposal
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(sender=artist2.address)
    collaboration.call("approve", sp.record(
        proposal_id=0,
        approval=True)).run(sender=artist3.address)

    # Execute the mint proposal
    collaboration.call("execute_proposal", sp.nat(0)).run(sender=artist1.address)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(collaboration.address, 0)] == minted_editions)
    scenario.verify(fa2.data.token_metadata[0].token_info[""] == mint_parameters.metadata[""])
    scenario.verify(sp.len(fa2.data.token_data[0]) == 0)
    scenario.verify(fa2.data.token_royalties[0].minter.address == collaboration.address)
    scenario.verify(fa2.data.token_royalties[0].minter.royalties == 0)
    scenario.verify(fa2.data.token_royalties[0].creator.address == collaboration.address)
    scenario.verify(fa2.data.token_royalties[0].creator.royalties == mint_parameters.royalties)

    # Add a proposal to swap the token
    swapped_editions = 50
    price = sp.mutez(10000)
    swap_parameters = sp.set_type_expr(
        sp.record(
            owner=collaboration.address,
            swap_params=sp.record(
                token_id=0,
                editions=swapped_editions,
                price=price,
                donations=[])),
        t=combined_params_type)
    collaboration.call("add_proposal", sp.record(
        lambda_id=101,
        parameters=sp.pack(swap_parameters))).run(sender=artist2.address)

    # The other collaborators approve the proposal
    collaboration.call("approve", sp.record(
        proposal_id=1,
        approval=True)).run(sender=artist1.address)
    collaboration.call("approve", sp.record(
        proposal_id=1,
        approval=True)).run(sender=artist3.address)

    # Execute the swap proposal
    collaboration.call("execute_proposal", sp.nat(1)).run(sender=artist2.address)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(collaboration.address, 0)] == minted_editions - swapped_editions)
    scenario.verify(fa2.data.ledger[(marketplace.address, 0)] == swapped_editions)

    # Check that the swaps big map is correct
    scenario.verify(marketplace.data.swaps.contains(0))
    scenario.verify(marketplace.data.swaps[0].issuer == collaboration.address)
    scenario.verify(marketplace.data.swaps[0].token_id == 0)
    scenario.verify(marketplace.data.swaps[0].editions == swapped_editions)
    scenario.verify(marketplace.data.swaps[0].price == price)
    scenario.verify(sp.len(marketplace.data.swaps[0].donations) == 0)
    scenario.verify(marketplace.data.counter == 1)

    # Collect the token
    marketplace.collect(0).run(sender=user, amount=price)

    # Check that the tez arrived to the collaboration
    received_tez = price - sp.split_tokens(price, 25, 1000)
    scenario.verify(collaboration.balance == received_tez)

    # Transfer the funds
    collaboration.call("transfer_funds", sp.unit).run(sender=artist1.address)

    # Check that all the funds have been transferred
    scenario.verify(collaboration.balance == sp.mutez(0))
    scenario.verify(artist1.balance - sp.split_tokens(received_tez, 200, 1000) <= sp.mutez(1))
    scenario.verify(artist2.balance - sp.split_tokens(received_tez, 500, 1000) <= sp.mutez(1))
    scenario.verify(artist3.balance - sp.split_tokens(received_tez, 300, 1000) <= sp.mutez(1))
    scenario.verify(received_tez == (artist1.balance + artist2.balance + artist3.balance))

    # Add a proposal to cancel the swap
    collaboration.call("add_proposal", sp.record(
        lambda_id=0,
        parameters=sp.pack(sp.nat(0)))).run(sender=artist2.address)

    # Execute the swap proposal
    collaboration.call("execute_proposal", sp.nat(2)).run(sender=artist3.address)

    # Check that the FA2 contract information has been updated
    scenario.verify(fa2.data.ledger[(collaboration.address, 0)] == minted_editions - 1)
    scenario.verify(fa2.data.ledger[(marketplace.address, 0)] == 0)

    # Check that the swaps big map is correct
    scenario.verify(~marketplace.data.swaps.contains(0))
    scenario.verify(marketplace.data.counter == 1)
