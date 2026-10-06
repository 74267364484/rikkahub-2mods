# -*- coding: utf-8 -*-
"""把 DI 装配处与可写白名单两处补丁也改成"调用新辅助方法"形式"""
import io, os
ROOT='/workspace/apkwork'
def edit(path, old, new, tag):
    p=os.path.join(ROOT,path); s=io.open(p,encoding='utf-8').read()
    assert s.count(old)==1, '%s: %d 处' % (tag, s.count(old))
    io.open(p,'w',encoding='utf-8').write(s.replace(old,new)); print('OK', tag)

# ---------- 1. DI 装配: 内联建列表 -> 调 WorkspaceManager.rikkaWithStorageMounts ----------
edit('smali1/me/rerere/rikkahub/di/ViewModelModuleKt$$ExternalSyntheticLambda1.smali',
'''    new-instance v7, Ljava/util/ArrayList;

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
''',
'''    invoke-static {v0}, Lme/rerere/workspace/WorkspaceManager;->rikkaWithStorageMounts(Ljava/util/List;)Ljava/util/List;

    move-result-object v0
''', 'DI 装配 -> 调辅助方法')

# 追加辅助方法到 WorkspaceManager
p=os.path.join(ROOT,'smali1/me/rerere/workspace/WorkspaceManager.smali')
s=io.open(p,encoding='utf-8').read()
s = s.rstrip('\n') + '''

# ---- RikkaHub patch: 给工作区绑定挂载追加手机存储(/sdcard, /storage) ----
.method public static rikkaWithStorageMounts(Ljava/util/List;)Ljava/util/List;
    .registers 5

    new-instance v0, Ljava/util/ArrayList;

    invoke-direct {v0, p0}, Ljava/util/ArrayList;-><init>(Ljava/util/Collection;)V

    new-instance v1, Ljava/io/File;

    const-string v2, "/storage/emulated/0"

    invoke-direct {v1, v2}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v2, Lme/rerere/workspace/WorkspaceBindMount;

    const-string v3, "/sdcard"

    invoke-direct {v2, v1, v3}, Lme/rerere/workspace/WorkspaceBindMount;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    new-instance v1, Ljava/io/File;

    const-string v2, "/storage"

    invoke-direct {v1, v2}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    new-instance v2, Lme/rerere/workspace/WorkspaceBindMount;

    const-string v3, "/storage"

    invoke-direct {v2, v1, v3}, Lme/rerere/workspace/WorkspaceBindMount;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v0, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    return-object v0
.end method
'''
io.open(p,'w',encoding='utf-8').write(s)
print('OK WorkspaceManager 辅助方法已追加')

# ---------- 2. 可写白名单: 内联建列表 -> 调 WorkspaceToolsKt.rikkaWritableRoots ----------
edit('smali3/me/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt.smali',
'''    const-string v0, "/tmp"

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
    filled-new-array {v2, v0, v1, v3, v4}, [Ljava/lang/String;

    .line 82
    .line 83
    .line 84
    move-result-object v0

    .line 85
    invoke-static {v0}, Lkotlin/uuid/Uuid$Companion;->listOf([Ljava/lang/Object;)Ljava/util/List;

    .line 86
    .line 87
    .line 88
    move-result-object v0

    .line 89
    sput-object v0, Lme/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt;->WRITABLE_ROOT_PREFIXES:Ljava/util/List;''',
'''    invoke-static {}, Lme/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt;->rikkaWritableRoots()Ljava/util/List;

    move-result-object v0

    .line 89
    sput-object v0, Lme/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt;->WRITABLE_ROOT_PREFIXES:Ljava/util/List;''',
'可写白名单 -> 调辅助方法')

p=os.path.join(ROOT,'smali3/me/rerere/rikkahub/data/ai/tools/WorkspaceToolsKt.smali')
s=io.open(p,encoding='utf-8').read()
s = s.rstrip('\n') + '''

# ---- RikkaHub patch: 免审批可写目录(加入手机存储) ----
.method public static rikkaWritableRoots()Ljava/util/List;
    .registers 5

    const-string v0, "/workspace"

    const-string v1, "/tmp"

    const-string v2, "/skills"

    const-string v3, "/sdcard"

    const-string v4, "/storage"

    filled-new-array {v0, v1, v2, v3, v4}, [Ljava/lang/String;

    move-result-object v0

    invoke-static {v0}, Lkotlin/uuid/Uuid$Companion;->listOf([Ljava/lang/Object;)Ljava/util/List;

    move-result-object v0

    return-object v0
.end method
'''
io.open(p,'w',encoding='utf-8').write(s)
print('OK WorkspaceToolsKt 辅助方法已追加')
