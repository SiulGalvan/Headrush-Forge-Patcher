"""Small ext4 helper on top of the vendored ext4.py."""


def overwrite(fs, path, data):
    """Replace the contents of an existing file with data of exactly the same size, in place: the file's
    own blocks are rewritten, nothing is allocated (ext4.py can only place a file in at most 4 extents, which
    a 40 MB binary may not get if the free space is fragmented)."""
    n = fs.lookup(path)
    ino = bytearray(fs.inode(n))
    size = fs._size(ino)
    if size != len(data):
        raise ValueError("%s: new contents are %d bytes, the file has %d" % (path, len(data), size))
    runs, _ = fs._data_runs(ino)
    bs = fs.bs
    for lblk, pblk, ln in runs:
        seg = data[lblk * bs:(lblk + ln) * bs]
        fs.d[pblk * bs:pblk * bs + len(seg)] = seg
