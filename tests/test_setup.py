from pathlib import Path


def test_requirements_dev():
    repo_root = Path(__file__).parent.parent

    # Get requirements-dev imports.
    requirements_dev = repo_root / "requirements-dev.txt"
    with requirements_dev.open() as f:
        dev_imports = set(
            map(lambda x: x.replace("\n", "").replace(" ", ""), f.readlines())
        )
    dev_imports.discard("")  # This allows for empty lines the requirements file.

    # Get imports from setup.cfg.
    setup_imports = set()
    with (repo_root / "setup.cfg").open() as f:
        setup_txt = f.read()
    ir_tag = "install_requires"
    install_lines = setup_txt[
        setup_txt.find(ir_tag) + len(ir_tag) : setup_txt.find(f"# end_{ir_tag}")
    ]
    install_lines = install_lines.replace(" ", "")
    install_lines = install_lines.replace("=\n", "")
    # [:-1] to avoid an empty-line entry.
    setup_imports |= set(install_lines.split("\n")[:-1])
    assert setup_imports.issubset(dev_imports)

    # Get imports specified in setup.py.
    with (repo_root / "setup.py").open() as f:
        setup_txt = f.read()
    setup_txt = setup_txt[: setup_txt.find("setup(")]
    # Avoid unnecessary DeprecationWarning during test.
    setup_txt = setup_txt.replace("from setuptools import setup", "")
    extras_require = {}
    exec(setup_txt, dict(extras_require=extras_require))
    setup_imports |= set(extras_require["complete"])
    assert len(setup_imports) == len(dev_imports)
    for setup_import, dev_import in zip(
        sorted(set(setup_imports)), sorted(set(dev_imports))
    ):
        assert setup_import == dev_import
