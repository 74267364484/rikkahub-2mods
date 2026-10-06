# RikkaHub 改版（两个）

RikkaHub **2.5.6** 的两个独立魔改版，**都跟官方原版共存**——不同包名、不同签名、各用各的数据，装完手机上是三个图标互不干扰。

> 仓库名被 GitHub 限制成了 `rikkahub-2mods`（GitHub 不接受中文仓库名），本名就是 **RikkaHub 改版（两个）**。

---

## 下载

| 改版 | 文件 | 包名 | 版本 | 它解决什么 |
|---|---|---|---|---|
| **改版一** | [`apk/RikkaHub_2.5.6-fullaccess_clone.apk`](apk/RikkaHub_2.5.6-fullaccess_clone.apk) | `me.rerere.rikkahuc` | 2.5.6 (191) | **模型调用工具时不需要用户许可**，省得反复点「允许」 |
| **改版二** | [`apk/RikkaHubMod.apk`](apk/RikkaHubMod.apk) | `me.rerere.rikkahub.mod` | 2.5.6-mod.19 (207) | **工作台和本地存储相连**（应用名显示为 `RikkaHub Mod`） |

校验值见 [`SHA256SUMS.txt`](SHA256SUMS.txt)。

---

## 改版一：模型调用工具时不需要用户许可

原版每调一次工具（跑 shell、读写文件、联网搜索……）就弹一次「允许 / 拒绝」，一次任务下来点几十下。改版一把这个判断**直接短路**：工具调用不再等待人工确认，模型自己就执行了。

**改动只有一条指令**，在 `classes3.dex` 里：

```
类:   me.rerere.rikkahub.data.ai.GenerationLoop$generateText$1
位置: 读取 Tool.needsApproval 的 lambda 结果处
改前: invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z
      move-result v1                    ← 取回 needsApproval 的真实返回值
改后: invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z
      const/4 v1, 0x0                   ← 恒为 false，返回值直接丢弃
```

因为 `v1 == false`，紧随其后的 `if-ne v1, v7, :cond_45c`（`v7 = 1`）必然跳转到 `:cond_45c`，**跳过"把该工具标记为 `ToolApprovalState$Pending`（待审批）"那一整段**，于是工具直接执行。

安全性说明：
- `move-result` 和 `const/4` 都是 2 字节指令，**dex 结构、指令地址全都没变**，只是把结果丢掉。
- `invoke` 之后不接 `move-result` 在 Dalvik/ART 里是**合法**的，返回值被丢弃而已。
- 只动了这一处，其余字节与官方包完全一致（逐类 baksmali 比对，只有这一个文件有差异）。
- 已用 smali 回汇编验证，补丁后 dex 可正常汇编、无校验错误。

> ⚠️ 装这个版本 = **你放弃了所有工具调用的最后一道人工闸门**。模型想删什么、想发什么，不会再问你。请配合「改版二」那套权限设置一起看下面的安全须知。

---

## 改版二：工作台和本地存储相连

原版的工作台是一个**沙箱**：模型被告知"你只能看到 rootfs 里的 `/workspace`"，所以它会回答"我看不到你的设备"。改版二把手机真实存储接进工作台：

- proot 里加了绑定挂载：`/storage/emulated/0` → `/sdcard`，`/storage` → `/storage`
- 提示词和 4 个工具描述都改了，明确告诉模型 **`/sdcard` 就是你手机的真实存储**（相册 / Download / Documents / Pictures / Music / Android/media…），隐藏文件也可见，不许再说"看不到设备"
- 工作台文件区默认落在 `/storage/emulated/0/RikkaHub/workspaces/<工作区ID>/`
- 长按桌面图标有两个快捷方式：**「手机存储权限」**（跳系统「所有文件访问权限」页）、**「设置工作台目录」**（系统目录选择器，选完即生效）
- 想手工换目录：写 `/storage/emulated/0/RikkaHub/workspace_base.txt`，内容是一个绝对路径，支持 `{root}` 占位符
- 写 `/sdcard`、`/storage` 不再触发审批弹窗

完整说明见 [`docs/改版二-工作台接本地存储.md`](docs/改版二-工作台接本地存储.md)。

---

## 安装

三个包互不冲突，装哪个都行，也可以都装：

| 你手机上已有的 | 装改版一 `me.rerere.rikkahuc` | 装改版二 `me.rerere.rikkahub.mod` |
|---|---|---|
| 官方原版 `me.rerere.rikkahub` | ✅ 共存 | ✅ 共存 |
| 之前那个二次打包版 `me.rerere.rikkahuc` | ⚠️ **同包名 = 覆盖**，签名不一致要先卸载 | ✅ 共存 |

**改版二装完必做**（不做的话工作台会退回 APP 私有目录，看不到手机文件）：

```
设置 → 应用 → RikkaHub Mod → 特殊权限 → 所有文件访问权限 → 允许
```

或者长按桌面图标 → 「手机存储权限」。

---

## ⚠️ 安全须知（重要，请读完）

这两个改动合起来，等于**把一个能读写你整台手机的 shell 交给了一个大模型**：

1. **改版二让模型看得见也改得动你的真实存储。** `/sdcard` 就是你的相册、下载、文档、微信文件夹……没有回收站，模型一条 `rm -rf` 下去就是没了。
2. **改版一取消了工具调用的人工确认。** 模型不会先问你"我要删这个可以吗"，它直接做。
3. **两个一起装 = 全自动 + 全权限。** 这是最危险的组合。

建议：
- 重要数据先备份（照片/文档同步到网盘或电脑）
- 别把含密钥、身份证照、银行卡截图、`.ssh`、`auths/*.json` 这类东西放在模型能扫到的目录
- 用改版二时尽量把工作台目录**限定到一个子目录**（用「设置工作台目录」快捷方式挑一个专用文件夹），而不是把整个 `/storage/emulated/0` 交给它
- 模型跑长任务时盯着点，尤其是它开始批量 `rm` / `mv` 的时候
- 本魔改版用自建签名（证书 SHA-256 见下），**升级必须用同一个 keystore**，否则要先卸载

---

## 签名与校验

```
改版二 RikkaHubMod.apk
  签名主体: CN=RikkaHub Mod, OU=Workspace, O=RikkaHubMod, L=CN, C=CN
  证书 SHA-256: FD:BF:F9:21:BE:9F:85:04:57:93:41:CB:A2:BD:A3:B1:CE:6A:08:CA:14:3B:70:F7:D8:50:D0:4B:8B:58:EE:94
  v1 + v2 + v3 签名

改版一 RikkaHub_2.5.6-fullaccess_clone.apk
  签名主体: C=US, ST=California, L=Mountain View, O=Android, OU=Android, CN=Android
  证书 SHA-256: A4:0D:A8:0A:59:D1:70:CA:A9:50:CF:15:C1:8C:45:4D:47:A3:9B:26:98:9D:8B:64:0E:CD:74:5B:A7:1B:F5:DC
  v2 签名
```

> 改版一用的是 **AOSP 公开测试密钥**（AOSP 源码里就有，人人可签）。所以**任何人都能签一个同包名 `me.rerere.rikkahuc` 的 APK 冒充它**。如果这个包对你有意义，建议自己重新签名；日常用的话，认准本仓库的 SHA256。
>
> 本仓库**不提供改版二的 keystore 文件**（那等于把覆盖安装你手机 APP 的钥匙公开挂在网上）。要长期自己维护这个改版，请自行生成 keystore 并固定使用。

---

## 开发记录

两个改版的全部实现过程都留档在 [`docs/`](docs/)：

```
docs/
├── 改版一-免工具调用审批.md          ← 改版一的技术说明（补丁定位、验证方法）
├── 改版二-工作台接本地存储.md        ← 改版二的完整说明
└── 开发记录/
    └── 改版二/
        ├── 说明-原始.txt
        ├── 改动说明与使用指南.md
        ├── 交付记录.md               ← 踩过的坑：签名冲突 / VerifyError / 寄存器覆盖 / 悬空引用
        ├── smali补丁/                ← 免源码路线：baksmali + AXML + arsc 改名 + 打包 + 签名
        └── 源码改动/                 ← 源码路线：apply_code_changes*.py（可复现的全部 diff）
```

改版二的路线说明：最初走的是**免源码**（反汇编 smali 直接改，见 `smali补丁/`），后来因为要在 Compose UI 里加权限卡片和目录选择器，改走**源码编译**（RikkaHub 2.5.6 源码 + `apply_code_changes*.py`），最终产物是 `RikkaHubMod.apk`。

---

## 已知限制

- 其他 APP 的 `Android/data`、`Android/obb` 目录读不到——Android 11+ 的系统限制，跟本次改动无关
- 改版二的 rootfs（Linux 系统本体）仍在 APP 私有目录，不能放到 `/sdcard`（`/sdcard` 是 `noexec`，放那儿跑不了程序）
- 改版一、改版二都是基于 **RikkaHub 2.5.6**，上游更新后需要重新定位补丁点
- 卸载重装会丢 APP 数据（聊天记录 / 工作区），rootfs 要重新下载
- 仅自用测试过，不保证在你机型和 ROM 上完全正常；改版二对「所有文件访问权限」有硬依赖

---

## 免责声明

本项目仅供**个人学习与自用**。RikkaHub 版权归原作者所有（[原项目](https://github.com/rikkahub/rikkahub)），本仓库只分发修改后的 APK 与改动记录，**不对任何数据丢失、设备损坏或账号风险负责**。下载即表示你已知晓上面全部安全须知并自行承担后果。
