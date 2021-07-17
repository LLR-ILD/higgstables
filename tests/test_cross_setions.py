import pytest

from higgstables.ild_specific.get_cross_sections import (
    CrossSectionException,
    CrossSections,
    get_polarization_weights,
)

valid_machines = ["E250-SetA", "E250-TDR_ws"]
invalid_machines = ["invalid", ""]


def test_polarization_weights():
    w1 = {"eLpL": 0.25, "eLpR": 0.25, "eRpL": 0.25, "eRpR": 0.25}
    assert get_polarization_weights((0, 0)) == w1

    w2 = {"eLpR": 0.14, "eRpL": 0.39, "eRpR": 0.21, "eLpL": 0.26}
    assert get_polarization_weights((0.2, -0.3)) == pytest.approx(w2)

    invalid_polarizations = [(2, 0)]
    for pol in invalid_polarizations:
        with pytest.raises(CrossSectionException):
            get_polarization_weights(pol)


def test_machine_info_loading():
    for machine in valid_machines:
        CrossSections(machine)
    for machine in invalid_machines:
        with pytest.raises(CrossSectionException):
            CrossSections(machine)


@pytest.mark.parametrize("machine", valid_machines)
def test_cross_sections(machine):
    def n_entries(cs_dict):
        return sum(len(pol_dict) for pol_dict in cs_dict.values())

    exotics_default = CrossSections(machine).per_polarization()
    include_exotics = CrossSections(machine).per_polarization(include_exotic=True)
    without_exotics = CrossSections(machine).per_polarization(include_exotic=False)

    assert exotics_default == without_exotics
    assert n_entries(include_exotics) > n_entries(without_exotics)
    assert len(include_exotics) > len(without_exotics)  # Extra polariation scenarios.


@pytest.mark.parametrize("machine", valid_machines)
def test_polarization_weighted(machine):
    unweighted = CrossSections(machine).per_polarization()
    evenly_weighted = CrossSections(machine).polarization_weighted((0, 0))

    by_hand_weighted = {polarization: {} for polarization in unweighted}
    for polarization in unweighted:
        for process, cs in unweighted[polarization].items():
            by_hand_weighted[polarization][process] = cs / 4

    polarizations = set(evenly_weighted.keys())
    polarizations.update(set(by_hand_weighted.keys()))
    for pol in polarizations:
        assert evenly_weighted[pol] == pytest.approx(by_hand_weighted[pol])
