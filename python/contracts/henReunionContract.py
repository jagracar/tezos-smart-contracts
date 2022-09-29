import smartpy as sp


class HenReunionContract(sp.Contract):
    """This contract implements a simple contract where users can sign for the
    #henreunion event.

    """

    def __init__(self, metadata, end_party):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract metadata
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The timestamp when the party ends
            end_party=sp.TTimestamp,
            # The participants bigmap
            participants=sp.TBigMap(sp.TAddress, sp.TUnit)))

        # Initialize the contract storage
        self.init(
            metadata=metadata,
            end_party=end_party,
            participants=sp.big_map())

    @sp.entry_point
    def default(self, unit):
        """Don't allow any tez transactions.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Check that the user didn't send anytez
        sp.verify(sp.amount == sp.mutez(0), message="The party is free!")

    @sp.entry_point
    def go_to_the_kitchen(self, unit):
        """You didn't join a party if you didn't visit the kitchen.

        """
        # Define the input parameter data type
        sp.set_type(unit, sp.TUnit)

        # Check that the user didn't send anytez
        sp.verify(sp.amount == sp.mutez(0), message="The party is free!")

        # Check that the party didn't finish
        sp.verify(sp.now < self.data.end_party,
                  message="Someone called the police and the party is finished :(")

        # Check that the user didn't sign up yet
        sp.verify(~self.data.participants.contains(sp.sender),
                  message="You already joined the party! Are you drunk?")

        # Add the new participant
        self.data.participants[sp.sender] = sp.unit

    @sp.onchain_view(pure=True)
    def attended(self, user_address):
        """Returns True if the user address attended the party.

        """
        # Define the input parameter data type
        sp.set_type(user_address, sp.TAddress)

        # Return True if the user attended the party 
        sp.result(self.data.participants.contains(user_address))


# Add a compilation target
sp.add_compilation_target("henreunionContract", HenReunionContract(
    metadata=sp.utils.metadata_of_url("ipfs://QmadaqKUJyV9fJS9fhEbEC3uQUK5Tz995quGrnwMFqLmzf"),
    end_party=sp.timestamp_from_utc(2022, 10, 3, 12, 0, 0)))
