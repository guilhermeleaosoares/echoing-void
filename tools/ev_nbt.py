"""
Minimal NBT reader/writer - just enough to author Minecraft structure templates.

No third-party dependency: structure .nbt files are gzipped, big-endian, tagged
binary, and the subset used by StructureTemplate is small (compound, list,
string, int, byte, double, int-array). The reader exists so the writer can be
checked against real vanilla structures rather than trusted blindly.
"""

from __future__ import annotations

import gzip
import struct
from typing import Any

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


# ---------------------------------------------------------------------------
# typed wrappers - needed because Python ints alone cannot say "this is a short"
# ---------------------------------------------------------------------------

class Tag:
    tag_id = TAG_END

    def __init__(self, value: Any):
        self.value = value


class Byte(Tag):
    tag_id = TAG_BYTE


class Short(Tag):
    tag_id = TAG_SHORT


class Int(Tag):
    tag_id = TAG_INT


class Long(Tag):
    tag_id = TAG_LONG


class Float(Tag):
    tag_id = TAG_FLOAT


class Double(Tag):
    tag_id = TAG_DOUBLE


class String(Tag):
    tag_id = TAG_STRING


class IntArray(Tag):
    tag_id = TAG_INT_ARRAY


class List(Tag):
    """A homogeneous NBT list. element_id is required when the list is empty."""

    tag_id = TAG_LIST

    def __init__(self, items: list, element_id: int | None = None):
        super().__init__(items)
        if element_id is not None:
            self.element_id = element_id
        elif items:
            self.element_id = _infer_id(items[0])
        else:
            self.element_id = TAG_END


class Compound(Tag):
    tag_id = TAG_COMPOUND

    def __init__(self, mapping: dict[str, Any] | None = None):
        super().__init__(dict(mapping or {}))

    def __setitem__(self, key: str, value: Any) -> None:
        self.value[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.value[key]


def _infer_id(value: Any) -> int:
    if isinstance(value, Tag):
        return value.tag_id
    if isinstance(value, bool):
        return TAG_BYTE
    if isinstance(value, int):
        return TAG_INT
    if isinstance(value, float):
        return TAG_DOUBLE
    if isinstance(value, str):
        return TAG_STRING
    if isinstance(value, dict):
        return TAG_COMPOUND
    if isinstance(value, list):
        return TAG_LIST
    raise TypeError(f"cannot infer NBT tag for {type(value)!r}")


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------

def _write_string(out: bytearray, s: str) -> None:
    raw = s.encode("utf-8")
    out += struct.pack(">H", len(raw))
    out += raw


def _write_payload(out: bytearray, tag_id: int, value: Any) -> None:
    if isinstance(value, Tag) and not isinstance(value, (List, Compound)):
        value = value.value

    if tag_id == TAG_BYTE:
        out += struct.pack(">b", int(value))
    elif tag_id == TAG_SHORT:
        out += struct.pack(">h", int(value))
    elif tag_id == TAG_INT:
        out += struct.pack(">i", int(value))
    elif tag_id == TAG_LONG:
        out += struct.pack(">q", int(value))
    elif tag_id == TAG_FLOAT:
        out += struct.pack(">f", float(value))
    elif tag_id == TAG_DOUBLE:
        out += struct.pack(">d", float(value))
    elif tag_id == TAG_STRING:
        _write_string(out, str(value))
    elif tag_id == TAG_INT_ARRAY:
        items = value.value if isinstance(value, Tag) else value
        out += struct.pack(">i", len(items))
        for i in items:
            out += struct.pack(">i", int(i))
    elif tag_id == TAG_LIST:
        lst = value if isinstance(value, List) else List(list(value))
        out += struct.pack(">b", lst.element_id)
        out += struct.pack(">i", len(lst.value))
        for item in lst.value:
            _write_payload(out, lst.element_id, item)
    elif tag_id == TAG_COMPOUND:
        mapping = value.value if isinstance(value, Compound) else value
        for key, item in mapping.items():
            item_id = _infer_id(item)
            out += struct.pack(">b", item_id)
            _write_string(out, key)
            _write_payload(out, item_id, item)
        out += struct.pack(">b", TAG_END)
    else:
        raise TypeError(f"unsupported tag id {tag_id}")


def dumps(root: Compound, root_name: str = "") -> bytes:
    out = bytearray()
    out += struct.pack(">b", TAG_COMPOUND)
    _write_string(out, root_name)
    _write_payload(out, TAG_COMPOUND, root)
    return bytes(out)


def write_file(path, root: Compound, root_name: str = "") -> int:
    raw = dumps(root, root_name)
    with gzip.GzipFile(filename="", mode="wb", fileobj=open(path, "wb"), mtime=0) as fh:
        fh.write(raw)
    return len(raw)


# ---------------------------------------------------------------------------
# reading (verification only)
# ---------------------------------------------------------------------------

class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u(self, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))[0]

    def string(self) -> str:
        return self.take(self.u(">H")).decode("utf-8", "replace")

    def payload(self, tag_id: int) -> Any:
        if tag_id == TAG_BYTE:
            return self.u(">b")
        if tag_id == TAG_SHORT:
            return self.u(">h")
        if tag_id == TAG_INT:
            return self.u(">i")
        if tag_id == TAG_LONG:
            return self.u(">q")
        if tag_id == TAG_FLOAT:
            return self.u(">f")
        if tag_id == TAG_DOUBLE:
            return self.u(">d")
        if tag_id == TAG_BYTE_ARRAY:
            return list(self.take(self.u(">i")))
        if tag_id == TAG_STRING:
            return self.string()
        if tag_id == TAG_LIST:
            eid = self.u(">b")
            n = self.u(">i")
            return [self.payload(eid) for _ in range(n)]
        if tag_id == TAG_COMPOUND:
            out: dict[str, Any] = {}
            while True:
                tid = self.u(">b")
                if tid == TAG_END:
                    return out
                name = self.string()
                out[name] = self.payload(tid)
        if tag_id == TAG_INT_ARRAY:
            return [self.u(">i") for _ in range(self.u(">i"))]
        if tag_id == TAG_LONG_ARRAY:
            return [self.u(">q") for _ in range(self.u(">i"))]
        raise TypeError(f"unknown tag id {tag_id}")


def read_file(path) -> dict:
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    r = _Reader(raw)
    tid = r.u(">b")
    if tid != TAG_COMPOUND:
        raise ValueError("root tag is not a compound")
    r.string()
    return r.payload(TAG_COMPOUND)
