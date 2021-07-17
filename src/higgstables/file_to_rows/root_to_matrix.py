import itertools
import logging
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Set, Tuple

import numexpr
import numpy as np
import pandas as pd
import tqdm
import uproot
from tqdm.contrib.logging import logging_redirect_tqdm

from ..config import Config, Trigger

logger = logging.getLogger(__name__)


def _get_process_name(path: Path) -> str:
    return path.absolute().parent.name


class FileToCounts:
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

        self.row_cells["unselected"] = self.run_triggers()
        self.keep_mask = self.run_preselections()
        n_not_preselected = self.keep_mask.shape[0] - np.sum(self.keep_mask)
        self.row_cells["unselected"] = self.row_cells["unselected"] + n_not_preselected
        self.fill_categories()

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

    def run_preselections(self) -> "np.ndarray[np.bool_]":
        keep_mask = None
        for preselection in self._config.preselections:
            keep_mask_step = self._get_condition_mask(preselection)
            if keep_mask is None:
                keep_mask = keep_mask_step
            else:
                keep_mask = keep_mask & keep_mask_step
        return keep_mask

    def fill_categories(self) -> None:
        if self.keep_mask is None:
            old_n_events_without_category = 0
        else:
            old_n_events_without_category = np.sum(self.keep_mask)
        for name, selection in self._config.categories_wrapped_as_triggers():
            is_in_category = self._get_condition_mask(selection)
            if self.keep_mask is None:
                self.keep_mask = is_in_category
            else:
                self.keep_mask = self.keep_mask & np.logical_not(is_in_category)
            n_events_without_category = np.sum(self.keep_mask)
            self.row_cells[name] = (
                old_n_events_without_category - n_events_without_category
            )
            old_n_events_without_category = n_events_without_category

    def _get_condition_mask(self, selector: Trigger) -> "np.ndarray[np.bool_]":
        local_arrays = self._get_array_dict(selector)
        mask = numexpr.evaluate(selector.condition, local_arrays)
        return mask

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

    def as_series(self) -> pd.Series:
        return pd.Series(self.row_cells, name=self.name)


class TablesFromFiles:
    """Handles the combination of files into a consitent table."""

    def __init__(
        self,
        data_source: Path,
        data_dir: Path,
        config: Config,
    ) -> None:
        self._data_source = data_source
        self._data_dir = data_dir
        self._config = config

        self.build_tables()

    def build_tables(self) -> None:
        n_files, table_files = self._find_files()
        with logging_redirect_tqdm():
            self._per_file_bar = tqdm.tqdm(total=n_files)
            for name, files in table_files.items():
                self._per_file_bar.set_description(f"Building table {name}")
                df = self.build_table(sorted(list(files)), name)
                df.to_csv(self._data_dir / f"{name}.csv")
            self._per_file_bar.close()

    def build_table(self, files: List[Path], name: str) -> pd.DataFrame:
        process_columns = self._get_counts(files)
        table = process_columns.transpose()
        if not self._config.no_cs:
            cs = self._get_cross_sections(name, table.index)
            table.insert(0, "cross section [fb]", cs)
        return table

    def _get_cross_sections(self, name: str, processes: pd.Index) -> pd.Series:
        cross_sections = self._config.cross_sections.per_polarization()
        if name not in cross_sections:
            logger.warning(
                f"The table name {name} was not understood "
                f"as a valid polarization {tuple(cross_sections.keys())}. "
                "All cross sections are set to infinity."
            )
            return pd.Series(float("inf"), index=processes)
        cs_polarized = cross_sections[name]
        cs_dict = {
            process: cs_polarized.get(process, float("inf")) for process in processes
        }
        return pd.Series(cs_dict)

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
            logger.error("No file was found for any table.")
        elif n_files != sum(len(v) for v in table_files.values()):
            logger.warning("Some files contribute to more than one table.")

        return n_files, table_files

    def _apply_ignoring(self, path_set: Set[Path]) -> Set[Path]:
        ignored_processes = self._config.ignored_processes
        ignored_paths = [
            path for path in path_set if _get_process_name(path) in ignored_processes
        ]
        for ignored_path in ignored_paths:
            path_set.remove(ignored_path)
        return path_set
