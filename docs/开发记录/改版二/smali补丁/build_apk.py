# -*- coding: utf-8 -*-
"""重建 APK: 替换 dex / AndroidManifest.xml, 保持原条目顺序与压缩方式, 未压缩条目 4 字节对齐。"""
import struct, zlib, zipfile, os, sys, io

import json
SRC = os.environ.get('SRC_APK', '/workspace/RikkaHub_2.5.6.apk')
VARIANT = os.environ.get('BUILD_VARIANT', 'coexist')
OUT = os.environ.get('OUT_APK', '/workspace/apkwork/RikkaHub_2.5.6-mod-unsigned.apk')
_cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replace-%s.json' % VARIANT)))
REPLACE = {k: (v if os.path.isabs(v) else os.path.join('/workspace/apkwork', v)) for k, v in _cfg.items()}

def dos_time(dt):
    return (dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2), (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]

def main():
    z = zipfile.ZipFile(SRC)
    src = open(SRC, 'rb')
    out = open(OUT, 'wb')
    central = []
    replaced = set()
    for info in z.infolist():
        name = info.filename
        raw = z.read(name)
        if name in REPLACE:
            raw = open(REPLACE[name], 'rb').read()
            replaced.add(name)
        method = info.compress_type
        crc = zlib.crc32(raw) & 0xFFFFFFFF
        usize = len(raw)
        if method == 8:
            co = zlib.compressobj(9, zlib.DEFLATED, -15)
            payload = co.compress(raw) + co.flush()
        else:
            payload = raw
        csize = len(payload)
        extra = info.extra or b''
        nameb = name.encode('utf-8')
        offset = out.tell()
        # 未压缩条目按 4 字节对齐数据起点
        pad = b''
        if method == 0:
            dstart = offset + 30 + len(nameb) + len(extra)
            need = (-dstart) % 4
            if need:
                pad = b'\x00' * need
                # 让 extra 长度字段随之增长
                extra_used = extra + pad
            else:
                extra_used = extra
        else:
            extra_used = extra
        dstart = offset + 30 + len(nameb) + len(extra_used)
        assert method != 0 or dstart % 4 == 0, (name, dstart)
        flag = 0
        t, d = dos_time(info.date_time)
        lh = struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, flag, method, t, d, crc, csize, usize,
                         len(nameb), len(extra_used))
        out.write(lh)
        out.write(nameb)
        out.write(extra_used)
        assert out.tell() == dstart
        out.write(payload)
        central.append((nameb, method, t, d, crc, csize, usize, len(extra_used), extra_used, offset,
                        info.external_attr, info.create_system, info.internal_attr))

    cd_start = out.tell()
    for (nameb, method, t, d, crc, csize, usize, elen, extra, offset, extattr, csys, iattr) in central:
        out.write(struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, (csys << 8) | 20, 20, 0, method, t, d,
                              crc, csize, usize, len(nameb), elen, 0, 0, iattr, extattr, offset))
        out.write(nameb)
        out.write(extra)
    cd_size = out.tell() - cd_start
    n = len(central)
    out.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, n, n, cd_size, cd_start, 0))
    out.close()
    print('写出 %s (%.1f MB), 条目 %d, 替换 %s' % (OUT, os.path.getsize(OUT) / 1048576.0, n, sorted(replaced)))
    missing = set(REPLACE) - replaced
    if missing:
        print('!! 未替换:', missing); sys.exit(1)

main()
