"""The working horse: Gets counts out of rootfiles into the .csv tables."""
import itertools
import logging
import warnings
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Set, Tuple

import numexpr
import numpy as np
import pandas as pd
import tqdm
import uproot
from tqdm.contrib.logging import logging_redirect_tqdm

from ..config import Config, Trigger

logger = logging.getLogger(__name__)
KeepMaskType = Optional["np.ndarray[np.bool_]"]


def _get_process_name(path: Path) -> str:
    return path.absolute().parent.name


class FileToSelected:
    """From a single rootfile, extract the counts per category."""

    def __init__(
        self,
        rootfile_path: Path,
        config: Config,
    ) -> None:
        self._rootfile_path = rootfile_path
        self._config = config

        self._rootfile = uproot.open(self._rootfile_path)
        self.name = _get_process_name(self._rootfile_path)
        self._loaded_arrays: DefaultDict = defaultdict(dict)
        self.row_cells: Dict[str, int] = {}

        n_not_triggered = self.run_triggers()
        n_not_preselected, self._keep_mask = self.run_preselections()
        self.row_cells["unselected"] = n_not_triggered + n_not_preselected

    def _get_array_dict(self, selector: Trigger) -> Dict["str", np.ndarray]:
        local_arrays = {}
        for var in selector.variables:
            var_tree = selector.out_of_tree_variables.get(var, selector.tree)
            if var not in self._loaded_arrays[var_tree]:
                try:
                    array = self._rootfile[var_tree][var].array(library="np")
                except KeyError as e:
                    logger.error(
                        f"{var} not found in {var_tree} of {self._rootfile_path}"
                    )
                    raise e
                self._loaded_arrays[var_tree][var] = array
            local_arrays[var] = self._loaded_arrays[var_tree][var]
        return local_arrays

    def run_triggers(self) -> int:
        n_not_selected = 0
        for trigger in self._config.triggers:
            if trigger.type == "histogram":
                bin_counts = self._rootfile[trigger.tree].to_numpy()[0]
                n_before_trigger = np.sum(bin_counts)
                n_after_trigger = np.sum(bin_counts[trigger.condition])
                n_not_selected_in_step = n_before_trigger - n_after_trigger
                n_not_selected += n_not_selected_in_step
            elif trigger.type == Trigger._default_type:
                mask = self._get_condition_mask(trigger)
                n_not_selected += mask.shape[0] - np.sum(mask)
            else:
                raise NotImplementedError(trigger.type)
        return n_not_selected

    def run_preselections(self) -> Tuple[int, KeepMaskType]:
        keep_mask = None
        for preselection in self._config.preselections:
            keep_mask_step = self._get_condition_mask(preselection)
            if keep_mask is None:
                keep_mask = keep_mask_step
            keep_mask = keep_mask & keep_mask_step
        if keep_mask is not None:
            n_not_preselected = keep_mask.shape[0] - np.sum(keep_mask)
        else:
            n_not_preselected = 0
        return n_not_preselected, keep_mask

    def _get_condition_mask(self, selector: Trigger) -> "np.ndarray[np.bool_]":
        local_arrays = self._get_array_dict(selector)
        mask = numexpr.evaluate(selector.condition, local_arrays)
        return mask


class FileToCounts(FileToSelected):
    """From a single rootfile, extract the counts per category."""

    def __init__(
        self,
        rootfile_path: Path,
        config: Config,
    ) -> None:
        super().__init__(rootfile_path, config)
        self.fill_categories(self._keep_mask)

    def fill_categories(self, keep_mask: KeepMaskType = None) -> None:
        for name, selection in self._config.categories_wrapped_as_triggers():
            is_in_category = self._get_condition_mask(selection)
            if keep_mask is None:
                keep_mask = np.ones_like(is_in_category, dtype=bool)
            self.row_cells[name] = np.sum(keep_mask & is_in_category)
            keep_mask = keep_mask & np.logical_not(is_in_category)

    def as_series(self) -> pd.Series:
        return pd.Series(self.row_cells, name=self.name)


def _get_entry_stop(keep_mask: KeepMaskType = None, n_max: int = -1) -> int:
    entry_stop = n_max
    if n_max >= 0 and keep_mask is not None:
        try:
            entry_stop = np.nonzero(np.cumsum(keep_mask) == n_max)[0][0] + 1
        except IndexError:
            entry_stop = -1
    return entry_stop


VarsPerTreeType = Optional[Dict[str, Optional[List[str]]]]


def _validate_vars_per_tree(
    vars_per_tree: VarsPerTreeType, config: Config
) -> Dict[str, Optional[List[str]]]:
    if vars_per_tree is not None:
        return vars_per_tree
    if len(config.df) > 0:
        vars_per_tree = config.df
    if vars_per_tree is None:
        cat_tree = config.categories_tree
        vars_per_tree = {cat_tree: None}
        logger.warning(
            "The `df` field was not found in the config file. "
            f"Instead, all branches from `categories-tree` ({cat_tree}) are taken."
        )
    return vars_per_tree


class FileToDf(FileToSelected):
    """From a single rootfile, build the DataFrame of selected events."""

    def __init__(
        self,
        rootfile_path: Path,
        config: Config,
        n_max: int = -1,
        vars_per_tree: VarsPerTreeType = None,
    ) -> None:
        super().__init__(rootfile_path, config)
        self._df = self.fill_df(self._keep_mask, n_max, vars_per_tree)

    def fill_df(
        self,
        keep_mask: KeepMaskType = None,
        n_max: int = -1,
        vars_per_tree: VarsPerTreeType = None,
    ) -> pd.DataFrame:
        entry_stop = _get_entry_stop(keep_mask, n_max)
        df_parts = []
        vars_per_tree = _validate_vars_per_tree(vars_per_tree, self._config)
        for tree, vars in vars_per_tree.items():
            df_parts.append(self._get_df_part(tree, vars, entry_stop=entry_stop))
            if keep_mask is not None:
                df_parts[-1] = df_parts[-1][keep_mask[:entry_stop]]
        df = pd.concat(df_parts, axis="columns")
        n_selected = np.sum(keep_mask)
        df.insert(
            0, "efficiency", n_selected / (self.row_cells["unselected"] + n_selected)
        )
        return df

    def _get_df_part(
        self,
        var_tree: str,
        vars: Optional[List[str]] = None,
        entry_stop: int = -1,
    ) -> pd.DataFrame:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=FutureWarning)
                df_part = self._rootfile[var_tree].arrays(
                    expressions=vars, library="pd", entry_stop=entry_stop
                )
        except KeyError as e:
            logger.error(f"tree {var_tree} not found in {self._rootfile_path}")
            raise e
        return df_part

    def as_df(self) -> pd.Series:
        self._df.name = self.name
        return self._df


class DataFromFiles:
    """Handles the combination of files into a consistent table."""

    def __init__(
        self,
        data_source: Path,
        data_dir: Path,
        config: Config,
        obj_type: str = "table",
    ) -> None:
        self._data_source = data_source
        self._data_dir = data_dir
        self._config = config
        self._obj_type = obj_type

        self.build_objects()

    def build_objects(self) -> None:
        n_files, table_files = self._find_files()
        with logging_redirect_tqdm():
            self._per_file_bar = tqdm.tqdm(total=n_files)
            for name, files in table_files.items():
                self._per_file_bar.set_description(f"Building {self._obj_type} {name}")
                df = self.build_obj(sorted(list(files)), name)
                self._save(df, name)
            self._per_file_bar.close()

    def _save(self, df: pd.DataFrame, name: str) -> None:
        raise NotImplementedError

    def build_obj(self, files: List[Path], name: str) -> pd.DataFrame:
        raise NotImplementedError

    def _get_cross_sections(self, name: str, processes: pd.Index) -> pd.Series:
        cross_sections = self._config.cross_sections.per_polarization()
        if name not in cross_sections:
            logger.warning(
                f"The {self._obj_type} name {name} was not understood "
                f"as a valid polarization {tuple(cross_sections.keys())}. "
                "All cross sections are set to infinity."
            )
            return pd.Series(float("inf"), index=processes)
        cs_polarized = cross_sections[name]
        cs_dict = {
            process: cs_polarized.get(process, float("inf")) for process in processes
        }
        return pd.Series(cs_dict)

    def _find_files(self) -> Tuple[int, Dict[str, Set[Path]]]:
        table_files: Dict[str, Set[Path]] = {}
        if self._data_source.is_file():
            table_files[_get_process_name(self._data_source)] = {self._data_source}

        elif self._data_source.is_dir():
            for table_name, search_pattern in self._config.tables.items():
                in_this_table = set(self._data_source.glob(search_pattern))
                in_this_table = self._apply_ignoring(in_this_table)
                if len(in_this_table) == 0:
                    logger.warning(f"No file matches the pattern {search_pattern}.")
                table_files[table_name] = in_this_table
        else:
            raise NotImplementedError(self._data_source)

        # Plausibility checks-
        all_considered_files = set(itertools.chain(*table_files.values()))
        n_files = len(all_considered_files)
        if n_files == 0:
            logger.error(f"No file was found for any {self._obj_type}.")
        elif n_files != sum(len(v) for v in table_files.values()):
            logger.warning(f"Some files contribute to more than one {self._obj_type}.")

        return n_files, table_files

    def _apply_ignoring(self, path_set: Set[Path]) -> Set[Path]:
        ignored_processes = self._config.ignored_processes
        ignored_paths = [
            path for path in path_set if _get_process_name(path) in ignored_processes
        ]
        for ignored_path in ignored_paths:
            path_set.remove(ignored_path)
        return path_set


class TablesFromFiles(DataFromFiles):
    """Handles the combination of files into a consistent table."""

    def __init__(
        self,
        data_source: Path,
        data_dir: Path,
        config: Config,
    ) -> None:
        super().__init__(data_source, data_dir, config, obj_type="table")

    def _save(self, df: pd.DataFrame, name: str):
        df.to_csv(self._data_dir / f"{name}.csv")

    def build_obj(self, files: List[Path], name: str) -> pd.DataFrame:
        process_columns = self._get_counts(files)
        table = process_columns.transpose()
        if not self._config.no_cs:
            cs = self._get_cross_sections(name, table.index)
            table.insert(0, "cross section [fb]", cs)
        return table

    def _get_counts(self, files: List[Path]) -> pd.DataFrame:
        df = None
        for file in files:
            series: pd.Series = FileToCounts(file, self._config).as_series()
            if df is None:
                df = series.to_frame()
            if series.name in df.columns:
                df[series.name] = df[series.name] + series
            else:
                df[series.name] = series
            self._per_file_bar.update(1)
        return df


class DfFromFiles(DataFromFiles):
    """Create a pandas DataFrame for all selected events, per polarization."""

    def __init__(
        self,
        data_source: Path,
        data_dir: Path,
        config: Config,
        vars_per_tree: VarsPerTreeType = None,
        n_max: Optional[int] = None,
    ) -> None:
        if n_max is None:
            self._n_max = config.df_n_max
        else:
            self._n_max = n_max
        self._vars_per_tree = _validate_vars_per_tree(vars_per_tree, config)
        super().__init__(data_source, data_dir, config, obj_type="df")

    def _save(self, df: pd.DataFrame, name: str):
        df.to_pickle(self._data_dir / f"{name}.pkl")

    def build_obj(self, files: List[Path], name: str) -> pd.DataFrame:
        dfs = []
        for file in files:
            file_df: pd.DataFrame = FileToDf(
                file, self._config, self._n_max, self._vars_per_tree
            ).as_df()
            file_df.insert(0, "process", file_df.name)
            dfs.append(file_df)
            self._per_file_bar.update(1)
        df = pd.concat(dfs)
        if not self._config.no_cs:
            cs = self._get_cross_sections(name, df.process.unique())
        df.insert(2, "cross section [fb]", df.process.map(cs))
        return df
