"""The higgstables command line interface."""
from .cli import main as cli
from .cli import make_selected_event_dfs_instead_of_count_tables as cli_df

__all__ = ["cli", "cli_df"]
