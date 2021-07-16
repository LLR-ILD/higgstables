from .root_to_matrix import FileToCounts


def save_data(args, config):
    series = FileToCounts(args.data_source, config).as_series()
    series.to_csv(args.data_dir / "matrix.txt")
