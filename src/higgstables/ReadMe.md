# New data

## Update the data

1. The underlying data/events changed.
2. You want to try out a changed analysis (e.g. new categories).

### The underlying data/events changed

Decide on an _event-vector_ rootfile as the basis for the data.

- Produced through the `make_event_vector` part in the [Higgs-BR-classes](https://github.com/LLR-ILD/Higgs-BR-classes) project.
- Change used `.slcio` file simulation campaigns?
- Different number of events per background type / Higgs decay mode?
- Different variables to build per event?

### Change the analysis

The analysis can be changed from within this repository.
The event categories are defined in [./make_data](./make_data).

### _Warning_

As the rootfile is not tracked by the `iminuit-BRs` repository (this repository), it is not possible to change the analysis without having access to the rootfile from an external source.

It is adviced to re-run `new_data.py` after each change, to keep documentation and data in sync.

## Usage example

```bash
python3 helper/get_data/new_data.py ../Higgs-BR-classes/data/v05/simple_event_vector_njets_997k.root
```
