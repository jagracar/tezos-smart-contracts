"""Unit tests for the DoctorContract class.

"""

import smartpy as sp

# Import the patientContract and the doctorContract modules
patientContract = sp.io.import_script_from_url(
    "file:python/contracts/patientContract.py")
doctorContract = sp.io.import_script_from_url(
    "file:python/contracts/doctorContract.py")


@sp.add_test(name="Test initialization")
def test_initialization():
    # Initialize the contract
    c = doctorContract.DoctorContract()

    # Add the contract to the test scenario
    scenario = sp.test_scenario()
    scenario += c

    # Check that the information in the contract strorage is correct
    scenario.verify(sp.len(c.data.patients) == 0)
    scenario.verify(sp.len(c.data.medicaments) == 3)


@sp.add_test(name="Test treat illness")
def test_treat_illness():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Initialize the doctor contract
    doctor = doctorContract.DoctorContract()
    scenario += doctor

    # Initialize the patient contract
    patient = patientContract.PatientContract(doctor.address)
    scenario += patient

    # Make the patient sick
    illness = "flu"
    patient.get_sick(illness)

    # Treat the patient illness
    doctor.treat_illness(illness).run(sender=patient.address)

    # Check that the doctor sent the correct medicament and the patient is cured
    scenario.verify(patient.data.illness.open_some().name == illness)
    scenario.verify(
        patient.data.illness.open_some().medicament.open_some() == doctor.data.medicaments[illness])
    scenario.verify(patient.data.illness.open_some().cured)

    # Check that the patient is in the doctor patients list
    scenario.verify(doctor.data.patients.contains(patient.address))

    # Clean the doctor patients list
    doctor.clean_patients().run(sender=doctor.address)
    scenario.verify(~doctor.data.patients.contains(patient.address))
