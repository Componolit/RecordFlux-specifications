import glob
import re
import subprocess
import warnings
from pathlib import Path
from xml.etree import ElementTree

import pytest
from rflx.converter import iana
from rflx.validator import Validator

DATA_PATH = Path("tests/data")


@pytest.mark.parametrize("spec", glob.glob("*.rflx"))
def test_spec(spec: str, tmp_path: Path) -> None:
    subprocess.run(
        ["rflx", "generate", "--ignore-unsupported-checksum", "-d", tmp_path, spec], check=True
    )
    subprocess.run(["gprbuild", "-U"], check=True, cwd=tmp_path)


@pytest.mark.parametrize("registry_file", (Path(f) for f in glob.glob("iana_registries/*.xml")))
def test_iana_specs_synchronized(registry_file: Path) -> None:
    registry = ElementTree.fromstring(registry_file.read_text(encoding="utf-8"))
    registry_last_updated = registry.find("iana:updated", iana.NAMESPACE)
    assert registry_last_updated is not None
    assert (
        re.search(
            f"Registry last updated on {registry_last_updated.text}",
            Path(f"{registry_file.stem}.rflx".replace("-", "_")).read_text(encoding="utf-8"),
        )
        is not None
    )


@pytest.mark.parametrize("spec", glob.glob("*.rflx"))
def test_validate_spec(spec: str) -> None:
    validator = Validator([spec], "checksum", skip_model_verification=True)

    # https://github.com/Componolit/RecordFlux/issues/833
    for package in validator._pyrflx:  # pylint: disable = protected-access
        for message_value in package:
            test_data_dir = (
                DATA_PATH
                / str(message_value.identifier.parent).lower()
                / str(message_value.identifier.name).lower()
            )

            if not test_data_dir.is_dir():
                warnings.warn(f"No example data found for {message_value.identifier}")
                continue

            directory_invalid = test_data_dir / "invalid"
            directory_valid = test_data_dir / "valid"

            validator.validate(
                message_value.identifier,
                directory_invalid,
                directory_valid,
                coverage=True,
            )
