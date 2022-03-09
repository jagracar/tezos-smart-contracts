"""Unit tests for the PatientContract class.

"""

import smartpy as sp

# Import the patientContract and the doctorContract modules
patientContract = sp.io.import_script_from_url(
    "file:python/contracts/patientContract.py")
doctorContract = sp.io.import_script_from_url(
    "file:python/contracts/doctorContract.py")


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
    c.get_sick("cold")
    scenario.verify(c.data.illness.open_some().name == "cold")
    scenario.verify(~c.data.illness.open_some().medicament.is_some())
    scenario.verify(~c.data.illness.open_some().cured)

    # Check that the patient cannot get another illness before is cured from the
    # previous one
    c.get_sick("flu").run(valid=False)


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
    c.get_sick("cold")

    # Get a medicament from the doctor to get cured
    c.get_medicament("pills").run(sender=doctor)
    scenario.verify(
        c.data.illness.open_some().medicament.open_some() == "pills")
    scenario.verify(c.data.illness.open_some().cured)

    # Check that it can only get medicaments from the doctor
    c.get_medicament("drugs").run(valid=False, sender=friend)

    # Check that it can get sick again
    scenario += c.get_sick("flu")
    scenario.verify(c.data.illness.open_some().name == "flu")
    scenario.verify(~c.data.illness.open_some().medicament.is_some())
    scenario.verify(~c.data.illness.open_some().cured)


@sp.add_test(name="Test visit doctor")
def test_visit_doctor():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Initialize the doctor contract
    doctor = doctorContract.DoctorContract()
    scenario += doctor

    # Initialize the patient contract
    patient = patientContract.PatientContract(doctor.address)
    scenario += patient

    # Make the patient sick
    illness = "headache"
    patient.get_sick(illness)
    scenario.verify(patient.data.illness.open_some().name == illness)
    scenario.verify(~patient.data.illness.open_some().medicament.is_some())
    scenario.verify(~patient.data.illness.open_some().cured)

    # Make the patient visit the doctor
    patient.visit_doctor()

    # Check that the doctor sent the correct medicament and the patient is cured
    scenario.verify(patient.data.illness.open_some().name == illness)
    scenario.verify(
        patient.data.illness.open_some().medicament.open_some() == doctor.data.medicaments[illness])
    scenario.verify(patient.data.illness.open_some().cured)
