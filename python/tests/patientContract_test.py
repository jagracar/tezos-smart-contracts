"""Unit tests for the PatientContract class.

"""

import smartpy as sp

# Import the patientContract module
patientContract = sp.io.import_script_from_url(
    "file:python/contracts/patientContract.py")


@sp.add_test(name="Test initialization")
def test_initialization():
    # Define the doctor account
    doctor = sp.test_account("doctor")

    # Initialize the contract
    c = patientContract.PatientContract(doctor.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Check that the information in the contract strorage is correct
    scenario.verify(c.data.doctor == doctor.address)
    scenario.verify(~c.data.illness.is_some())


@sp.add_test(name="Test get sick")
def test_get_sick():
    # Define the doctor account
    doctor = sp.test_account("doctor")

    # Initialize the contract
    c = patientContract.PatientContract(doctor.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Make the patient sick
    scenario += c.get_sick("cold")
    scenario.verify(c.data.illness.open_some().name == "cold")
    scenario.verify(~c.data.illness.open_some().medicament.is_some())
    scenario.verify(~c.data.illness.open_some().cured)

    # Check that the patient cannot get another illness before is cured from the
    # previous one
    scenario += c.get_sick("flu").run(valid=False)


@sp.add_test(name="Test get medicament")
def test_get_medicament():
    # Define the test accounts
    doctor = sp.test_account("doctor")
    friend = sp.test_account("friend")

    # Initialize the contract
    c = patientContract.PatientContract(doctor.address)

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Make the patient sick
    scenario += c.get_sick("cold")

    # Get a medicament from the doctor to get cured
    scenario += c.get_medicament("pills").run(sender=doctor)
    scenario.verify(
        c.data.illness.open_some().medicament.open_some() == "pills")
    scenario.verify(c.data.illness.open_some().cured)

    # Check that it can only get medicaments from the doctor
    scenario += c.get_medicament("drugs").run(valid=False, sender=friend)

    # Check that it can get sick again
    scenario += c.get_sick("flu")
    scenario.verify(c.data.illness.open_some().name == "flu")
    scenario.verify(~c.data.illness.open_some().medicament.is_some())
    scenario.verify(~c.data.illness.open_some().cured)
