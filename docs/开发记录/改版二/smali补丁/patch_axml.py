# -*- coding: utf-8 -*-
"""给 AndroidManifest.xml (二进制 AXML) 追加 uses-permission 节点。
做法: 在字符串池尾部追加新字符串(修正 stringsStart/stylesStart/偏移表),
然后在 <manifest> 起始元素之后插入 <uses-permission> 的 start/end 元素块。
"""
import struct, sys, zipfile, io, os

UTF8_FLAG = 1 << 8

class AXML:
    def __init__(self, data):
        self.d = data
        self._parse()

    def _parse(self):
        d = self.d
        magic, size = struct.unpack_from('<II', d, 0)
        assert magic == 0x00080003, hex(magic)
        # string pool
        p = 8
        t, hs, sz = struct.unpack_from('<HHI', d, p)
        assert t == 0x0001, hex(t)
        (strcount, stylecount, flags, strings_start, styles_start) = struct.unpack_from('<IIIII', d, p + 8)
        self.sp_off = p
        self.sp_size = sz
        self.strcount = strcount
        self.stylecount = stylecount
        self.flags = flags
        self.strings_start = strings_start
        self.styles_start = styles_start
        self.offsets = list(struct.unpack_from('<%dI' % strcount, d, p + 28))
        self.style_offsets = list(struct.unpack_from('<%dI' % stylecount, d, p + 28 + strcount * 4)) if stylecount else []
        self.rest = d[p + sz:]            # 其余 chunk(资源表 + 元素树)
        self.total_size = size

    def strings(self):
        out = []
        base = self.sp_off + self.strings_start
        for o in self.offsets:
            q = base + o
            if not (self.flags & UTF8_FLAG):
                n = struct.unpack_from('<H', d2 := self.d, q)[0]
                q += 2
                if n & 0x8000:
                    n = ((n & 0x7FFF) << 16) | struct.unpack_from('<H', self.d, q)[0]
                    q += 2
                out.append(self.d[q:q + n * 2].decode('utf-16le', 'replace'))
            else:
                n = self.d[q]
                q += 1
                if n & 0x80:
                    n = ((n & 0x7F) << 8) | self.d[q]
                    q += 1
                out.append(self.d[q:q + n].decode('utf-8', 'replace'))
        return out

    def add_strings(self, new_strings):
        """返回 (新的字符串池字节, 新字符串的索引列表)"""
        d = self.d
        # 现有字符串数据区(不含 style 数据)
        strdata_start = self.sp_off + self.strings_start
        strdata_end = (self.sp_off + self.styles_start) if self.stylecount else (self.sp_off + self.sp_size)
        strdata = bytearray(d[strdata_start:strdata_end])
        new_offsets = []
        for s in new_strings:
            # 与池保持一致: 若是 UTF-8 池则用 UTF-8 编码, 否则 UTF-16LE
            while len(strdata) % 4 != 0:
                strdata.append(0)
            new_offsets.append(len(strdata))
            if self.flags & UTF8_FLAG:
                b = s.encode('utf-8')
                u16len = len(s.encode('utf-16le')) // 2
                if u16len > 0x7F:
                    strdata += bytes([(u16len >> 8) | 0x80, u16len & 0xFF])
                else:
                    strdata += bytes([u16len])
                if len(b) > 0x7F:
                    strdata += bytes([(len(b) >> 8) | 0x80, len(b) & 0xFF])
                else:
                    strdata += bytes([len(b)])
                strdata += b + b'\x00'
            else:
                b = s.encode('utf-16le')
                n = len(b) // 2
                if n > 0x7FFF:
                    strdata += struct.pack('<HH', ((n >> 16) | 0x8000) & 0xFFFF, n & 0xFFFF)
                else:
                    strdata += struct.pack('<H', n)
                strdata += b + b'\x00\x00'
        while len(strdata) % 4 != 0:
            strdata.append(0)

        add = len(new_strings)
        new_strcount = self.strcount + add
        new_offsets_all = self.offsets + new_offsets
        # 头(28) + 字符串偏移表 + style 偏移表
        head = struct.pack('<HHI', 0x0001, 28, 0)  # size 稍后填
        head += struct.pack('<IIIII', new_strcount, self.stylecount, self.flags, 0, 0)
        off_bytes = b''.join(struct.pack('<I', o) for o in new_offsets_all)
        style_bytes = b''.join(struct.pack('<I', o) for o in self.style_offsets)
        new_strings_start = 28 + 4 * new_strcount + 4 * self.stylecount
        new_styles_start = new_strings_start + len(strdata) if self.stylecount else 0
        styles_data = b''
        if self.stylecount:
            sd_start = self.sp_off + self.styles_start
            styles_data = d[sd_start:self.sp_off + self.sp_size]
        body = off_bytes + style_bytes + bytes(strdata) + styles_data
        size = 28 + len(body)
        head = struct.pack('<HHI', 0x0001, 28, size) + struct.pack('<IIIII', new_strcount, self.stylecount, self.flags, new_strings_start, new_styles_start)
        return head + body, [self.strcount + i for i in range(add)]

def start_element(ns, name, attrs):
    """attrs: list of (ns_idx, name_idx, raw_idx_or_neg, type, data)"""
    n = 16 + 20 + 20 * len(attrs)
    out = struct.pack('<HHI', 0x0102, 16, n)
    out += struct.pack('<II', 0xFFFFFFFF, 0xFFFFFFFF)  # lineNumber, comment
    out += struct.pack('<II', ns, name)
    out += struct.pack('<HHHHHH', 20, 20, len(attrs), 0, 0, 0)
    for (a_ns, a_name, a_raw, a_type, a_data) in attrs:
        out += struct.pack('<III', a_ns, a_name, a_raw)
        out += struct.pack('<HBBI', 8, 0, a_type, a_data)
    return out

def end_element(ns, name):
    out = struct.pack('<HHI', 0x0103, 16, 24)
    out += struct.pack('<II', 0xFFFFFFFF, 0xFFFFFFFF)
    out += struct.pack('<II', ns, name)
    return out

def set_app_label(data, label):
    """把 <application android:label=...> 改成字面量字符串(避免与已安装的同名 APP 混淆)"""
    ax = AXML(data)
    strs = ax.strings()
    idx = {s: i for i, s in enumerate(strs)}
    ANDROID_NS = 'http://schemas.android.com/apk/res/android'
    ns_i = idx[ANDROID_NS]
    new_pool, new_idx = ax.add_strings([label])
    label_i = new_idx[0]
    rest = bytearray(ax.rest)
    p = 0
    done = False
    while p + 8 <= len(rest):
        t, hs, sz = struct.unpack_from('<HHI', rest, p)
        if sz <= 0:
            break
        if t == 0x0102:
            nm = struct.unpack_from('<I', rest, p + 20)[0]
            if nm < len(strs) and strs[nm] == 'application':
                astart, asz, acnt = struct.unpack_from('<HHH', rest, p + 24)
                abase = p + 16 + astart
                for i in range(acnt):
                    o = abase + i * asz
                    a_ns, a_name, a_raw = struct.unpack_from('<III', rest, o)
                    if a_name < len(strs) and strs[a_name] == 'label' and a_ns == ns_i:
                        # 就地改成 string 类型, 指向新字符串
                        struct.pack_into('<I', rest, o + 8, label_i)
                        struct.pack_into('<HBBI', rest, o + 12, 8, 0, 0x03, label_i)
                        done = True
                break
        p += sz
    if not done:
        print('警告: 未找到 application/label, 跳过改名')
        return data
    total = 8 + len(new_pool) + len(rest)
    return struct.pack('<HHI', 0x0003, 0x0008, total) + new_pool + bytes(rest)



# ---- 包名改写(共存版): 只改 package/authorities/自定义权限, 不动类名与 action ----
RENAME_SUFFIXES = (
    'fileprovider', 'documents', 'androidx-startup', 'mlkitinitprovider',
    'firebaseinitprovider', 'floatingx.app.init', 'jlatexmathinitprovider',
    'DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION',
    '_com.google.android.gms.permission.AD_ID',
)


def rename_package(data, old_pkg, new_pkg):
    ax = AXML(data)
    strs = ax.strings()
    wanted = {}
    for s in strs:
        if s == old_pkg:
            wanted[s] = new_pkg
        elif s.startswith(old_pkg + '.'):
            rest = s[len(old_pkg) + 1:]
            if rest in RENAME_SUFFIXES:
                wanted[s] = new_pkg + '.' + rest
        elif s.startswith(old_pkg + '_com.google.android.gms.permission.AD_ID'):
            wanted[s] = new_pkg + s[len(old_pkg):]
    if not wanted:
        print('警告: 没有需要改写的包名字符串')
        return data, 0
    new_pool, new_idx = ax.add_strings([wanted[s] for s in wanted])
    remap = {strs.index(s): new_idx[i] for i, s in enumerate(wanted)}
    rest = bytearray(ax.rest)
    p = 0
    hits = 0
    while p + 8 <= len(rest):
        t, hs, sz = struct.unpack_from('<HHI', rest, p)
        if sz <= 0:
            break
        if t == 0x0102:
            astart, asz, acnt = struct.unpack_from('<HHH', rest, p + 24)
            abase = p + 16 + astart
            for i in range(acnt):
                o = abase + i * asz
                vtype = rest[o + 15]
                vdata = struct.unpack_from('<I', rest, o + 16)[0]
                if vtype == 0x03 and vdata in remap:
                    struct.pack_into('<I', rest, o + 16, remap[vdata])
                    struct.pack_into('<I', rest, o + 8, remap[vdata])   # rawValue 必须一起改, 否则系统仍读旧值
                    hits += 1
        p += sz
    total = 8 + len(new_pool) + len(rest)
    out = struct.pack('<HHI', 0x0003, 0x0008, total) + new_pool + bytes(rest)
    print('包名改写: %s -> %s (替换 %d 处)' % (old_pkg, new_pkg, hits))
    return out, hits



def set_manifest_version(data, version_code=None, version_name=None):
    """改 <manifest> 的 versionCode(整数, 就地改) / versionName(字符串, 追加到池里)"""
    ax = AXML(data)
    strs = ax.strings()
    extra = [version_name] if version_name else []
    new_pool, new_idx = ax.add_strings(extra) if extra else (None, [])
    vname_i = new_idx[0] if extra else None
    rest = bytearray(ax.rest)
    p = 0
    done = 0
    while p + 8 <= len(rest):
        t, hs, sz = struct.unpack_from('<HHI', rest, p)
        if sz <= 0:
            break
        if t == 0x0102:
            nm = struct.unpack_from('<I', rest, p + 20)[0]
            if nm < len(strs) and strs[nm] == 'manifest':
                astart, asz, acnt = struct.unpack_from('<HHH', rest, p + 24)
                abase = p + 16 + astart
                for i in range(acnt):
                    o = abase + i * asz
                    a_name = struct.unpack_from('<I', rest, o + 4)[0]
                    if a_name >= len(strs):
                        continue
                    if strs[a_name] == 'versionCode' and version_code is not None:
                        struct.pack_into('<I', rest, o + 16, version_code)   # 值是 int
                        done += 1
                    elif strs[a_name] == 'versionName' and vname_i is not None:
                        struct.pack_into('<I', rest, o + 8, vname_i)
                        struct.pack_into('<HBBI', rest, o + 12, 8, 0, 0x03, vname_i)
                        done += 1
                break
        p += sz
    if new_pool is None:
        total = 8 + len(data) - 8
        return data
    total = 8 + len(new_pool) + len(rest)
    print('版本信息改写 %d 处' % done)
    return struct.pack('<HHI', 0x0003, 0x0008, total) + new_pool + bytes(rest)


def patch_manifest(data, permissions):
    ax = AXML(data)
    strs = ax.strings()
    idx = {s: i for i, s in enumerate(strs)}
    ANDROID_NS = 'http://schemas.android.com/apk/res/android'
    if ANDROID_NS not in idx:
        raise SystemExit('找不到 android 命名空间字符串')
    if 'name' not in idx:
        raise SystemExit('找不到 name 属性字符串')
    if 'uses-permission' not in idx:
        raise SystemExit('找不到 uses-permission 字符串')
    ns_i = idx[ANDROID_NS]
    name_i = idx['name']
    up_i = idx['uses-permission']

    new_pool, new_idx = ax.add_strings(permissions)
    ins = b''
    for pi in new_idx:
        ins += start_element(0xFFFFFFFF, up_i, [(ns_i, name_i, pi, 0x03, pi)])
        ins += end_element(0xFFFFFFFF, up_i)

    rest = bytearray(ax.rest)
    # 找 <manifest> 起始元素块, 在其后插入
    p = 0
    inserted = False
    while p + 8 <= len(rest):
        t, hs, sz = struct.unpack_from('<HHI', rest, p)
        if sz <= 0:
            break
        if t == 0x0102:
            nm = struct.unpack_from('<I', rest, p + 16 + 4)[0]
            if nm < len(strs) and strs[nm] == 'manifest':
                pos = p + sz
                rest = rest[:pos] + bytearray(ins) + rest[pos:]
                inserted = True
                break
        p += sz
    if not inserted:
        raise SystemExit('未找到 <manifest> 元素')

    total = 8 + len(new_pool) + len(rest)
    out = struct.pack('<HHI', 0x0003, 0x0008, total) + new_pool + bytes(rest)
    return out

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 2:
        raise SystemExit('用法: patch_axml.py <in.apk> <out.xml> [--label 名称] [额外权限...]')
    apk, out_apk = args[0], args[1]
    rest_args = args[2:]
    label = None
    if '--label' in rest_args:
        k = rest_args.index('--label')
        label = rest_args[k + 1]
        rest_args = rest_args[:k] + rest_args[k + 2:]
    newpkg = None
    if '--package' in rest_args:
        k = rest_args.index('--package')
        newpkg = rest_args[k + 1]
        rest_args = rest_args[:k] + rest_args[k + 2:]
    vcode = vname = None
    for flag, key in (('--version-code', 'vcode'), ('--version-name', 'vname')):
        if flag in rest_args:
            k = rest_args.index(flag)
            val = rest_args[k + 1]
            rest_args = rest_args[:k] + rest_args[k + 2:]
            if key == 'vcode':
                vcode = int(val, 0)
            else:
                vname = val
    perms = rest_args or ['android.permission.MANAGE_EXTERNAL_STORAGE',
                          'android.permission.READ_EXTERNAL_STORAGE']
    z = zipfile.ZipFile(apk)
    mf = z.read('AndroidManifest.xml')
    newmf = patch_manifest(mf, perms)
    if newpkg:
        newmf, n = rename_package(newmf, 'me.rerere.rikkahub', newpkg)
        if not n:
            raise SystemExit('包名改写失败')
    if vcode is not None or vname:
        newmf = set_manifest_version(newmf, vcode, vname)
    if label:
        newmf = set_app_label(newmf, label)
        print('应用名 -> %s' % label)
    print('原始 manifest: %d 字节 -> 新: %d 字节' % (len(mf), len(newmf)))
    io.open(out_apk, 'wb').write(newmf)
    print('已写出', out_apk)
