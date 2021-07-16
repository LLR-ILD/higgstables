import pytest

from higgstables.config import Config, _default_yaml_path
from higgstables.config.load_config import load_config
from higgstables.config.util import InvalidConfigurationError


def test_default_config_found():
    _default_yaml_path.exists()


def test_build_default_config():
    load_config()


def test_invalid_category_expression_raises_error():
    from higgstables.config.load_config import _load_config_dict

    faulty_dict = _load_config_dict(None)
    faulty_dict["higgstables"]["categories"]["new_cat"] = "this is invalid!"
    with pytest.raises(InvalidConfigurationError):
        Config(faulty_dict)
