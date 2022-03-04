"""Unit tests for the ManagerContract class.

"""

import smartpy as sp

# Import the managerContract module
managerContract = sp.io.import_script_from_url(
    "file:python/contracts/managerContract.py")


@sp.add_test(name="Test default initialization")
def test_default_initialization():
    # Define the test account
    user = sp.test_account("user")

    # Initialize the contract
    c = managerContract.ManagerContract(user.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Check that the information in the contract strorage is correct
    scenario.verify(c.data.manager == user.address)
    scenario.verify(c.data.rescue_time == managerContract.DEFAULT_RESCUE_TIME)
    scenario.verify(sp.len(c.data.rescue_accounts) == 0)
    scenario.verify(
        sp.as_nat(sp.timestamp_from_utc_now() - c.data.last_ping) == 0)


@sp.add_test(name="Test initialization with rescue time")
def test_initialization_with_rescue_time():
    # Define the test account
    user = sp.test_account("user")

    # Initialize the contract
    rescue_time = 1000
    c = managerContract.ManagerContract(user.address, rescue_time)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Check that the rescue time is correct
    scenario.verify(c.data.rescue_time == rescue_time)


@sp.add_test(name="Test ping")
def test_ping():
    # Define the test accounts
    user_1 = sp.test_account("user_1")
    user_2 = sp.test_account("user_2")

    # Initialize the contract
    c = managerContract.ManagerContract(user_1.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Ping the contract with the manager account
    c.ping().run(sender=user_1, now=sp.timestamp(1000))
    scenario.verify(c.data.last_ping == sp.timestamp(1000))

    # Check that the ping will fail if it's not executed by the manager account
    c.ping().run(valid=False, sender=user_2, now=sp.timestamp(2000))


@sp.add_test(name="Test update manager")
def test_update_manager():
    # Define the test accounts
    user_1 = sp.test_account("user_1")
    user_2 = sp.test_account("user_2")

    # Initialize the contract
    c = managerContract.ManagerContract(user_1.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Set user 2 as the new manager
    c.update_manager(user_2.address).run(sender=user_1)
    scenario.verify(c.data.manager == user_2.address)

    # Check that user 1 cannot update the manager anymore
    c.update_manager(user_1.address).run(valid=False, sender=user_1)
    scenario.verify(c.data.manager == user_2.address)


@sp.add_test(name="Test update rescue accounts")
def test_update_manager():
    # Define the test accounts
    user_1 = sp.test_account("user_1")
    user_2 = sp.test_account("user_2")
    user_3 = sp.test_account("user_3")

    # Initialize the contract
    c = managerContract.ManagerContract(user_1.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Add user 2 to the rescue accounts
    c.add_rescue_account(user_2.address).run(sender=user_1)
    scenario.verify(c.data.rescue_accounts.contains(user_2.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 1)

    # Add user 3 to the rescue accounts
    c.add_rescue_account(user_3.address).run(sender=user_1)
    scenario.verify(c.data.rescue_accounts.contains(user_2.address))
    scenario.verify(c.data.rescue_accounts.contains(user_3.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 2)

    # Add user 1 to the rescue accounts
    c.add_rescue_account(user_1.address).run(sender=user_1)
    scenario.verify(c.data.rescue_accounts.contains(user_1.address))
    scenario.verify(c.data.rescue_accounts.contains(user_2.address))
    scenario.verify(c.data.rescue_accounts.contains(user_3.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 3)

    # Remove user 2 from the rescue accounts
    c.remove_rescue_account(user_2.address).run(sender=user_1)
    scenario.verify(c.data.rescue_accounts.contains(user_1.address))
    scenario.verify(~c.data.rescue_accounts.contains(user_2.address))
    scenario.verify(c.data.rescue_accounts.contains(user_3.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 2)

    # Check that only the manager can add or remove rescue accounts
    c.add_rescue_account(user_2.address).run(valid=False, sender=user_3)
    c.remove_rescue_account(user_1.address).run(valid=False, sender=user_3)
    scenario.verify(c.data.rescue_accounts.contains(user_1.address))
    scenario.verify(c.data.rescue_accounts.contains(user_3.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 2)


@sp.add_test(name="Test rescue mode")
def test_update_manager():
    # Define the test accounts
    user_1 = sp.test_account("user_1")
    user_2 = sp.test_account("user_2")
    user_3 = sp.test_account("user_3")

    # Initialize the contract
    c = managerContract.ManagerContract(user_1.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Add user 2 to the rescue accounts
    c.add_rescue_account(user_2.address).run(sender=user_1)
    scenario.verify(c.data.rescue_accounts.contains(user_2.address))
    scenario.verify(sp.len(c.data.rescue_accounts) == 1)

    # Ping the contract
    ping_time = sp.timestamp(1000)
    c.ping().run(sender=user_1, now=ping_time)

    # Check that the rescue mode cannot be run before the rescue time has passed
    ellapsed_time = managerContract.DEFAULT_RESCUE_TIME - 10
    c.rescue().run(valid=False, sender=user_2, now=ping_time.add_seconds(ellapsed_time))
    scenario.verify(c.data.manager == user_1.address)

    # Check that the rescue mode only works for users inside the rescue accounts
    ellapsed_time = managerContract.DEFAULT_RESCUE_TIME + 10
    c.rescue().run(valid=False, sender=user_3, now=ping_time.add_seconds(ellapsed_time))
    c.rescue().run(sender=user_2, now=ping_time.add_seconds(ellapsed_time))
    scenario.verify(c.data.manager == user_2.address)
    scenario.verify(c.data.last_ping == ping_time.add_seconds(ellapsed_time))

    # Check that the old manager lost its manager rights
    c.update_manager(user_1.address).run(valid=False, sender=user_1)
    scenario.verify(c.data.manager == user_2.address)
