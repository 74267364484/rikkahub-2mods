# -*- coding: utf-8 -*-
import io, os
ROOT='/workspace/build/src/rikkahub-2.5.6'
P='app/src/main/java/me/rerere/rikkahub/ui/pages/extensions/workspace/WorkspaceDetailPage.kt'
def edit(old, new, tag, cnt=1, path=P):
    p=os.path.join(ROOT,path); s=io.open(p,encoding='utf-8').read()
    n=s.count(old); assert n==cnt, '[%s] 期望 %d, 实际 %d' % (tag,cnt,n)
    io.open(p,'w',encoding='utf-8').write(s.replace(old,new)); print('OK',tag)

# 1) 导入
edit('''import androidx.compose.material3.TextButton''',
'''import androidx.compose.material3.TextButton
import androidx.compose.runtime.DisposableEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner''', '导入')

# 2) 在页面里加状态/选择器/生命周期监听
edit('''    val directoryExportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        vm.exportFilesToDirectory(uri, context.contentResolver)
    }''',
'''    val directoryExportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        vm.exportFilesToDirectory(uri, context.contentResolver)
    }

    // ---- RikkaHub Mod: 手机存储权限 + 工作台目录选择 ----
    var storageBase by remember { mutableStateOf(vm.storageBase()) }
    var allFilesGranted by remember { mutableStateOf(isAllFilesAccessGranted()) }
    val storagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri != null) {
            val path = treeUriToStoragePath(uri)
            if (path != null) {
                vm.setStorageBase(path)
                storageBase = vm.storageBase()
            } else {
                android.widget.Toast.makeText(
                    context,
                    "这个目录映射不到本地路径, 换一个试试(比如「内部存储 / Download」)",
                    android.widget.Toast.LENGTH_LONG,
                ).show()
            }
        }
    }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                allFilesGranted = isAllFilesAccessGranted()
                storageBase = vm.storageBase()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }''', '页面状态与选择器')

# 3) 传给 WorkspaceBasicPage
edit('''                0 -> WorkspaceBasicPage(
                    workspace = state.workspace,
                    installProgress = installProgress,
                    onInstallRootfs = { showInstallDialog = true },
                    onToolApprovalChange = vm::setToolApproval,
                    onShellCompatibilityModeChange = vm::setShellCompatibilityMode,
                )''',
'''                0 -> WorkspaceBasicPage(
                    workspace = state.workspace,
                    installProgress = installProgress,
                    onInstallRootfs = { showInstallDialog = true },
                    onToolApprovalChange = vm::setToolApproval,
                    onShellCompatibilityModeChange = vm::setShellCompatibilityMode,
                    storageBase = storageBase,
                    allFilesGranted = allFilesGranted,
                    onRequestAllFilesAccess = { requestAllFilesAccess(context) },
                    onPickStorageFolder = { storagePickerLauncher.launch(null) },
                    onResetStorageFolder = {
                        vm.setStorageBase(null)
                        storageBase = vm.storageBase()
                    },
                )''', 'WorkspaceBasicPage 调用')

# 4) WorkspaceBasicPage 签名
edit('''private fun WorkspaceBasicPage(
    workspace: WorkspaceEntity?,
    installProgress: RootfsInstallProgress?,
    onInstallRootfs: () -> Unit,
    onToolApprovalChange: (String, Boolean) -> Unit,
    onShellCompatibilityModeChange: (Boolean) -> Unit,
) {''',
'''private fun WorkspaceBasicPage(
    workspace: WorkspaceEntity?,
    installProgress: RootfsInstallProgress?,
    onInstallRootfs: () -> Unit,
    onToolApprovalChange: (String, Boolean) -> Unit,
    onShellCompatibilityModeChange: (Boolean) -> Unit,
    storageBase: String,
    allFilesGranted: Boolean,
    onRequestAllFilesAccess: () -> Unit,
    onPickStorageFolder: () -> Unit,
    onResetStorageFolder: () -> Unit,
) {''', 'WorkspaceBasicPage 签名')

# 5) 卡片渲染
edit('''        item {
            WorkspaceToolApprovalCard(
                workspace = workspace,
                onToolApprovalChange = onToolApprovalChange,
            )
        }
    }
}''',
'''        item {
            WorkspaceToolApprovalCard(
                workspace = workspace,
                onToolApprovalChange = onToolApprovalChange,
            )
        }

        item {
            WorkspaceStorageCard(
                storageBase = storageBase,
                granted = allFilesGranted,
                onRequestPermission = onRequestAllFilesAccess,
                onPickFolder = onPickStorageFolder,
                onResetFolder = onResetStorageFolder,
            )
        }
    }
}

@Composable
private fun WorkspaceStorageCard(
    storageBase: String,
    granted: Boolean,
    onRequestPermission: () -> Unit,
    onPickFolder: () -> Unit,
    onResetFolder: () -> Unit,
) {
    CardGroup(
        title = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("手机存储")
                Text(
                    text = if (granted) {
                        "已授权「所有文件访问权限」, 工作台可直接读写手机文件"
                    } else {
                        "未授权: 现在只能读写 APP 私有目录, 看不到手机里的文件"
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = if (granted) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.error,
                )
            }
        },
    ) {
        item(
            headlineContent = { Text("工作台目录") },
            supportingContent = {
                Text(text = storageBase, maxLines = 2, overflow = TextOverflow.Ellipsis)
            },
            trailingContent = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onPickFolder) { Text("选择") }
                    TextButton(onClick = onResetFolder) { Text("默认") }
                }
            },
        )
        if (!granted) {
            item(
                headlineContent = { Text("授予所有文件访问权限") },
                supportingContent = { Text("用于读写相册 / 下载 / 文档等真实文件") },
                trailingContent = { TextButton(onClick = onRequestPermission) { Text("去授权") } },
            )
        }
    }
}

/** RikkaHub Mod: 是否已授予「所有文件访问权限」 */
private fun isAllFilesAccessGranted(): Boolean =
    if (android.os.Build.VERSION.SDK_INT < 30) true
    else runCatching { android.os.Environment.isExternalStorageManager() }.getOrDefault(false)

/** RikkaHub Mod: 跳系统「所有文件访问权限」页面 */
private fun requestAllFilesAccess(context: android.content.Context) {
    runCatching {
        context.startActivity(
            Intent(android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                .setData(android.net.Uri.parse("package:${context.packageName}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }
}

/** RikkaHub Mod: 把 SAF 选中的目录 URI 映射成本地绝对路径(内部存储 / SD 卡) */
private fun treeUriToStoragePath(uri: android.net.Uri): String? = runCatching {
    val docId = android.provider.DocumentsContract.getTreeDocumentId(uri)
    val volume = docId.substringBefore(':', "")
    val relative = docId.substringAfter(':', "")
    when {
        volume.equals("primary", true) ->
            if (relative.isBlank()) "/storage/emulated/0" else "/storage/emulated/0/$relative"
        volume.equals("raw", true) -> relative.ifBlank { null }
        volume.isNotBlank() ->
            if (relative.isBlank()) "/storage/$volume" else "/storage/$volume/$relative"
        else -> null
    }
}.getOrNull()''', '存储卡片 + 工具函数')
print('=== 第 3 批(UI)完成 ===')
