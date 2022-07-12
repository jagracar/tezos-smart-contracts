import smartpy as sp


class CollaborativeTextContract(sp.Contract):
    """This contract implements a simple contract where users can write some
    collaborative text.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            text=sp.TBigMap(sp.TNat, sp.TString),
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            text=sp.big_map(),
            counter=0)

    @sp.entry_point
    def add_line(self, line):
        """Adds a line to the text.

        """
        # Define the input parameter data type
        sp.set_type(line, sp.TString)

        # Check that no tez have been transferred
        sp.verify(sp.amount == sp.tez(0),
                  message="The operation does not need tez transfers")

        # Add the line and increase the line counter
        self.data.text[self.data.counter] = line
        self.data.counter += 1


# Add a compilation target
sp.add_compilation_target("collaborativeText", CollaborativeTextContract())
