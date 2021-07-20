# tezos-smart-contracts

This repository contains some Tezos smart contracts that I write at the same
time that I learn [SmartPy](https://smartpy.io). For that reason, be careful if
you decide to use them for your own projects: they could be buggy and highly
inefficient!

## SmartPy installation

```bash
wget https://smartpy.io/cli/install.sh
bash ./install.sh local-install ~/admin/smartpy
rm install.sh
```

## Execute the tests

```bash
cd ~/github/tezos-smart-contracts
~/admin/smartpy/SmartPy.sh test python/tests/managerContract_test.py output/tests/managerContract --html --purge
~/admin/smartpy/SmartPy.sh test python/tests/patientContract_test.py output/tests/patientContract --html --purge
~/admin/smartpy/SmartPy.sh test python/tests/doctorContract_test.py output/tests/doctorContract --html --purge
~/admin/smartpy/SmartPy.sh test python/tests/pingPongContract_test.py output/tests/pingPongContract --html --purge
```

## Compile the contracts

```bash
cd ~/github/tezos-smart-contracts
~/admin/smartpy/SmartPy.sh compile python/contracts/managerContract.py output/contracts/managerContract --html --purge
~/admin/smartpy/SmartPy.sh compile python/contracts/patientContract.py output/contracts/patientContract --html --purge
~/admin/smartpy/SmartPy.sh compile python/contracts/doctorContract.py output/contracts/doctorContract --html --purge
~/admin/smartpy/SmartPy.sh compile python/contracts/pingPongContract.py output/contracts/pingPongContract --html --purge
```
