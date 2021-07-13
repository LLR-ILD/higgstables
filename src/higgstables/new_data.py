from pathlib import Path
from types import SimpleNamespace
import numpy as np

from make_data import save_data


rootfile_help = ("The basic file with simulated events. "
    "Produced through `make_event_vector` in the Higgs-BR-classes project: "
    "https://github.com/LLR-ILD/Higgs-BR-classes")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Replace the data.")
    parser.add_argument("rootfile", help=rootfile_help)
    parser.add_argument("--data_dir", type=str,
        help="Folder to store data into.",
        default=Path(__file__).parents[2] / "data")
    args = parser.parse_args()
    save_data(args.rootfile, args.data_dir)
