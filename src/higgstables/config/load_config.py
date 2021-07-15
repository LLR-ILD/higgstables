"""Config file loader for `higgstables`."""
import argparse
import logging
import shutil
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Union

import numexpr.necompiler as nec
import yaml

logger = logging.getLogger(__name__)


class ConfigFileNotFoundError(FileNotFoundError):
    """No configuration file could be found."""

    pass


class InvalidConfigurationError(Exception):
    """The specified configuration is not valid."""

    pass


class Config:
    """Configuration class.

    Populated from a dictionary or from a yaml file through `load_config`.
    In both cases, an invalid configuration (scheme)
    should raise `InvalidConfigurationError`.
    """

    def __init__(self, config_dict: Optional[Dict] = None) -> None:
        """Configuration loading through a dictionary (of a specific schema)."""
        if config_dict is None:
            config_dict = _load_config_dict(None)

        top_level_key = "higgstables"
        try:
            conf = config_dict[top_level_key]
        except KeyError:
            raise InvalidConfigurationError(
                f"{top_level_key} must be a top level key in the configuration."
            )
        self.categories = conf["categories"]

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
    def _getvariables_from_expression(expression: str) -> Iterator[str]:
        # https://stackoverflow.com/questions/58585735/numexpr-how-to-get-variables-inside-expression
        return map(
            lambda x: x.value,
            nec.typeCompileAst(
                nec.expressionToAST(nec.stringToExpression(expression, {}, {}))
            ).allOf("variable"),
        )

    def _get_category_variables(self, categories: Dict[str, str]) -> Set[str]:
        all_variables: Set[str] = set()
        for key, expression in categories.items():
            try:
                variables = self._getvariables_from_expression(expression)
            except SyntaxError:
                raise InvalidConfigurationError(
                    f"Category {key} has an invalid syntax."
                )
            all_variables.update(variables)
        logger.info(f"The variables used for category building are: {all_variables}")
        return all_variables


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
    logger.debug(f"{yaml_path} is used as configuration file.")
    with yaml_path.open("r") as f:
        config_dict = yaml.safe_load(f)
    return config_dict


def load_config(yaml_path: Union[Path, str, None] = None) -> "Config":
    """Configuration loading through a file name.

    >>> default_config = load_config()
    >>> my_config = load_config("path/to/config.yaml")
    """
    return Config(_load_config_dict(yaml_path))


class ConfigFromArgs:
    _default_config_cli = "in local folder"
    _default_config_tag = "default"

    def __init__(self, args: argparse.Namespace) -> None:
        self.config_path = args.config
        self.data_source = args.data_source
        self.data_destination = args.data_dir

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


if __name__ == "__main__":
    config = load_config()
    print(config.category_variables)
