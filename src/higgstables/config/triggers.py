"""The Preselector class, used for the `unselected` and pre-selections entries."""
from typing import Dict, Iterable, Optional

from .util import CheckFields, InvalidConfigurationError, get_variables_from_expression


class Trigger:
    """Class wrapper of a selection step in the configuration file."""

    _default_type = "expression"
    _allowed_types = {"expression", "histogram"}

    def __init__(self, trigger_dict: Dict) -> None:
        self.type = trigger_dict["type"]
        self.tree = trigger_dict["tree"]
        self.out_of_tree_variables = trigger_dict.get("out-of-tree-variables", {})

        get_condition = getattr(self, "_get_condition_" + self.type)
        try:
            self.condition = get_condition(trigger_dict["condition"])
        except Exception:
            raise InvalidConfigurationError("Trigger condition not understood")

    def _get_condition_histogram(self, condition):
        assert isinstance(condition, list)
        return [int(i) for i in condition]

    def _get_condition_expression(self, condition):
        if isinstance(condition, str):
            pass
        elif isinstance(condition, list):
            # Combine selector expression by logical_and.
            condition = "(" + ") & (".join(condition) + ")"
        else:
            raise InvalidConfigurationError(f"Category {condition=}.")
        try:
            self.variables = set(get_variables_from_expression(condition))
        except SyntaxError:
            raise InvalidConfigurationError(condition)
        return condition


class Triggers:
    """Used for the `triggers` and `preselections` entries."""

    _field_checker = CheckFields(
        required={"tree", "condition"}, optional={"type", "out-of-tree-variables"}
    )

    def __init__(
        self,
        elements: Optional[Iterable] = None,
        only_preselections: bool = False,
    ) -> None:
        self._triggers = list()
        if elements is not None:
            if type(elements) != list:
                raise InvalidConfigurationError(
                    "triggers and preselections must be provided as lists. "
                    f"We got (type{type(elements)}): {elements}."
                )
            for trigger_dict in self._field_checker.iterate_list(elements):
                trigger_type = trigger_dict.get("type", Trigger._default_type)
                trigger_dict["type"] = trigger_type  # In case it was not set yet.

                if only_preselections:
                    if trigger_type != Trigger._default_type:
                        raise InvalidConfigurationError(
                            f"All preselections must have type `{Trigger._default_type}``."
                        )
                else:
                    if trigger_type not in Trigger._allowed_types:
                        raise InvalidConfigurationError(
                            f"{trigger_type} is not a valid trigger type."
                            f"Choose one of: {Trigger._allowed_types}."
                        )

                self._triggers.append(Trigger(trigger_dict))

    def __iter__(self):
        yield from self._triggers
