# -*- coding: utf-8 -*-
"""改写 resources.arsc 里的资源包名(就地覆盖, 长度不变, 仅用于包名共存版)"""
import struct, sys, io

def patch(data, old, new):
    assert len(new) <= 127, '包名过长(arsc 名称字段 128 字符)'
    pat = old.encode('utf-16le')
    i = data.find(pat)
    assert i > 0, '未找到资源包名'
    # 校验: 位于 RES_TABLE_PACKAGE_TYPE(0x0200) 的 name 字段
    p = i - 12
    t, hs, sz = struct.unpack_from('<HHI', data, p)
    assert t == 0x0200, hex(t)
    buf = bytearray(data)
    field = new.encode('utf-16le') + b'\x00' * (256 - len(new.encode('utf-16le')))
    buf[i:i+256] = field
    print('resources.arsc 资源包名: %s -> %s (@0x%x)' % (old, new, i))
    return bytes(buf)

if __name__ == '__main__':
    import zipfile
    apk, out, old, new = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    z = zipfile.ZipFile(apk)
    d = z.read('resources.arsc')
    io.open(out, 'wb').write(patch(d, old, new))
    print('已写出', out, len(d), '字节(长度不变)')
