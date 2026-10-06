# -*- coding: utf-8 -*-
"""① 改工作区注入提示词/工具描述(让模型知道 /sdcard 是真实存储)
   ② 工作台文件区默认落在手机存储目录(可用 workspace_base.txt 覆盖, 不可用时回退私有目录)"""
import io, os
ROOT = '/workspace/apkwork'

def edit(path, old, new, tag):
    p = os.path.join(ROOT, path)
    s = io.open(p, encoding='utf-8').read()
    assert s.count(old) == 1, '%s: %d 处' % (tag, s.count(old))
    io.open(p, 'w', encoding='utf-8').write(s.replace(old, new))
    print('OK', tag)

PHONE_NOTE = (" The user\\'s REAL phone storage is mounted read-write at /sdcard "
              "(= /storage/emulated/0) and /storage; absolute paths there are valid, "
              "e.g. /sdcard/Download/a.txt (hidden files included). "
              "手机真实存储已挂载在 /sdcard 与 /storage, 可直接读写(相册/下载/文档等)。")

RTK = 'smali3/me/rerere/rikkahub/data/ai/transformers/WorkspaceReminderTransformerKt.smali'

# ---- ① 注入提示词 ----
edit(RTK,
     'const-string p0, "\\", running in a sandboxed proot rootfs environment."',
     'const-string p0, "\\", running in a proot rootfs environment with the user\\\'s REAL phone storage '
     'mounted read-write at /sdcard (= /storage/emulated/0) and /storage."',
     '提示词: 首句')

old_block = ('\\n- All paths passed to workspace tools must be absolute and inside the Rootfs '
             '(for example `/workspace/notes.md`).')
new_block = (
    '\\n- The user\\\'s REAL phone storage is mounted read-write: `/sdcard` (identical to `/storage/emulated/0`: '
    'DCIM, Download, Documents, Pictures, Movies, Music, Android/media, ...) and `/storage` (whole storage incl. SD card). '
    'These are the user\\\'s actual device directories - read and write them directly: `workspace_read_file` with path '
    '`/sdcard/Download/a.txt`, `workspace_shell` with command `ls -a /sdcard/DCIM`, `cp /sdcard/DCIM/1.jpg /workspace/`. '
    'Hidden files and folders (names starting with `.`) are visible too. NEVER claim you cannot see the user\\\'s device files: '
    '`/sdcard` IS the device storage. 手机真实存储已挂载: /sdcard 与 /storage 就是手机上的真实目录, '
    '可直接读写(相册/下载/文档等), 隐藏文件也可见。'
    '\\n- All paths passed to workspace tools must be absolute; use `/workspace` for the workspace files area, '
    '`/sdcard` or `/storage/...` for the phone\\\'s real storage (for example `/workspace/notes.md`, `/sdcard/Download/a.txt`).')
edit(RTK, old_block, new_block, '提示词: 路径说明')

# ---- ② 工具描述: 在指定锚点字符串的结尾引号前插入 ----
TOOLS = 'smali3/me/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt.smali'
anchors = [
    ('读取工具描述', '\\nSupports UTF-8 text files and image files (png, jpg, jpeg, gif, webp, bmp, svg, heic, heif, avif, ico)."'),
    ('写入工具描述', '\\nUse /workspace for the workspace files area."'),
    ('编辑工具描述', '\\nIf no exact match is found, whitespace-tolerant line matching is attempted automatically."'),
    ('shell 工具描述', 'Use cwd for a path relative to the workspace files root. "'),
]
for tag, anchor in anchors:
    p = os.path.join(ROOT, TOOLS)
    s = io.open(p, encoding='utf-8').read()
    i = s.find(anchor)
    assert i > 0, tag
    j = s.index('"', i)          # 锚点字符串结尾的引号
    s = s[:j] + PHONE_NOTE + s[j:]
    io.open(p, 'w', encoding='utf-8').write(s)
    print('OK', tag)

edit(TOOLS,
     'const-string v2, "Absolute path inside Rootfs. Use /workspace for the workspace files area."',
     'const-string v2, "Absolute path inside Rootfs. Use /workspace for the workspace files area, or /sdcard '
     '(= /storage/emulated/0) / /storage for the user\\\'s real phone storage (hidden files included)."',
     'path 参数描述')

# ---- ③ filesDir: 可用性校验 + 默认落到手机存储 ----
p = os.path.join(ROOT, 'smali1/me/rerere/workspace/WorkspaceManager.smali')
s = io.open(p, encoding='utf-8').read()
old_fd = '''    new-instance v2, Ljava/io/File;

    invoke-direct {v2, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    return-object v2

    :rikka_files_direct
    new-instance v1, Ljava/io/File;

    invoke-direct {v1, v0, p1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    return-object v1

    :rikka_files_fallback'''
new_fd = '''    new-instance v2, Ljava/io/File;

    invoke-direct {v2, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    goto :rikka_files_verify

    :rikka_files_direct
    new-instance v2, Ljava/io/File;

    invoke-direct {v2, v0, p1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    :rikka_files_verify
    invoke-virtual {v2}, Ljava/io/File;->mkdirs()Z

    invoke-virtual {v2}, Ljava/io/File;->isDirectory()Z

    move-result v1

    if-eqz v1, :rikka_files_fallback

    return-object v2

    :rikka_files_fallback'''
assert s.count(old_fd) == 1
s = s.replace(old_fd, new_fd)

old_default = '''    const/4 v0, 0x0

    :rikka_try_start
    new-instance v1, Ljava/io/File;

    const-string v2, "/storage/emulated/0/RikkaHub/workspace_base.txt"'''
new_default = '''    new-instance v0, Ljava/io/File;

    const-string v1, "/storage/emulated/0/RikkaHub/workspaces"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    :rikka_try_start
    new-instance v1, Ljava/io/File;

    const-string v2, "/storage/emulated/0/RikkaHub/workspace_base.txt"'''
assert s.count(old_default) == 1
s = s.replace(old_default, new_default)

old_catch = '''    :rikka_catch
    const/4 v0, 0x0

    return-object v0

    .catch Ljava/lang/Throwable; {:rikka_try_start .. :rikka_try_end} :rikka_catch'''
new_catch = '''    :rikka_catch
    new-instance v0, Ljava/io/File;

    const-string v1, "/storage/emulated/0/RikkaHub/workspaces"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    return-object v0

    .catch Ljava/lang/Throwable; {:rikka_try_start .. :rikka_try_end} :rikka_catch'''
assert s.count(old_catch) == 1
s = s.replace(old_catch, new_catch)
io.open(p, 'w', encoding='utf-8').write(s)
print('OK filesDir 可用性校验 + 默认手机存储目录')
