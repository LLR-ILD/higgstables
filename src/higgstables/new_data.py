from pathlib import Path

from make_data import save_data

rootfile_help = (
    "The basic file with simulated events. "
    "Produced through `make_event_vector` in the Higgs-BR-classes project: "
    "https://github.com/LLR-ILD/Higgs-BR-classes"
)

if __name__ == "__main__":
    try:
        default_csv_dir = Path(__file__).parents[2] / "data"
    except IndexError:
        # This script might not be that far down in the file hierarchy.
        default_csv_dir = Path("data")
    import argparse

    parser = argparse.ArgumentParser(description="Replace the data.")
    parser.add_argument("rootfile", help=rootfile_help)
    parser.add_argument(
        "--data_dir",
        type=str,
        help="Folder to store data into.",
        default=default_csv_dir,
    )
    args = parser.parse_args()
    save_data(args.rootfile, args.data_dir)
