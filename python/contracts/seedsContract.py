import smartpy as sp


class SeedsContract(sp.Contract):
    """This contract implements a simple contract where users can name their
    own random seeds.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            seeds=sp.TBigMap(sp.TNat, sp.TString)))

        # Initialize the contract storage
        self.init(seeds=sp.big_map({42: "The answer to everything"}))

    @sp.entry_point
    def name_seed(self, params):
        """Names a seed.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            seed=sp.TNat,
            name=sp.TString).layout(("seed", "name")))

        # Check that the seeds doesn't have already a name
        sp.verify(~self.data.seeds.contains(params.seed),
                  message="The seed already has a name")

        # Check that the name is not too long
        sp.verify(sp.len(params.name) <= 64,
                  message="The name cannot be longer than 64 characters")

        # Check that no tez have been transferred
        sp.verify(sp.amount == sp.tez(0),
                  message="The operation does not need tez transfers")

        # Add the new seed
        self.data.seeds[params.seed] = params.name


# Add a compilation target
sp.add_compilation_target("seedsContract", SeedsContract())
