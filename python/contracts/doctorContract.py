import smartpy as sp


class DoctorContract(sp.Contract):
    """This contract implements a basic doctor account.

    The doctor treats their patient's illnesses prescribing them the
    appropriate medicaments.

    """

    def __init__(self):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            patients=sp.TSet(sp.TAddress),
            medicaments=sp.TMap(sp.TString, sp.TString)))

        # Initialize the contract storage
        self.init(
            patients=sp.set([]),
            medicaments={
            "cold": "med1",
            "flu": "med2",
            "headache": "med3"})

    @sp.entry_point
    def clean_patients(self):
        """Cleans the list of patients.

        """
        sp.verify(sp.sender == sp.self_address)
        self.data.patients = sp.set([])

    @sp.entry_point
    def treat_illness(self, params):
        """Treats the patient illness.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TString)

        # Check that it knows a medicament for the patient illness
        sp.verify(self.data.medicaments.contains(params))

        # Add the patient to the patients list
        self.data.patients.add(sp.sender)

        # Prescribe the medicaments to the patient
        patient = sp.contract(
            sp.TString, sp.sender,
            entry_point="get_medicament").open_some()
        sp.transfer(self.data.medicaments[params], sp.mutez(0), patient)


# Add a compilation target
sp.add_compilation_target("doctor", DoctorContract())
