from pathlib import Path

import numpy as np

from .categories import categories
from .root_to_matrix import get_train_test_matrices


def save_data(rootfile_path, data_str):
    data_folder = Path(data_str)
    data_folder.mkdir(exist_ok=True, parents=True)

    train_m, test_m = get_train_test_matrices(rootfile_path)
    np.savetxt(data_folder / "train.txt", train_m, fmt="%i")
    np.savetxt(data_folder / "test.txt", test_m, fmt="%i")

    y_names = "\n".join(list(categories.keys()))
    (data_folder / "categories.txt").write_text(y_names)
    (data_folder / "meta.txt").write_text(
        "\n".join([f"{rootfile_path=}", f"{categories=}"])
    )
    # x_names = "\n".join([k for k, v in sorted(higgs_decay_id.items(),
    #                                           key=lambda item: item[1])])
    # (data_folder / "brs.txt").write_text(x_names)
