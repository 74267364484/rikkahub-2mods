# -*- coding: utf-8 -*-
"""RikkaHub 2.5.6 (me.rerere.rikkahuc) smali 补丁
1) 手机存储绑定挂载：/storage/emulated/0 -> /sdcard, /storage -> /storage
2) 工作区文件区可指向手机存储目录（配置文件 /storage/emulated/0/RikkaHub/workspace_base.txt）
3) 手机存储目录免审批写入（WRITABLE_ROOT_PREFIXES）
4) rootfs 内预建挂载点目录
"""
import io, sys, os

ROOT = '/workspace/apkwork'
SM1, SM2, SM3 = ROOT + '/smali1', ROOT + '/smali2', ROOT + '/smali3'

def patch(path, old, new, tag, count=1):
    p = os.path.join(ROOT, path)
    s = io.open(p, encoding='utf-8').read()
    n = s.count(old)
    if n != count:
        print('!! [%s] 期望 %d 处匹配, 实际 %d 处 -> %s' % (tag, count, n, path))
        return False
    s = s.replace(old, new)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('OK [%s] %s' % (tag, path))
    return True

ok = True

# ---------------- P-A: WorkspaceManager.filesDir ----------------
old_filesdir = '''.method public final filesDir(Ljava/lang/String;)Ljava/io/File;
    .registers 3

    .line 1
    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    .line 2
    .line 3
    .line 4
    new-instance v0, Ljava/io/File;

    .line 5
    .line 6
    invoke-virtual {p0, p1}, Lme/rerere/workspace/WorkspaceManager;->workspaceDir(Ljava/lang/String;)Ljava/io/File;

    .line 7
    .line 8
    .line 9
    move-result-object p0

    .line 10
    const-string p1, "files"

    .line 11
    .line 12
    invoke-direct {v0, p0, p1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    .line 13
    .line 14
    .line 15
    return-object v0'''

new_filesdir = '''.method public final filesDir(Ljava/lang/String;)Ljava/io/File;
    .registers 5

    invoke-static {}, Lme/rerere/workspace/WorkspaceManager;->externalFilesBase()Ljava/io/File;

    move-result-object v0

    if-eqz v0, :rikka_files_fallback

    new-instance v1, Ljava/io/File;

    invoke-direct {v1, v0, p1}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    return-object v1

    :rikka_files_fallback
    invoke-virtual {p0, p1}, Lme/rerere/workspace/WorkspaceManager;->workspaceDir(Ljava/lang/String;)Ljava/io/File;

    move-result-object v0

    new-instance v1, Ljava/io/File;

    const-string v2, "files"

    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    return-object v1'''

ok &= patch('smali1/me/rerere/workspace/WorkspaceManager.smali', old_filesdir, new_filesdir, 'filesDir')

# ---------------- P-B: 追加 externalFilesBase() ----------------
helper = '''
# ---- RikkaHub patch: 工作区文件区外部根目录(手机存储) ----
# 读取 /storage/emulated/0/RikkaHub/workspace_base.txt (内容为一个绝对路径),
# 若存在且非空, 则该目录作为工作区文件区的父目录, 否则使用应用私有目录。
.method public static externalFilesBase()Ljava/io/File;
    .registers 5

    const/4 v0, 0x0

    :rikka_try_start
    new-instance v1, Ljava/io/File;

    const-string v2, "/storage/emulated/0/RikkaHub/workspace_base.txt"

    invoke-direct {v1, v2}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-virtual {v1}, Ljava/io/File;->isFile()Z

    move-result v2

    if-eqz v2, :rikka_ret

    invoke-virtual {v1}, Ljava/io/File;->toPath()Ljava/nio/file/Path;

    move-result-object v1

    invoke-static {v1}, Ljava/nio/file/Files;->readAllBytes(Ljava/nio/file/Path;)[B

    move-result-object v1

    new-instance v2, Ljava/lang/String;

    sget-object v3, Ljava/nio/charset/StandardCharsets;->UTF_8:Ljava/nio/charset/Charset;

    invoke-direct {v2, v1, v3}, Ljava/lang/String;-><init>([BLjava/nio/charset/Charset;)V

    invoke-virtual {v2}, Ljava/lang/String;->trim()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/String;->isEmpty()Z

    move-result v3

    if-eqz v3, :rikka_ret

    const-string v3, "/"

    invoke-virtual {v2, v3}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v3

    if-eqz v3, :rikka_ret

    new-instance v0, Ljava/io/File;

    invoke-direct {v0, v2}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    :rikka_try_end
    :rikka_ret
    return-object v0

    :rikka_catch
    const/4 v0, 0x0

    return-object v0

    .catch Ljava/lang/Throwable; {:rikka_try_start .. :rikka_try_end} :rikka_catch
.end method
'''

p = os.path.join(ROOT, 'smali1/me/rerere/workspace/WorkspaceManager.smali')
s = io.open(p, encoding='utf-8').read()
s = s.rstrip('\n') + '\n' + helper
io.open(p, 'w', encoding='utf-8').write(s)
print('OK [externalFilesBase] 已追加辅助方法')

# ---------------- P-C: DI 装配处追加手机存储 bind mount ----------------
old_di = '''    move-result-object v0

    .line 206
    new-instance v3, Lme/rerere/workspace/WorkspaceManager;'''

new_di = '''    move-result-object v0

    new-instance v7, Ljava/util/ArrayList;

    invoke-direct {v7, v0}, Ljava/util/ArrayList;-><init>(Ljava/util/Collection;)V

    new-instance v8, Ljava/io/File;

    const-string v9, "/storage/emulated/0"

    invoke-direct {v8, v9}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v9, Lme/rerere/workspace/WorkspaceBindMount;

    const-string v10, "/sdcard"

    invoke-direct {v9, v8, v10}, Lme/rerere/workspace/WorkspaceBindMount;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v7, v9}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    new-instance v8, Ljava/io/File;

    const-string v9, "/storage"

    invoke-direct {v8, v9}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v9, Lme/rerere/workspace/WorkspaceBindMount;

    const-string v10, "/storage"

    invoke-direct {v9, v8, v10}, Lme/rerere/workspace/WorkspaceBindMount;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v7, v9}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    move-object v0, v7

    .line 206
    new-instance v3, Lme/rerere/workspace/WorkspaceManager;'''

ok &= patch('smali1/me/rerere/rikkahub/di/ViewModelModuleKt$$ExternalSyntheticLambda1.smali', old_di, new_di, 'DI bind mounts')

# ---------------- P-D: rootfs 预建挂载点目录 ----------------
old_dirs = '''    :goto_45d
    const-string v1, "tmp"

    .line 1119
    .line 1120
    const-string v2, "var/tmp"

    .line 1121
    .line 1122
    const-string v3, "root"

    .line 1123
    .line 1124
    filled-new-array {v1, v2, v3}, [Ljava/lang/String;'''

new_dirs = '''    :goto_45d
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
    filled-new-array {v1, v2, v3, v6, v7}, [Ljava/lang/String;'''

ok &= patch('smali1/me/rerere/workspace/RootfsPatcher.smali', old_dirs, new_dirs, 'rootfs 挂载点目录')

# ---------------- P-E: 免审批写入白名单 ----------------
old_wr = '''    const-string v0, "/tmp"

    .line 76
    .line 77
    const-string v1, "/skills"

    .line 78
    .line 79
    const-string v2, "/workspace"

    .line 80
    .line 81
    filled-new-array {v2, v0, v1}, [Ljava/lang/String;'''

new_wr = '''    const-string v0, "/tmp"

    .line 76
    .line 77
    const-string v1, "/skills"

    .line 78
    .line 79
    const-string v2, "/workspace"

    const-string v3, "/sdcard"

    const-string v4, "/storage"

    .line 80
    .line 81
    filled-new-array {v2, v0, v1, v3, v4}, [Ljava/lang/String;'''

ok &= patch('smali3/me/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt.smali', old_wr, new_wr, '可写白名单')

# ---------------- P-F: 内置终端 proot 命令追加手机存储挂载 ----------------
old_term = '''    :cond_d4
    const-string v16, "SHELL=/bin/bash"'''

new_term = '''    :cond_d4
    const-string v5, "-b"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "/storage/emulated/0:/sdcard"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "-b"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v5, "/storage"

    invoke-virtual {v1, v5}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    const-string v16, "SHELL=/bin/bash"'''

ok &= patch('smali3/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceTerminalSessionKt.smali', old_term, new_term, '终端挂载')

print('\n=== 全部补丁 %s ===' % ('成功' if ok else '有失败项'))
sys.exit(0 if ok else 1)
