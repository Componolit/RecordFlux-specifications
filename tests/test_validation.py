from tools.validate_spec import cli


def test_validate_ethernet() -> None:
    assert (
        cli(
            [
                "validate_spec",
                "-s",
                "in_ethernet.rflx",
                "-m",
                "Ethernet::Frame",
                "-v",
                "tests/data/ethernet/valid",
                "-i",
                "tests/data/ethernet/invalid",
            ]
        )
        == 0
    )


def test_validate_arp() -> None:
    assert (
        cli(
            [
                "validate_spec",
                "-s",
                "arp.rflx",
                "-m",
                "ARP::IPv4",
                "-v",
                "tests/data/arp/valid",
                "-i",
                "tests/data/arp/invalid",
            ]
        )
        == 0
    )
