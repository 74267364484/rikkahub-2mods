# -*- coding: utf-8 -*-
"""正确的 AXML 解析器(用于校验)"""
import struct

def parse(data):
    magic, hsz, total = struct.unpack_from('<HHI', data, 0)
    assert magic == 0x0003 and hsz == 8, (hex(magic), hsz)
    p = 8
    pool = []
    t, hs, sz = struct.unpack_from('<HHI', data, p)
    assert t == 0x0001
    strcount, stylecount, flags, strings_start, styles_start = struct.unpack_from('<IIIII', data, p+8)
    offs = struct.unpack_from('<%dI' % strcount, data, p+28)
    base = p + strings_start
    utf8 = bool(flags & 0x100)
    for o in offs:
        q = base + o
        if utf8:
            n = data[q]; q += 1
            if n & 0x80:
                n = ((n & 0x7f) << 8) | data[q]; q += 1
            ln = data[q]; q += 1
            if ln & 0x80:
                ln = ((ln & 0x7f) << 8) | data[q]; q += 1
            pool.append(data[q:q+ln].decode('utf-8', 'replace'))
        else:
            n = struct.unpack_from('<H', data, q)[0]; q += 2
            if n & 0x8000:
                n = ((n & 0x7fff) << 16) | struct.unpack_from('<H', data, q)[0]; q += 2
            pool.append(data[q:q+n*2].decode('utf-16le', 'replace'))
    p += sz
    out = []
    while p + 8 <= len(data):
        t, hs, sz = struct.unpack_from('<HHI', data, p)
        if sz <= 0:
            break
        if t == 0x0102:  # START_ELEMENT
            ns, name = struct.unpack_from('<II', data, p+16)
            astart, asz, acnt = struct.unpack_from('<HHH', data, p+24)
            attrs = []
            abase = p + 16 + astart
            for i in range(acnt):
                o = abase + i*asz
                a_ns, a_name, a_raw = struct.unpack_from('<III', data, o)
                vsize, res0, vtype, vdata = struct.unpack_from('<HBBI', data, o+12)
                def s(i): return pool[i] if i != 0xFFFFFFFF and i < len(pool) else None
                if vtype == 0x03:
                    val = s(vdata)
                elif vtype == 0x10:
                    val = '#%x' % vdata
                elif vtype == 0x12:
                    val = bool(vdata)
                elif vtype == 0x01:
                    val = '@ref:0x%x' % vdata
                else:
                    val = 'type=0x%x data=0x%x' % (vtype, vdata)
                attrs.append((s(a_name), val))
            out.append(('start', s(ns), s(name), attrs, p))
        elif t == 0x0103:
            ns, name = struct.unpack_from('<II', data, p+16)
            def s(i): return pool[i] if i != 0xFFFFFFFF and i < len(pool) else None
            out.append(('end', s(ns), s(name), [], p))
        p += sz
    return pool, out

def dump(data, only_perms=False, limit=100000):
    pool, nodes = parse(data)
    depth = 0
    n = 0
    for kind, ns, name, attrs, off in nodes:
        if kind == 'start':
            if only_perms and name != 'uses-permission':
                depth += 1
                continue
            a = ' '.join('%s=%r' % (k, v) for k, v in attrs)
            print('  '*depth + '<%s %s> @0x%x' % (name, a, off))
            depth += 1
            n += 1
        else:
            if only_perms and name != 'uses-permission':
                depth -= 1
                continue
            depth -= 1
            n += 1
        if n > limit: break

if __name__ == '__main__':
    import sys, zipfile
    src = sys.argv[1]
    if src.endswith('.apk'):
        d = zipfile.ZipFile(src).read('AndroidManifest.xml')
    else:
        d = open(src, 'rb').read()
    only = len(sys.argv) > 2 and sys.argv[2] == 'perms'
    dump(d, only_perms=only)
