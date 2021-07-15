import smartpy as sp


class PatientContract(sp.Contract):
    """This contract implements a basic patient account.

    A patient might get sick and the way to be cured is to go to their doctor
    and get some medicament.

    """

    def __init__(self, doctor):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            doctor=sp.TAddress,
            illness=sp.TOption(sp.TRecord(
                name=sp.TString,
                medicament=sp.TOption(sp.TString),
                cured=sp.TBool))))

        # Initialize the contract storage
        self.init(doctor=doctor, illness=sp.none)

    @sp.entry_point
    def get_sick(self, params):
        """The patient gets a new illness.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TString)

        # Check that the patient is not already ill
        sp.verify(
            ~self.data.illness.is_some() | self.data.illness.open_some().cured)

        # Set the patient illness
        self.data.illness = sp.some(
            sp.record(name=params, medicament=sp.none, cured=False))

    @sp.entry_point
    def get_medicament(self, params):
        """The patient gets some medicament from the doctor.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TString)

        # Make sure the medicament comes from the doctor
        sp.verify(sp.sender == self.data.doctor)

        # Update the patient illness
        name = self.data.illness.open_some().name
        self.data.illness = sp.some(
            sp.record(name=name, medicament=sp.some(params), cured=True))

    @sp.entry_point
    def visit_doctor(self):
        """The patient visits the doctor.

        """
        # Pass the illness information to the doctor and wait for the treatment
        doctor = sp.contract(
            sp.TString, self.data.doctor,
            entry_point="treat_illness").open_some()
        sp.transfer(self.data.illness.open_some().name, sp.mutez(0), doctor)


# Add a compilation target
sp.add_compilation_target("patient", PatientContract(sp.address("KT111")))
