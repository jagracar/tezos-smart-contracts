import smartpy as sp

DEFAULT_RESCUE_TIME = 100 * 24 * 3600


class ManagerContract(sp.Contract):
    """This contract implements a basic manager account that can be used to
    manage other kind of contracts.

    The contract includes a rescue mode to solve the bus accident scenario:
    a situation where the manager dissapears and someone else needs to take
    control of the manager tasks.

    """

    def __init__(self, manager, rescue_time=DEFAULT_RESCUE_TIME):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            manager=sp.TAddress,
            rescue_time=sp.TNat,
            rescue_accounts=sp.TSet(sp.TAddress),
            last_ping=sp.TTimestamp))

        # Initialize the contract storage
        self.init(
            manager=manager,
            rescue_time=rescue_time,
            rescue_accounts=sp.set([]),
            last_ping=sp.timestamp_from_utc_now())

    def check_is_manager(self):
        """Checks that the address that called the entry point is the contract
        manager.

        """
        sp.verify(sp.sender == self.data.manager,
                  message="This can only be executed by the contract manager.")

    @sp.entry_point
    def ping(self):
        """Pings the contract to indicate that the manager is still active.

        """
        # Update the last ping time stamp
        self.check_is_manager()
        self.data.last_ping = sp.now

    @sp.entry_point
    def update_manager(self, params):
        """Updates the manager account.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Update the manager account
        self.check_is_manager()
        self.data.manager = params

    @sp.entry_point
    def add_rescue_account(self, params):
        """Adds a new account to the rescue accounts.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Add the new rescue account
        self.check_is_manager()
        self.data.rescue_accounts.add(params)

    @sp.entry_point
    def remove_rescue_account(self, params):
        """Removes an account from the rescue accounts.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Remove the rescue account
        self.check_is_manager()
        self.data.rescue_accounts.remove(params)

    @sp.entry_point
    def rescue(self):
        """Rescues the manager account when the elapsed time between now and
        the last ping from the manager account is larger than the rescue time.

        """
        # Check that the ellapsed time is larger than the rescue time
        sp.verify(
            sp.as_nat(sp.now - self.data.last_ping) > self.data.rescue_time)

        # Check that the sender is in the rescue accounts
        sp.verify(self.data.rescue_accounts.contains(sp.sender),
                  message="The sender is not in the rescue accounts.")

        # Set the sender as the new manager and update the last ping time stamp
        self.data.manager = sp.sender
        self.data.last_ping = sp.now


# Add a compilation target initialized to my tezos wallet account
sp.add_compilation_target("manager", ManagerContract(
    manager=sp.address("tz1g6JRCpsEnD2BLiAzPNK3GBD1fKicV9rCx")))
