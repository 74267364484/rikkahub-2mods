# -*- coding: utf-8 -*-
"""RikkaHub Mod 源码改动: 手机存储读写 + 权限申请 + 文件夹选择器"""
import io, os, sys
ROOT = '/workspace/build/src/rikkahub-2.5.6'

def edit(path, old, new, tag, cnt=1):
    p = os.path.join(ROOT, path)
    s = io.open(p, encoding='utf-8').read()
    n = s.count(old)
    assert n == cnt, '[%s] 期望 %d 处, 实际 %d' % (tag, cnt, n)
    io.open(p, 'w', encoding='utf-8').write(s.replace(old, new))
    print('OK', tag)

# ============ 1. WorkspaceManager: 文件区可指向手机存储 ============
edit('workspace/src/main/java/me/rerere/workspace/WorkspaceManager.kt',
'''    fun filesDir(root: String): File = File(workspaceDir(root), FILES_DIR)''',
'''    fun filesDir(root: String): File {
        // RikkaHub Mod: 工作区文件区优先落在手机存储上(可用 workspace_base.txt 自定义),
        // 取不到权限/不可用时回退到 APP 私有目录。
        val base = storageBase()
        val target = if (base.contains(STORAGE_ROOT_PLACEHOLDER)) {
            File(base.replace(STORAGE_ROOT_PLACEHOLDER, root))
        } else {
            File(base, root)
        }
        if (target.mkdirs() || target.isDirectory) return target
        return File(workspaceDir(root), FILES_DIR)
    }''', 'WorkspaceManager.filesDir')

edit('workspace/src/main/java/me/rerere/workspace/WorkspaceManager.kt',
'''        /** Rootfs 内工作区文件区的挂载点 */
        const val ROOTFS_WORKSPACE_DIR = "/workspace"''',
'''        /** Rootfs 内工作区文件区的挂载点 */
        const val ROOTFS_WORKSPACE_DIR = "/workspace"

        /** 手机存储上的工作区根目录配置文件(内容为一行绝对路径) */
        const val STORAGE_BASE_CONFIG_PATH = "/storage/emulated/0/RikkaHub/workspace_base.txt"

        /** 默认: 手机存储上的工作区目录, 每个工作区一个子目录 */
        const val DEFAULT_STORAGE_BASE = "/storage/emulated/0/RikkaHub/workspaces"

        /** 路径中可用 {root} 占位符表示"每个工作区一个子目录" */
        const val STORAGE_ROOT_PLACEHOLDER = "{root}"

        /** 读取用户配置的工作区根目录(无配置/不可读时返回默认值) */
        fun storageBase(): String = runCatching {
            val f = File(STORAGE_BASE_CONFIG_PATH)
            if (!f.isFile) return@runCatching DEFAULT_STORAGE_BASE
            f.readText().trim().takeIf { it.isNotEmpty() && it.startsWith("/") } ?: DEFAULT_STORAGE_BASE
        }.getOrDefault(DEFAULT_STORAGE_BASE)

        /** 写入/清除工作区根目录配置; path 为 null 或空白表示恢复默认 */
        fun setStorageBase(path: String?): Boolean = runCatching {
            val f = File(STORAGE_BASE_CONFIG_PATH)
            if (path.isNullOrBlank()) {
                f.delete()
            } else {
                f.parentFile?.mkdirs()
                f.writeText(path.trim() + "\\n")
            }
            true
        }.getOrDefault(false)''', 'WorkspaceManager companion')

# ============ 2. RootfsPatcher: 预建挂载点目录 ============
edit('workspace/src/main/java/me/rerere/workspace/RootfsPatcher.kt',
'''        listOf("tmp", "var/tmp", "root").forEach { path ->
            File(linuxDir, path).mkdirs()
        }''',
'''        // RikkaHub Mod: 预建手机存储挂载点(/sdcard, /storage/emulated/0)
        listOf("tmp", "var/tmp", "root", "sdcard", "storage/emulated/0", "storage/self").forEach { path ->
            File(linuxDir, path).mkdirs()
        }''', 'RootfsPatcher.ensureTempDirs')

# ============ 3. DI: 绑定挂载手机存储 ============
edit('app/src/main/java/me/rerere/rikkahub/di/RepositoryModule.kt',
'''                WorkspaceBindMount(
                    source = File(context.filesDir, FileFolders.UPLOAD).apply { mkdirs() },
                    target = "/upload",
                ),
            ),''',
'''                WorkspaceBindMount(
                    source = File(context.filesDir, FileFolders.UPLOAD).apply { mkdirs() },
                    target = "/upload",
                ),
                // RikkaHub Mod: 手机真实存储(需要「所有文件访问权限」)
                WorkspaceBindMount(
                    source = File("/storage/emulated/0"),
                    target = "/sdcard",
                ),
                WorkspaceBindMount(
                    source = File("/storage"),
                    target = "/storage",
                ),
            ),''', 'RepositoryModule bindMounts')

# ============ 4. 工具描述 + 可写白名单 ============
edit('app/src/main/java/me/rerere/rikkahub/data/ai/tools/WorkspaceTools.kt',
'''private val WRITABLE_ROOT_PREFIXES = listOf("/workspace", "/tmp", "/skills")''',
'''private val WRITABLE_ROOT_PREFIXES = listOf("/workspace", "/tmp", "/skills", "/sdcard", "/storage")

private const val PHONE_STORAGE_NOTE =
    " The user's REAL phone storage is mounted read-write at /sdcard (= /storage/emulated/0) " +
        "and /storage; absolute paths there are valid, e.g. /sdcard/Download/a.txt (hidden files included)."''', 'WRITABLE_ROOT_PREFIXES')

for tag, anchor in [
    ('read 描述', '\\nSupports UTF-8 text files and image files (png, jpg, jpeg, gif, webp, bmp, svg, heic, heif, avif, ico)."'),
    ('write 描述', '\\nUse /workspace for the workspace files area."'),
    ('edit 描述', '\\nIf no exact match is found, whitespace-tolerant line matching is attempted automatically."'),
    ('shell 描述', 'Use cwd for a path relative to the workspace files root. "'),
]:
    p = os.path.join(ROOT, 'app/src/main/java/me/rerere/rikkahub/data/ai/tools/WorkspaceTools.kt')
    s = io.open(p, encoding='utf-8').read()
    i = s.find(anchor)
    assert i > 0, tag
    j = s.index('"', i)
    s = s[:j] + ' ${PHONE_STORAGE_NOTE}"'.replace('"', '') + s[j:] if False else s[:j] + '" + PHONE_STORAGE_NOTE + "' + s[j:]
    io.open(p, 'w', encoding='utf-8').write(s)
    print('OK', tag)

edit('app/src/main/java/me/rerere/rikkahub/data/ai/tools/WorkspaceTools.kt',
'''                "Absolute path inside Rootfs. Use /workspace for the workspace files area."''',
'''                "Absolute path inside Rootfs. Use /workspace for the workspace files area, " +
                    "or /sdcard (= /storage/emulated/0) / /storage for the user's real phone storage (hidden files included)."''',
'path 参数描述')

# ============ 5. 注入提示词 ============
edit('app/src/main/java/me/rerere/rikkahub/data/ai/transformers/WorkspaceReminderTransformer.kt',
'''    appendLine("You have access to a persistent Linux workspace named \\"${workspace.name}\\", running in a sandboxed proot rootfs environment.")
    appendLine("- The workspace files area is mounted at `/workspace`. Use it as your working directory; files written there persist across turns of this conversation.")
    appendLine("- All paths passed to workspace tools must be absolute and inside the Rootfs (for example `/workspace/notes.md`).")''',
'''    appendLine("You have access to a persistent Linux workspace named \\"${workspace.name}\\", running in a proot rootfs environment with the user's REAL phone storage mounted read-write at /sdcard (= /storage/emulated/0) and /storage.")
    appendLine("- The workspace files area is mounted at `/workspace`. Use it as your working directory; files written there persist across turns of this conversation.")
    appendLine("- The user's REAL phone storage is mounted read-write: `/sdcard` (identical to `/storage/emulated/0`: DCIM, Download, Documents, Pictures, Movies, Music, Android/media, ...) and `/storage` (whole storage incl. SD card). These are the user's actual device directories - read and write them directly: `workspace_read_file` with path `/sdcard/Download/a.txt`, `workspace_shell` with command `ls -a /sdcard/DCIM`, `cp /sdcard/DCIM/1.jpg /workspace/`. Hidden files and folders (names starting with `.`) are visible too. NEVER claim you cannot see the user's device files: `/sdcard` IS the device storage. 手机真实存储已挂载: /sdcard 与 /storage 就是手机上的真实目录, 可直接读写(相册/下载/文档等), 隐藏文件也可见。")
    appendLine("- All paths passed to workspace tools must be absolute; use `/workspace` for the workspace files area, `/sdcard` or `/storage/...` for the phone's real storage (for example `/workspace/notes.md`, `/sdcard/Download/a.txt`).")''',
'注入提示词')

# ============ 6. 终端挂载 ============
edit('app/src/main/java/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceTerminalSession.kt',
'''    listOf("/dev", "/proc", "/sys").forEach { path ->
        if (File(path).exists()) {
            args += "-b"
            args += path
        }
    }''',
'''    listOf("/dev", "/proc", "/sys").forEach { path ->
        if (File(path).exists()) {
            args += "-b"
            args += path
        }
    }
    // RikkaHub Mod: 手机真实存储
    if (File("/storage/emulated/0").exists()) {
        args += "-b"
        args += "/storage/emulated/0:/sdcard"
        args += "-b"
        args += "/storage"
    }''', '终端挂载')

print('=== 第 1 批改动完成 ===')
