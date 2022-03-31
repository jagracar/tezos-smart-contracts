# UPDATE

The development of the smart contracts in this repository is now taking place at the Teia Community smart contracts repository:

https://github.com/teia-community/teia-smart-contracts

Please, go there for more updated source code and unit tests.


# tezos-smart-contracts

This repository contains some Tezos smart contracts that I write at the same
time that I learn [SmartPy](https://smartpy.io). For that reason, be careful if
you decide to use them for your own projects: they could be buggy and highly
inefficient!

## SmartPy installation

```bash
wget https://smartpy.io/cli/install.sh
bash ./install.sh
rm install.sh
```

## Execute the tests

```bash
cd ~/github/tezos-smart-contracts
~/smartpy-cli/SmartPy.sh test python/tests/managerContract_test.py output/tests/managerContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/patientContract_test.py output/tests/patientContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/doctorContract_test.py output/tests/doctorContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/pingPongContract_test.py output/tests/pingPongContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/multisignWalletContract_test.py output/tests/multisignWalletContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/barterContract_test.py output/tests/barterContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/simpleBarterContract_test.py output/tests/simpleBarterContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/nonCustodialBarterContract_test.py output/tests/nonCustodialBarterContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/lambdaFunctionUtilContract_test.py output/tests/lambdaFunctionUtilsContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/fa2Contract_test.py output/tests/fa2Contract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/extendedFa2Contract_test.py output/tests/extendedFa2Contract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/minterContract_test.py output/tests/minterContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/marketplaceContract_test.py output/tests/marketplaceContract --html --purge
~/smartpy-cli/SmartPy.sh test python/tests/collaborationContract_test.py output/tests/collaborationContract --html --purge
```

## Compile the contracts

```bash
cd ~/github/tezos-smart-contracts
~/smartpy-cli/SmartPy.sh compile python/contracts/managerContract.py output/contracts/managerContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/patientContract.py output/contracts/patientContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/doctorContract.py output/contracts/doctorContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/pingPongContract.py output/contracts/pingPongContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/multisignWalletContract.py output/contracts/multisignWalletContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/barterContract.py output/contracts/barterContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/simpleBarterContract.py output/contracts/simpleBarterContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/nonCustodialBarterContract.py output/contracts/nonCustodialBarterContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/lambdaFunctionUtilContract.py output/contracts/lambdaFunctionUtilContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/fa2Contract.py output/contracts/fa2Contract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/extendedFa2Contract.py output/contracts/extendedFa2Contract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/minterContract.py output/contracts/minterContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/marketplaceContract.py output/contracts/marketplaceContract --html --purge
~/smartpy-cli/SmartPy.sh compile python/contracts/collaborationContract.py output/contracts/collaborationContract --html --purge
```
