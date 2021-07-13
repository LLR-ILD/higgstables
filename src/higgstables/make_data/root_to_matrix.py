import numexpr
import numpy as np
import pandas as pd
import uproot
from sklearn.model_selection import train_test_split

from .categories import categories

higgs_decay_id = {
    "H→ss": 3,
    "H→cc": 4,
    "H→bb": 5,
    "H→μμ": 13,
    "H→ττ": 15,
    "H→Zγ": 20,
    "H→gluons": 21,
    "H→γγ": 22,
    "H→ZZ*": 23,
    "H→WW": 24,
}

higgs_decay_name = {v: k for k, v in higgs_decay_id.items()}


def add_categorical(df, categories):
    new_cat = pd.Series(index=df.index)
    for label, expr in list(categories.items())[::-1]:
        mask = numexpr.evaluate(categories[label], df)
        new_cat.loc[mask] = label
    return pd.Categorical(new_cat, categories=categories.keys(), ordered=True)


def data_to_matrix(matrix_data):
    br_to_classes = np.zeros(
        (
            len(matrix_data["data_class"].cat.categories),
            len(matrix_data["BR"].cat.categories),
        )
    )
    for i, (h_dec, df) in enumerate(matrix_data.groupby("BR")):
        df_counts = df.groupby("data_class").count().values
        br_to_classes[:, i] = df_counts[:, 0]  # [0] to select one column.
    return br_to_classes


def get_train_test_matrices(rootfile_path):
    df = uproot.open(rootfile_path)["simple_event_vector"].pandas.df()
    matrix_data = pd.DataFrame()
    matrix_data["data_class"] = add_categorical(df, categories=categories)
    matrix_data["BR"] = pd.Categorical(
        df["hDecay"],
        ordered=True,
        categories=sorted(higgs_decay_id.values()),
    ).rename_categories(higgs_decay_name)
    train_df, test_df = train_test_split(
        matrix_data, test_size=0.5, random_state=42, stratify=matrix_data["BR"]
    )
    train_m, test_m = data_to_matrix(train_df), data_to_matrix(test_df)
    return train_m, test_m
