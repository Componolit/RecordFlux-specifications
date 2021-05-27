import re
import string
from datetime import datetime
from typing import Dict, List, Optional, TextIO, Tuple
from urllib.error import HTTPError
from urllib.request import urlopen

import rflx.specification.const
from defusedxml import ElementTree  # type: ignore

NAMESPACE = {"iana": "http://www.iana.org/assignments"}
RESERVED_WORDS = "|".join(rflx.specification.const.RESERVED_WORDS)


def iana_to_rflx(url: str, always_valid: bool) -> None:
    if not re.match(r"^https://www\.iana\.org/assignments/.*\.xml$", url):
        raise IANAError(f"{url} not a valid IANA url")

    try:
        with urlopen(url) as xml_response:
            xml_document: str = xml_response.read().decode("utf-8")
    except HTTPError as e:
        raise IANAError(f"cannot fetch url {e}") from e

    root = ElementTree.fromstring(xml_document)
    package_name = _normalize_name(
        root.get("id"),
    )
    with open(f"{package_name.lower()}.rflx", "w+") as file:
        file.write(f"-- AUTOMATICALLY GENERATED BY {__file__}. DO NOT EDIT.\n")
        file.write(f"-- SOURCE: {url}")
        file.write(f"-- Generation date: {datetime.now().strftime('%Y-%m-%d')}\n")
        file.write(f"-- {root.find('iana:title', NAMESPACE).text}\n")
        file.write(f"-- Registry last updated on {root.find('iana:updated', NAMESPACE).text}\n\n")
        file.write(f"package {package_name} is\n\n")
        for registry in root.findall(root.tag):
            write_registry(registry, always_valid, file)
        file.write(f"end {package_name};")


def write_registry(
    registry: ElementTree,
    always_valid: bool,
    file: TextIO,
) -> None:
    if registry.find("iana:record", NAMESPACE) is None:
        return
    duplicates = []
    file.write(f"{'':<3}type {_normalize_name(registry.find('iana:title', NAMESPACE).text)} is\n")
    file.write(f"{'':<6}(\n")

    # preprocess records and join for duplicate values
    records = registry.findall("iana:record", NAMESPACE)
    normalized_records = _normalize_records(records)
    size = max((record.bit_length for record in normalized_records))

    for record in normalized_records:
        name = record.name
        if name in duplicates or re.match(RESERVED_WORDS, name, re.I | re.X) is not None:
            name += f"_{record.value}"
        duplicates.append(name)

        if record.comment:
            file.write("\n")
            for comment_line in record.comment:
                file.write(f"{'':<9}-- {comment_line}\n")
            file.write(f"{'':<9}--\n")
        file.write(f"{'':<9}{f'{name} => {record.value}'},\n")

    file.seek(file.tell() - 2)
    file.write("\n")
    file.write(f"{'':<6})\n")
    file.write(f"{'':<3}with Size => {size}")
    if always_valid and len(normalized_records).bit_length() == size:
        file.write(", Always_Valid;")
    else:
        file.write(";")
    file.write("\n\n")


def _normalize_records(records: list) -> List["Record"]:
    normalized_records: Dict[str, Record] = {}
    for record in records:
        name_tag = f"iana:{_get_name_tag(record)}"
        value_tag = "iana:value"
        name = ""
        value = ""

        if (n := record.find(name_tag, NAMESPACE)) is not None:
            name = n.text
        if (v := record.find(value_tag, NAMESPACE)) is not None:
            value = v.text
        if name == "" or value == "" or re.search(r"RESERVED|UNASSIGNED", name, flags=re.I):
            continue
        comment = [
            element
            for element in record.iterfind("*", NAMESPACE)
            if element.tag not in [name_tag, value_tag]
        ]
        r = Record(name, value, comment)
        if value in normalized_records:
            normalized_records[value].join(r)
        else:
            normalized_records[value] = r
    return list(normalized_records.values())


def _get_name_tag(record) -> str:
    sub_elements = record.findall("*", NAMESPACE)
    child_names = set(c.tag[c.tag.index("}") + 1 :] for c in sub_elements)
    possible_name_tags = ["name", "description"]
    if all((p in child_names for p in possible_name_tags)):
        return "name"
    return child_names.intersection(possible_name_tags).pop()


class Record:
    def __init__(self, name: str = "", value: str = "", comments: Optional[List[str]] = None):
        self.name = _normalize_name(name)
        self.value, self.bit_length = _normalize_value(value)
        self._comments = comments

    def join(self, duplicate: "Record"):
        self.name = f"{self.name}_{duplicate.name}"
        self._comments.extend(duplicate._comments)

    @property
    def comment(self) -> List[str]:
        return _normalize_comment(self._comments)


def _normalize_comment(references: list) -> List[str]:
    comment_list = [
        f"{r.tag[r.tag.index('}') + 1:]} = {r.text}"
        if r.tag is not None and r.text is not None
        else f"Ref: {r.attrib['data']}"
        for r in references
    ]

    if (c := ", ".join(comment_list)) != "":
        c = c.replace("\n", " ")
        c = " ".join(c.split())
        lines = len(c) // 80 + 1
        return [c[i * 80 : i * 80 + 80] for i in range(lines)]
    return []


def _normalize_name(description_text: str) -> str:
    t = {c: " " for c in string.punctuation + "\n"}
    name = description_text.translate(str.maketrans(t))
    name = "_".join(name.split())

    return name.upper()


def _normalize_value(value: str) -> Tuple[str, int]:
    if value.find("0x") != -1:
        rflx_hex = _normalize_hex_value(value)
        return rflx_hex, (len(rflx_hex) - 3) * 4
    return value, int(value).bit_length()


def _normalize_hex_value(hex_value: str) -> str:
    if re.match(r"^0x[0-9A-F]{2},0x[0-9A-F]{2}$", hex_value) is not None:  # 0x0A,0xFF
        return f"16#{hex_value.replace('0x', '').replace(',', '')}#"
    elif re.match(r"^0x[0-9A-F]+$", hex_value) is not None:  # 0xA1A1
        return f"16#{hex_value[2:]}#"


class IANAError(Exception):
    pass


if __name__ == "__main__":
    iana_to_rflx(
        "https://www.iana.org/assignments/bootp-dhcp-parameters/bootp-dhcp-parameters.xml", True
    )
