from setuptools import setup

if "extras_require" not in locals().keys():
    # Guard for the requirements-dev.txt test.
    extras_require = {}

extras_require["lint"] = sorted({"flake8", "black"})

extras_require["test"] = sorted({"pytest"})

extras_require["develop"] = sorted(
    set(
        extras_require["lint"]
        + extras_require["test"]
        + [
            "pre-commit",
        ]
    )
)
extras_require["complete"] = sorted(set(sum(extras_require.values(), [])))

setup(
    extras_require=extras_require,
    use_scm_version=lambda: {"local_scheme": lambda version: ""},
)
