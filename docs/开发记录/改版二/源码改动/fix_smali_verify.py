# -*- coding: utf-8 -*-
"""把两处"内联改寄存器"的补丁改成"调用新辅助方法", 避免 ART 校验器报 VerifyError"""
import io, os
ROOT='/workspace/apkwork'
def edit(path, old, new, tag, cnt=1):
    p=os.path.join(ROOT,path); s=io.open(p,encoding='utf-8').read()
    n=s.count(old)
    assert n==cnt, '%s: 期望 %d 处, 实际 %d' % (tag, cnt, n)
    io.open(p,'w',encoding='utf-8').write(s.replace(old,new))
    print('OK', tag)

# ---------- 1. RootfsPatcher: 撤销改数组, 改为调用辅助方法 ----------
edit('smali1/me/rerere/workspace/RootfsPatcher.smali',
'''    :goto_45d
    const-string v1, "tmp"

    .line 1119
    .line 1120
    const-string v2, "var/tmp"

    .line 1121
    .line 1122
    const-string v3, "root"

    const-string v6, "storage/emulated/0"

    const-string v7, "sdcard"

    .line 1123
    .line 1124
    filled-new-array {v1, v2, v3, v6, v7}, [Ljava/lang/String;''',
'''    :goto_45d
    invoke-static {v0}, Lme/rerere/workspace/RootfsPatcher;->rikkaEnsureStorageDirs(Ljava/io/File;)V

    const-string v1, "tmp"

    .line 1119
    .line 1120
    const-string v2, "var/tmp"

    .line 1121
    .line 1122
    const-string v3, "root"

    .line 1123
    .line 1124
    filled-new-array {v1, v2, v3}, [Ljava/lang/String;''',
'RootfsPatcher 改数组 -> 调辅助方法')

# 追加辅助方法(在类末尾)
p=os.path.join(ROOT,'smali1/me/rerere/workspace/RootfsPatcher.smali')
s=io.open(p,encoding='utf-8').read()
s = s.rstrip('\n') + '''

# ---- RikkaHub patch: 预建手机存储挂载点目录(/sdcard, /storage/emulated/0) ----
.method public static rikkaEnsureStorageDirs(Ljava/io/File;)V
    .registers 4

    new-instance v0, Ljava/io/File;

    const-string v1, "storage/emulated/0"

    invoke-direct {v0, p0, v1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->mkdirs()Z

    new-instance v0, Ljava/io/File;

    const-string v1, "sdcard"

    invoke-direct {v0, p0, v1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->mkdirs()Z

    new-instance v0, Ljava/io/File;

    const-string v1, "storage/self"

    invoke-direct {v0, p0, v1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->mkdirs()Z

    return-void
.end method
'''
io.open(p,'w',encoding='utf-8').write(s)
print('OK RootfsPatcher 辅助方法已追加')

# ---------- 2. 终端: 撤销内联代码, 改为调用辅助方法 ----------
edit('smali3/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceTerminalSessionKt.smali',
'''    :cond_d4
    new-instance v5, Ljava/io/File;

    const-string v6, "/storage/emulated/0"

    invoke-direct {v5, v6}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v5}, Ljava/io/File;->exists()Z

    move-result v5

    if-eqz v5, :rikka_term_no_storage

    const-string v5, "-b"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "/storage/emulated/0:/sdcard"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "-b"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "/storage"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    :rikka_term_no_storage
    const-string v16, "SHELL=/bin/bash"''',
'''    :cond_d4
    invoke-static {v1}, Lme/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceTerminalSessionKt;->rikkaAddStorageMounts(Ljava/util/List;)V

    const-string v16, "SHELL=/bin/bash"''',
'终端内联 -> 调辅助方法')

p=os.path.join(ROOT,'smali3/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceTerminalSessionKt.smali')
s=io.open(p,encoding='utf-8').read()
s = s.rstrip('\n') + '''

# ---- RikkaHub patch: 终端 proot 命令追加手机存储挂载 ----
.method public static rikkaAddStorageMounts(Ljava/util/List;)V
    .registers 3

    new-instance v0, Ljava/io/File;

    const-string v1, "/storage/emulated/0"

    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/io/File;->exists()Z

    move-result v0

    if-eqz v0, :rikka_term_done

    const-string v0, "-b"

    invoke-interface {p0, v0}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    const-string v0, "/storage/emulated/0:/sdcard"

    invoke-interface {p0, v0}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    const-string v0, "-b"

    invoke-interface {p0, v0}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    const-string v0, "/storage"

    invoke-interface {p0, v0}, Ljava/util/List;->add(Ljava/lang/Object;)Z

    :rikka_term_done
    return-void
.end method
'''
io.open(p,'w',encoding='utf-8').write(s)
print('OK 终端辅助方法已追加')
