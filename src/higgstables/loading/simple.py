from pathlib import Path
from types import SimpleNamespace
import numpy as np


data_default = Path(__file__).parents[3] / "data"
MERGE_SS_INTO_GLUONS = True
default_brs = {
    "H→ss":     0.00034,
    "H→cc":     0.02718,
    "H→bb":     0.57720,
    "H→μμ":     0.00030,
    "H→ττ":     0.06198,
    "H→Zγ":     0.00170,
    "H→gluons": 0.08516,
    "H→γγ":     0.00242,
    "H→ZZ*":    0.02616,
    "H→WW":     0.21756,
}
if MERGE_SS_INTO_GLUONS:
    default_brs["H→gluons"] += default_brs.pop("H→ss")
assert sum(default_brs.values()) == 1


def load_normalized_columns(path):
    matrix = np.loadtxt(path)
    if MERGE_SS_INTO_GLUONS:
        ss_idx, gluons_idx = 0, 6
        matrix[:, gluons_idx] += matrix[:, ss_idx]
        matrix = np.delete(matrix, ss_idx, axis=1)
    for i in range(matrix.shape[1]):
        m_i = matrix[:,i]
        matrix[:,i] = m_i / m_i.sum()
    return matrix


def load_data(data_str=data_default, brs=None, different_X0=None,
        cheat_train_test=False):
    data_folder = Path(data_str)
    if brs is None:
        brs = np.fromiter(default_brs.values(), dtype=float)
    M = load_normalized_columns(data_folder / "train.txt")
    test_txt = "train.txt" if cheat_train_test else "test.txt"
    y_generator_matrix = load_normalized_columns(data_folder / test_txt)

    data = {}
    data["M"]  = M
    data["X0"] = np.array(different_X0 if different_X0 is not None else brs)
    data["Y"]  = y_generator_matrix.dot(brs)
    data["x_names"] = list(default_brs.keys())
    data["y_names"] = (data_folder / "categories.txt").read_text().split("\n")
    data = SimpleNamespace(**data)
    return data


if __name__ == "__main__":
    print(load_data().M.shape)