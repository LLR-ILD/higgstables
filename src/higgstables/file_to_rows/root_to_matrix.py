import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict

import numexpr
import numpy as np
import pandas as pd
import uproot

from ..config import Config, Trigger

logger = logging.getLogger(__name__)


class FileToCounts:
    def __init__(
        self,
        rootfile_path: Path,
        config: Config,
    ) -> None:
        self._rootfile_path = rootfile_path
        self._rootfile = uproot.open(self._rootfile_path)
        self._config = config
        self._loaded_arrays: DefaultDict = defaultdict(dict)
        self.row_cells: Dict[str, Any] = {"process": self._rootfile_path.parent.name}

        self.row_cells["n_not_selected"] = self.run_triggers()
        self.keep_mask = self.run_preselections()
        n_not_preselected = self.keep_mask.shape[0] - np.sum(self.keep_mask)
        self.row_cells["n_not_selected"] = (
            self.row_cells["n_not_selected"] + n_not_preselected
        )
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
        return pd.Series(self.row_cells)
