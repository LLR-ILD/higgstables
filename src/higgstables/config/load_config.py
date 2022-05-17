"""Config file loader for `higgstables`."""
import argparse
import logging
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

import pandas as pd
import yaml

from ..ild_specific import CrossSectionException, CrossSections
from .triggers import Trigger, Triggers
from .util import (
    CheckFields,
    ConfigFileNotFoundError,
    InvalidConfigurationError,
    get_variables_from_expression,
)

logger = logging.getLogger(__name__)


class Config:
    """Configuration class.

    Populated from a dictionary or from a yaml file through `load_config`.
    In both cases, an invalid configuration (scheme)
    should raise `InvalidConfigurationError`.
    """

    def __init__(self, config_dict: Optional[Dict] = None, no_cs: bool = False) -> None:
        """Configuration loading through a dictionary (of a specific schema)."""
        self.no_cs = no_cs
        if config_dict is None:
            config_dict = _load_config_dict(None)

        conf = CheckFields(
            required={"categories", "categories-tree", "machine", "tables"},
            optional={
                "anchors",
                "categories-out-of-tree-variables",
                "cross-section-zero",
                "format",
                "df",
                "ignored-processes",
                "triggers",
                "preselections",
            },
        ).by_name("higgstables", config_dict)

        self.categories = conf["categories"]
        self.categories_tree = conf["categories-tree"]
        self.categories_out_of_tree_variables = conf.get(
            "categories-out-of-tree-variables", {}
        )
        self.df = conf.get("df", {})
        assert type(self.df) == dict
        self.df_n_max = self.df.pop("n_max", None)
        if self.df_n_max is not None:
            self.df_n_max = int(self.df_n_max)

        self.triggers = Triggers(conf.get("triggers", None))
        self.preselections = Triggers(
            conf.get("preselections", None),
            only_preselections=True,
        )

        self._format = conf.get("format", "csv")
        self.save_df(pd.DataFrame(), Path(), "dummy_name", validate_only=True)
        self.tables = conf["tables"]
        self.ignored_processes: List["str"] = conf.get("ignored-processes", [])
        self.cross_section_zero: List["str"] = conf.get("cross-section-zero", [])
        if not self.no_cs:
            try:
                self.cross_sections = CrossSections(conf["machine"])
            except CrossSectionException as e:
                logger.error(
                    f'The cross sections for {conf["machine"]} could not be read. '
                    "To run without the cross sections column, specify `no_cs`."
                )
                raise e
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        try:
            out_of_tree = self.categories_out_of_tree_variables
            assert type(out_of_tree) == dict
            assert all(type(v) == str for v in out_of_tree.values())
            assert type(self.tables) == dict
            assert all(type(e) == str for e in self.tables.values())
            assert type(self.ignored_processes) == list
            assert all(type(e) == str for e in self.ignored_processes)
            assert type(self.cross_section_zero) == list
            assert all(type(e) == str for e in self.cross_section_zero)
            if self.df_n_max is not None:
                assert type(self.df_n_max) == int
                assert self.df_n_max >= -1
            assert type(self.df) == dict
            assert all(
                v is None or all(type(v_i) == str for v_i in v)
                for v in self.df.values()
            )
        except AssertionError:
            raise InvalidConfigurationError

    @property
    def categories(self) -> Dict[str, str]:
        return self._categories

    @categories.setter
    def categories(self, category_dict: Dict[str, Union[str, List[str]]]) -> None:
        new_categories = {}
        for key, value in category_dict.items():
            if isinstance(value, str):
                pass
            elif isinstance(value, list):
                # Combine selector expression by logical_and.
                value = "(" + ") & (".join(value) + ")"
            else:
                raise InvalidConfigurationError(f"Category {key=}, {value=}.")
            new_categories[key] = value
        self._category_variables = self._get_category_variables(new_categories)
        self._categories = new_categories

    @property
    def category_variables(self) -> Set[str]:
        return self._category_variables

    @staticmethod
    def _get_category_variables(categories: Dict[str, str]) -> Set[str]:
        all_variables: Set[str] = set()
        for key, expression in categories.items():
            try:
                variables = get_variables_from_expression(expression)
            except SyntaxError:
                raise InvalidConfigurationError(
                    f"Category {key} has an invalid syntax."
                )
            all_variables.update(variables)
        logger.info(f"The variables used for category building are: {all_variables}")
        return all_variables

    def categories_wrapped_as_triggers(self) -> Iterable[Tuple[str, Trigger]]:
        for key, condition in self.categories.items():
            yield key, Trigger(
                {
                    "condition": condition,
                    "type": Trigger._default_type,
                    "tree": self.categories_tree,
                    "out-of-tree-variables": self.categories_out_of_tree_variables,
                }
            )

    def save_df(
        self, df: pd.DataFrame, folder: Path, name: str, validate_only: bool = False
    ):
        _save_options = {
            "csv": lambda df: df.to_csv(folder / f"{name}.csv"),
            "parquet": lambda df: df.to_parquet(folder / f"{name}.parquet"),
            "pickle": lambda df: df.to_pickle(folder / f"{name}.pkl"),
        }
        if self._format not in _save_options:
            raise InvalidConfigurationError(
                f"{self._format} not in {_save_options.keys()}."
            )
        if not validate_only:
            _save_options[self._format](df)


_yaml_name = "higgstables-config.yaml"
_default_yaml_path = (Path(__file__).parent / _yaml_name).absolute()


def _select_yaml_path(yaml_path: Union[Path, str, None]) -> Path:
    """Returns an existing file path or raises an error."""
    if yaml_path is None:
        yaml_path = _default_yaml_path
        logger.info(f"Using the default configuration file at {yaml_path}.")
    yaml_path = Path(yaml_path)

    if not yaml_path.exists():
        raise ConfigFileNotFoundError(f"{yaml_path} does not exists.")
    if yaml_path.is_dir():
        yaml_path_in_dir = yaml_path / _yaml_name
        if yaml_path_in_dir.is_file():
            yaml_path = yaml_path_in_dir
        else:
            raise ConfigFileNotFoundError(f"{_yaml_name} not found in {yaml_path}.")
    return yaml_path


def _load_config_dict(yaml_path: Union[Path, str, None]) -> Dict:
    """Reads the yaml content from an appropriate path or raises an error."""
    yaml_path = _select_yaml_path(yaml_path)
    logger.debug(f"{yaml_path.absolute()} is used as configuration file.")
    with yaml_path.open("r") as f:
        config_dict = yaml.safe_load(f)
    return config_dict


def load_config(
    yaml_path: Union[Path, str, None] = None, no_cs: bool = False
) -> "Config":
    """Configuration loading through a file name.

    >>> default_config = load_config()
    >>> my_config = load_config("path/to/config.yaml")
    """
    return Config(_load_config_dict(yaml_path), no_cs)


class ConfigFromArgs:
    """Load the configuration when using the command line interface."""

    _default_config_cli = "in local folder"
    _default_config_tag = "default"

    def __init__(self, args: argparse.Namespace) -> None:
        self.config_path = args.config
        self.data_source = args.data_source
        self.data_destination = args.data_dir
        self.no_cs = args.no_cs

    def get_config(self) -> Config:
        """Return a Config object."""
        try:
            if self.config_path == self._default_config_tag:
                valid_config_path = _select_yaml_path(None)
            elif self.config_path == self._default_config_cli:
                valid_config_path = _select_yaml_path(self.data_source)
            else:
                valid_config_path = _select_yaml_path(self.config_path)
        except ConfigFileNotFoundError as e:
            logging.error(
                "If you intended to use the default config file, "
                f"set `--config {self._default_config_tag}`."
            )
            raise e
        shutil.copy(valid_config_path, self.data_destination)
        config = load_config(valid_config_path)
        return config
