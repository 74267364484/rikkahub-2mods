# -*- coding: utf-8 -*-
import io, os
ROOT='/workspace/build/src/rikkahub-2.5.6'
def edit(path, old, new, tag, cnt=1):
    p=os.path.join(ROOT,path); s=io.open(p,encoding='utf-8').read()
    n=s.count(old); assert n==cnt, '[%s] 期望 %d, 实际 %d' % (tag,cnt,n)
    io.open(p,'w',encoding='utf-8').write(s.replace(old,new)); print('OK',tag)

TOOLS='app/src/main/java/me/rerere/rikkahub/data/ai/tools/WorkspaceTools.kt'
edit(TOOLS, '''        append("Use cwd for a path relative to the workspace files root. ")''',
'''        append("Use cwd for a path relative to the workspace files root. ")
        append("The user's REAL phone storage is mounted read-write at /sdcard (= /storage/emulated/0) and /storage; e.g. `ls -a /sdcard/DCIM`. ")''', 'shell 描述')

edit(TOOLS, '''                "Absolute path inside Rootfs. Use /workspace for the workspace files area."''',
'''                "Absolute path inside Rootfs. Use /workspace for the workspace files area, or /sdcard (= /storage/emulated/0) / /storage for the user's real phone storage (hidden files included)."''', 'path 描述(必填)')
edit(TOOLS, '''                "Optional absolute path inside Rootfs. Use /workspace for the workspace files area."''',
'''                "Optional absolute path inside Rootfs. Use /workspace for the workspace files area, or /sdcard (= /storage/emulated/0) / /storage for the user's real phone storage (hidden files included)."''', 'path 描述(可选)')

# RouteActivity
RA='app/src/main/java/me/rerere/rikkahub/RouteActivity.kt'
edit(RA, '''        enableEdgeToEdge()
        disableNavigationBarContrast()
        super.onCreate(savedInstanceState)''',
'''        enableEdgeToEdge()
        disableNavigationBarContrast()
        super.onCreate(savedInstanceState)
        ensureAllFilesAccess()''', 'RouteActivity 调用点')

edit(RA, '''    override fun onCreate(savedInstanceState: Bundle?) {''',
'''    /** RikkaHub Mod: 检查「所有文件访问权限」, 未授权则提示并跳转系统授权页 */
    private fun ensureAllFilesAccess() {
        if (android.os.Build.VERSION.SDK_INT < 30) return
        if (rikkaAllFilesAsked) return
        rikkaAllFilesAsked = true
        if (runCatching { android.os.Environment.isExternalStorageManager() }.getOrDefault(false)) return
        runCatching {
            android.widget.Toast.makeText(
                this,
                "RikkaHub Mod 需要「所有文件访问权限」才能读写手机存储, 正在打开设置…",
                android.widget.Toast.LENGTH_LONG,
            ).show()
            startActivity(
                Intent(android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    .setData(android.net.Uri.parse("package:$packageName"))
            )
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {''', 'RouteActivity 权限方法')

p=os.path.join(ROOT,RA); s=io.open(p,encoding='utf-8').read()
if 'private var rikkaAllFilesAsked' not in s:
    i=s.index('\nclass RouteActivity')
    s=s[:i]+'\n\n/** RikkaHub Mod: 同一次进程内只提示一次权限 */\nprivate var rikkaAllFilesAsked = false\n'+s[i:]
    io.open(p,'w',encoding='utf-8').write(s); print('OK RouteActivity 标志位')

# WorkspaceRepository
edit('app/src/main/java/me/rerere/rikkahub/data/repository/WorkspaceRepository.kt',
'''    fun listFlow(): Flow<List<WorkspaceEntity>> = dao.listFlow()''',
'''    fun listFlow(): Flow<List<WorkspaceEntity>> = dao.listFlow()

    /** RikkaHub Mod: 工作区文件区根目录(手机存储) */
    fun storageBase(): String = me.rerere.workspace.WorkspaceManager.storageBase()

    /** RikkaHub Mod: 设置/恢复工作区文件区根目录 */
    fun setStorageBase(path: String?): Boolean = me.rerere.workspace.WorkspaceManager.setStorageBase(path)''',
'WorkspaceRepository 目录接口')

# WorkspaceDetailVM
edit('app/src/main/java/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceDetailVM.kt',
'''    private fun loadWorkspace() {''',
'''    /** RikkaHub Mod: 当前工作台目录(手机存储) */
    fun storageBase(): String = repository.storageBase()

    /** RikkaHub Mod: 切换工作台目录(null=恢复默认), 并刷新文件列表 */
    fun setStorageBase(path: String?) {
        viewModelScope.launch {
            repository.setStorageBase(path)
            refresh()
        }
    }

    private fun loadWorkspace() {''', 'WorkspaceDetailVM 方法')
print('=== 第 2b 批完成 ===')
