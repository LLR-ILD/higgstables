"""Read cross sections expected at ILD.

Based on the implementation at:
https://github.com/LLR-ILD/Ztau-identification/blob/4e92760a1204e0fe3a309ed2daa1f3688b8218ac/utils_llroot.py
"""
import json
import logging
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict

logger = logging.getLogger(__name__)


class CrossSectionException(Exception):
    """Wraps any exception that we expect here due to wrong user input."""

    pass


def get_polarization_weights(pol=(0.8, -0.3)):
    """Calculate the polarisation weights."""

    def is_valid_pol(p):
        return p >= -1 and p <= 1

    if len(pol) != 2 or not is_valid_pol(pol[0]) or not is_valid_pol(pol[1]):
        raise CrossSectionException(
            f"The polarisation {pol} is not understood. "
            "It should be of the same form as (0.8, -0.3)."
        )
    e, p = pol
    x = (1 + e) / 2.0
    y = (1 + p) / 2.0
    polarization_weights = {
        "eLpR": (1 - x) * y,
        "eRpL": x * (1 - y),
        "eRpR": x * y,
        "eLpL": (1 - x) * (1 - y),
    }
    return polarization_weights


class CrossSections:
    """Get process cross sections for an ILC machine scenario."""

    machine_dir = Path(__file__).parent / ".machines"
    meta_json = "genmetaByFile.json"
    get_polarization_weights = get_polarization_weights

    def __init__(self, machine: str) -> None:
        """Get process cross sections for an ILC machine scenario."""
        self._machine = machine
        self.machine_path = self.machine_dir / f"{machine}.json"

        if not self.machine_path.exists():
            if not (self.machine_dir / self.meta_json).exists():
                self._download_meta_from_web()
            self._extract_machine_cross_sections(machine)

    def per_polarization(
        self, include_exotic: bool = False
    ) -> Dict[str, Dict[str, float]]:
        """A dict with the process cross section in femtobarn.

        The form is cs[pol][process] = cs_in_fb.
        """
        assert self.machine_path.exists()
        with self.machine_path.open() as f:
            machine_meta_data_str = json.load(f)

        machine_meta_data: DefaultDict[str, Dict] = defaultdict(dict)
        for polarization in machine_meta_data_str:
            if not include_exotic:
                if polarization not in {"eLpL", "eLpR", "eRpL", "eRpR"}:
                    continue
            for process, cs_string in machine_meta_data_str[polarization].items():
                if cs_string == "":
                    cs_string = "inf"
                machine_meta_data[polarization][process] = float(cs_string)
        return machine_meta_data

    def polarization_weighted(self, polarization) -> Dict[str, Dict[str, float]]:
        weights = get_polarization_weights(polarization)
        machine_cs = self.per_polarization()
        process_cs: DefaultDict[str, Dict] = defaultdict(dict)
        for polarization in weights:
            for process in machine_cs[polarization]:
                cs = weights[polarization] * machine_cs[polarization][process]
                process_cs[polarization][process] = cs
        return process_cs

    def _download_meta_from_web(self) -> None:
        """Download/build the machine meta data file.

        Data source: https://ild.ngt.ndu.ac.jp/CDS/files/genmetaByFile.json.
        """
        self.machine_dir.mkdir(exist_ok=True)
        all_meta_path = self.machine_dir / self.meta_json
        if not all_meta_path.exists():
            logging.info(
                f"ILD simulation meta data not found at {all_meta_path}. "
                "Downloading it can take a moment..."
            )
            url = f"https://ild.ngt.ndu.ac.jp/CDS/files/{self.meta_json}"
            urllib.request.urlretrieve(url, all_meta_path)

    def _extract_machine_cross_sections(self, machine: str) -> None:
        with (self.machine_dir / self.meta_json).open() as f:
            meta_dict = json.load(f)
        machine_cs_dict: DefaultDict[str, Dict] = defaultdict(dict)
        for key, process_dict in meta_dict.items():
            entry_machine, process = key.split(".")[:2]
            if entry_machine != machine:
                continue
            polarization = "".join(key.split(".")[-4:-2])
            cross_section = process_dict["cross_section_in_fb"]
            machine_cs_dict[polarization][process] = cross_section

        if len(machine_cs_dict) == 0:
            raise CrossSectionException(
                f"The machine specification `{machine}`"
                "was not found in the lookup file. Maybe a spelling error?"
            )

        with self.machine_path.open("w") as f:
            json.dump(machine_cs_dict, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    print(CrossSections("E250-SetA").per_polarization())
    print(get_polarization_weights((0.2, -0.3)))
