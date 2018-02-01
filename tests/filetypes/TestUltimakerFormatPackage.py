# Copyright (c) 2018 Ultimaker B.V.
# Charon is released under the terms of the LGPLv3 or higher.

import io #To create fake streams to write to and read from.
import os.path #To find the resources with test packages.
import pytest #This module contains unit tests.

from Charon.filetypes.UltimakerFormatPackage import UltimakerFormatPackage #The class we're testing.
from Charon.OpenMode import OpenMode #To open archives.

##  Returns an empty package that you can read from.
#
#   The package has no resources at all, so reading from it will not find
#   anything.
@pytest.fixture()
def empty_read_ufp() -> UltimakerFormatPackage:
    result = UltimakerFormatPackage()
    result.openStream(open(os.path.join(os.path.dirname(__file__), "resources", "empty.ufp"), "rb"))
    yield result
    result.close()

##  Returns a package that has a single file in it.
#
#   The file is called "hello.txt" and contains the text "Hello world!" encoded
#   in UTF-8.
@pytest.fixture()
def single_resource_read_ufp() -> UltimakerFormatPackage:
    result = UltimakerFormatPackage()
    result.openStream(open(os.path.join(os.path.dirname(__file__), "resources", "hello.ufp"), "rb"))
    yield result
    result.close()

##  Returns an empty package that you can write to.
#
#   Note that you can't really test the output of the write since you don't have
#   the stream it writes to.
@pytest.fixture()
def empty_write_ufp() -> UltimakerFormatPackage:
    result = UltimakerFormatPackage()
    result.openStream(io.BytesIO(), "application/x-ufp", OpenMode.WriteOnly)
    yield result
    result.close()

#### Now follow the actual tests. ####

##  Tests whether an empty file is recognised as empty.
def test_listPathsEmpty(empty_read_ufp: UltimakerFormatPackage):
    assert len(empty_read_ufp.listPaths()) == 0

##  Tests getting write streams of various resources that may or may not exist.
#
#   Every test will write some arbitrary data to it to see that that also works.
@pytest.mark.parametrize("virtual_path", ["/dir/file", "/file", "dir/file", "file", "/Metadata", "/_rels/.rels"]) #Some extra tests without initial slash to test robustness.
def test_getWriteStream(empty_write_ufp: UltimakerFormatPackage, virtual_path: str):
    stream = empty_write_ufp.getStream(virtual_path)
    stream.write(b"The test is successful.")

##  Tests writing data to an archive, then reading it back.
@pytest.mark.parametrize("virtual_path", ["/dir/file", "/file", "/Metadata"]) #Don't try to read .rels back. That won't work.
def test_cycleSetDataGetData(virtual_path: str):
    test_data = b"Let's see if we can read this data back."

    stream = io.BytesIO()
    package = UltimakerFormatPackage()
    package.openStream(stream, mode = OpenMode.WriteOnly)
    package.setData({virtual_path: test_data})
    package.close()

    stream.seek(0)
    package = UltimakerFormatPackage()
    package.openStream(stream)
    result = package.getData(virtual_path)

    assert len(result) == 1 #This data must be the only data we've found.
    assert virtual_path in result #The path must be in the dictionary.
    assert result[virtual_path] == test_data #The data itself is still correct.

##  Tests writing data via a stream to an archive, then reading it back via a
#   stream.
@pytest.mark.parametrize("virtual_path", ["/dir/file", "/file", "/Metadata"])
def test_cycleStreamWriteRead(virtual_path: str):
    test_data = b"Softly does the river flow, flow, flow."

    stream = io.BytesIO()
    package = UltimakerFormatPackage()
    package.openStream(stream, mode = OpenMode.WriteOnly)
    resource = package.getStream(virtual_path)
    resource.write(test_data)
    package.close()

    stream.seek(0)
    package = UltimakerFormatPackage()
    package.openStream(stream)
    resource = package.getStream(virtual_path)
    result = resource.read()

    assert result == test_data

##  Tests setting metadata in an archive, then reading that metadata back.
@pytest.mark.parametrize("virtual_path", ["/Metadata/some/global/setting", "/hello.txt/test", "/also/global/entry"])
def test_cycleSetMetadataGetMetadata(virtual_path: str):
    test_data = "Hasta la vista, baby."

    stream = io.BytesIO()
    package = UltimakerFormatPackage()
    package.openStream(stream, mode = OpenMode.WriteOnly)
    package.setData({"/hello.txt": b"Hello world!"}) #Add a file to attach non-global metadata to.
    package.setMetadata({virtual_path: test_data})
    package.close()

    stream.seek(0)
    package = UltimakerFormatPackage()
    package.openStream(stream)
    result = package.getMetadata(virtual_path)

    assert len(result) == 1 #Only one metadata entry was set.
    assert virtual_path in result #And it was the correct entry.
    assert result[virtual_path] == test_data #With the correct value.

##  Tests toByteArray with its parameters.
#
#   This doesn't test if the bytes are correct, because that is the task of the
#   zipfile module. We merely test that it gets some bytes array and that the
#   offset and size parameters work.
def test_toByteArray(single_resource_read_ufp):
    original = single_resource_read_ufp.toByteArray()
    original_length = len(original)

    #Even empty zip archives are already 22 bytes, so offsets and sizes of less than that should be okay.
    result = single_resource_read_ufp.toByteArray(offset = 10)
    assert len(result) == original_length - 10 #The first 10 bytes have fallen off.

    result = single_resource_read_ufp.toByteArray(count = 8)
    assert len(result) == 8 #Limited to size 8.

    result = single_resource_read_ufp.toByteArray(offset = 10, count = 8)
    assert len(result) == 8 #Still limited by the size, even though there is an offset.

    result = single_resource_read_ufp.toByteArray(count = 999999) #This is a small file, definitely smaller than 1MiB.
    assert len(result) == original_length #Should be limited to the actual file length.