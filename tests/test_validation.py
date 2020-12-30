from tools.validate_spec import cli


def validate_spec(spec: str, message: str, sample_dir: str = None) -> None:
    sample_dir = sample_dir or spec
    assert (
        cli(
            [
                "validate_spec",
                "-s",
                f"{spec}.rflx",
                "-m",
                message,
                "-v",
                f"tests/data/{sample_dir}/valid",
                "-i",
                f"tests/data/{sample_dir}/invalid",
            ]
        )
        == 0
    )


def test_validate_ethernet() -> None:
    validate_spec("in_ethernet", "Ethernet::Frame", "ethernet")


def test_validate_arp() -> None:
    validate_spec("arp", "ARP::IPv4")


def test_validate_ipv6() -> None:
    validate_spec("ipv6", "IPv6::Packet")
