"""This module is loaded in the `ZH` and `scratches/z_from_tau_notebooks`
projects. Be sure to propagate any changes of the interface to those modules.
"""
import collections
import json
import numpy
from pathlib import Path
import uproot
import urllib.request

polarisations = ["eLpR", "eRpL", "eLpL", "eRpR"]

def pol_proc_structure(dir_name):
    """Check wether the given path name is the head of file structure in the
    form that I expect in my projects. Returns True/False.
    """
    data_dir = Path(dir_name)
    # Is a directory.
    if not data_dir.is_dir():
        return False
    # Contains only polarisations as folders.
    if numpy.any([dir_entry.name not in polarisations and dir_entry.is_dir()
                      for dir_entry in data_dir.iterdir()]):
        return False
    # There are only folders inside the polarisation folders.
    pol_directories = [d for d in data_dir.iterdir() if d.is_dir()]
    for pol_dir in pol_directories:
        if numpy.any([not proc_dir.is_dir() for proc_dir in pol_dir.iterdir()]):
            return False
    # Inside all of these folders there are .root files of exactly the same name
    # and no further directories.
    a_proc_dir = next(next(data_dir.iterdir()).iterdir())
    required_root_file_names = set([f.name for f in a_proc_dir.glob("*.root")])
    for pol_dir in pol_directories:
        for proc_dir in pol_dir.iterdir():
            root_file_names = set([f.name for f in proc_dir.glob("*.root")])
            if root_file_names != required_root_file_names:
                return False
            if numpy.any([per_proc.is_dir()
                             for per_proc in proc_dir.iterdir()]):
                return False
    return True

def getPolarisationWeigths(pol=(.8,-.3)):
    # Calculate the polarisation weights.
    valid_pol = lambda p: p >= -1 and p <= 1
    if len(pol) != 2 or not valid_pol(pol[0]) or not valid_pol(pol[1]):
        raise Exception(f"The polarisation {pol} is not understood. Should be "
            "of the same form as (.8,.3).")
    e, p = pol
    pol_weight = {
        "eLpR": (1 - (1+e)/2.) *      (1+p)/2.,
        "eRpL":      (1+e)/2.  * (1 - (1+p)/2.),
        "eRpR":      (1+e)/2.  *      (1+p)/2.,
        "eLpL": (1 - (1+e)/2.) * (1 - (1+p)/2.),
    }
    return pol_weight

def getPerPolarisationCS(machine):
    """A dict with the process cross section in femtobarn.

    The form is cs[pol][process] = cs_in_fb.
    Data source: https://ild.ngt.ndu.ac.jp/CDS/files/genmetaByFile.json.
    """
    # Get the cross sections per polarisation.
    cs_json_path = Path(__file__).parent / f"{machine}.json"
    if not cs_json_path.exists():
        genmeta_json = Path(__file__).parent / "genmetaByFile.json"
        if not genmeta_json.exists():
            # We need to download the metadata file from the web.
            url = "https://ild.ngt.ndu.ac.jp/CDS/files/genmetaByFile.json"
            urllib.request.urlretrieve(url, genmeta_json)
        with genmeta_json.open() as f:
            meta_dict = json.load(f)
        machine_cs_dict = collections.defaultdict(dict)
        for key, proc_d in meta_dict.items():
            if machine in key:
                pol = f"e{proc_d['polarization1']}p{proc_d['polarization2']}"
                if pol not in polarisations:
                    continue # We only use th 4 pure e/p polarisation states.
                if 'process_name' not in proc_d.keys():
                    continue # Not all entries have the process_name key. Here
                    # we assume that all those that interest us do have it
                    # (all standard process types).
                proc = "P" + proc_d['process_name']
                if proc in machine_cs_dict[pol]:
                    # This hacky part could be removed by going for process_type
                    # instead of process_name. But then we get the long names
                    # for the 2f/4f types -> inconvenient.
                    if proc_d['process_name'] != proc_d['process_type']:
                        continue
                # Instead of Pffh we use the split up version Pe1e1h, ...
                if proc == "Pffh":
                    continue
                machine_cs_dict[pol][proc] = proc_d['cross_section_in_fb']
        if not machine_cs_dict:
            raise Exception(f"The machine specification `{machine}` was not "
                "found in the lookup file. Maybe a spelling error?")
        with cs_json_path.open("w") as f:
            json.dump(machine_cs_dict, f, indent=4, sort_keys=True)
    else:
        with cs_json_path.open() as f:
            machine_cs_dict = json.load(f)
    return machine_cs_dict

def getPolarisationWeightedCS(pol=(.8,-.3), machine="E250-TDR_ws"):
    pol_weight = getPolarisationWeigths(pol)
    machine_cs_dict = getPerPolarisationCS(machine)
    # Scale the cross sections to the desired polarisation scenario.
    process_cs = {}
    for pol, processes in machine_cs_dict.items():
        process_cs[pol] = {}
        for cs_key in processes.keys():
            process_cs[pol][cs_key] = pol_weight[pol] * float(processes[cs_key])
    return process_cs

process_grouping_key_phrases = ["Higgs only", "SM 250", "SM 250 Higgs blown up"]
SM250_dict = {
    "P2f_z_bhabhag": "P2f", "P2f_z_h": "P2f", "P2f_z_l": "P2f",
    "P4f_sw_l": "P4f_l", "P4f_sze_l": "P4f_l", "P4f_szeorsw_l": "P4f_l",
        "P4f_sznu_l": "P4f_l", "P4f_ww_l": "P4f_l", "P4f_zz_l": "P4f_l",
        "P4f_zzorww_l": "P4f_l",
    "P4f_sw_sl": "P4f_sl", "P4f_sze_sl": "P4f_sl", "P4f_sznu_sl": "P4f_sl",
        "P4f_ww_sl": "P4f_sl", "P4f_zz_sl": "P4f_sl",
    "P4f_ww_h": "P4f_h", "P4f_zz_h": "P4f_h", "P4f_zzorww_h": "P4f_h",
    "Pqqh": "Pffh", "Pnnh": "Pffh", "Pe1e1h": "Pffh", "Pe2e2h": "Pffh",
        "Pe3e3h": "Pffh"
}
def process_grouping_function(key_phrase):
    """Collection of grouping function.

    In order to have a cleaner plot, the many different process categories
    should be combined into a smaller number. The grouping function is selected
    by key_phrase. The functions that are returned take a string and return
    either a new string (the name of the group), or None. None is expected to be
    useful to indicate that a process should not be used.
    """
    if key_phrase == "Higgs only":
        pdict = {p: p for p in ["Pqqh", "Pnnh", "Pe1e1h", "Pe2e2h", "Pe3e3h"]}
    elif key_phrase == "SM 250":
        pdict = SM250_dict
    elif key_phrase == "SM 250 Higgs blown up":
        pdict = SM250_dict
        for higgs in ["Pqqh", "Pnnh", "Pe1e1h", "Pe2e2h", "Pe3e3h"]:
            pdict[higgs] = higgs
    else:
        # For unkown keyphrase, have each process as its own group to disguise
        # nothing.
        return lambda key: key
    return lambda key: pdict.setdefault(key, None)


if __name__ == "__main__":
    dir_name = "/home/kunath/2020-02-11-14:44:13"
    #print(pol_proc_structure(dir_name))
    getPolarisationWeightedCS(pol=(.2,-.3))