from typing import Dict, Iterable, Iterator, Optional

import numexpr.necompiler as nec


class ConfigFileNotFoundError(FileNotFoundError):
    """No configuration file could be found."""

    pass


class InvalidConfigurationError(Exception):
    """The specified configuration is not valid."""

    pass


class CheckFields:
    """Check the configuration scheme two levels down."""

    def __init__(
        self,
        required: Optional[Iterable] = None,
        optional: Optional[Iterable] = None,
    ) -> None:
        self._required_fields = set(required) if required is not None else set()
        self._optional_fields = set(optional) if optional is not None else set()

    def by_name(self, top_level_key: str, config_dict: Dict) -> Dict:
        """Use this if the next level is a dictionary, checks one of them."""
        try:
            conf = config_dict[top_level_key]
        except KeyError:
            raise InvalidConfigurationError(
                f"{top_level_key} must be a top level key in the configuration."
            )
        self._check_dict_fields(conf, top_level_key)
        return conf

    def iterate_list(self, config_list: Iterable) -> Iterable:
        """Use this if the next level is a list."""
        # First, check that all elements have the required scheme.
        for i, element in enumerate(config_list):
            self._check_dict_fields(element, f"list element #{i}")
        yield from config_list

    def _check_dict_fields(self, conf: Dict, name: str) -> None:
        conf_fields = set(conf)
        if not conf_fields.issuperset(self._required_fields):
            missing_fields = self._required_fields - conf_fields
            raise InvalidConfigurationError(f"Missing fields: {missing_fields}.")
        allowed_fields = self._required_fields | self._optional_fields
        if not conf_fields.issubset(allowed_fields):
            raise InvalidConfigurationError(
                f"A fields that was not understood is present under {name}: "
                f"{conf_fields - allowed_fields}.\n"
                f"Please use only: {allowed_fields}."
            )


def get_variables_from_expression(expression: str) -> Iterator[str]:
    # https://stackoverflow.com/questions/58585735/numexpr-how-to-get-variables-inside-expression
    return map(
        lambda x: x.value,
        nec.typeCompileAst(
            nec.expressionToAST(nec.stringToExpression(expression, {}, {}))
        ).allOf("variable"),
    )
