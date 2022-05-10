# Higgstables

Create category-decay tables in the input format for `alldecays`.

As input, root files as produced in `make_event_vector` of the `Higgs-BR-classes` repository are expected.
Further information:
* Code: https://github.com/LLR-ILD/higgstables
* alldecays: https://github.com/LLR-ILD/alldecays
* Higgs-BR-classes: https://github.com/LLR-ILD/Higgs-BR-classes

## Installation

For all installation methods, the standard Github ways
of specifying the code version apply.


### pip

```sh
pip install git+https://github.com/LLR-ILD/higgstables
```

### pipx

As higgstables is designed to be used from the command line,
this is the most straight forward way for obtaining the executable.
For information on (setting up) pipx, read [their repo](https://github.com/pypa/pipx).

```sh
pipx install git+https://github.com/LLR-ILD/higgstables higgstables
```

### For development

```sh
git clone git@github.com:LLR-ILD/higgstables.git
cd higgstables
# Standard venv creation
python3 -m venv .venv --prompt $(basename $(pwd))
source .venv/bin/activate
pip install -r requirements-dev.txt
# If you are developping a local package
python -m pip install -e .
# Git commit hooks, code pushed to the repo should pass all hooks.
pre-commit install
```

## Usage example

The best way to find out about all steering options is through `higgstables --help`.

```sh
$ tree data_source
data_source/
├── eLpL
│   ├── P4f_sw_l
│   │   └── simple_event_vector.root
│   ├── P4f_sw_sl
│   │   └── simple_event_vector.root
...
├── eLpR
...
├── eLpR
...
├── eLpR
...
├── higgstables-config.yaml
└── steerer.py

$ higgstables data_source -d my_data_source_folder
```

## The configuration file

The default/example is located
[here](./src/higgstables/config/higgstables-config.yaml).
Use it as a template and adapt it to your scenario.
