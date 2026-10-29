---
name: deploy-be213-driver
description: 将 driver 仓库中的 Intel BE213 离线驱动工具包上传到目标 Ubuntu 机器，执行源码 backport 或 DKMS 安装，并在重启后验收驱动、固件和无线接口。用户要求“部署 BE213 驱动”“把离线脚本传到机器安装”“远程安装无线驱动”或“重启后验收 BE213”时使用；不用于其他 Wi-Fi 芯片、蓝牙、ISO 构建或修改驱动源码。
---

# 部署 BE213 离线驱动

将完整的 `be213-offline-installer` 上传到目标机，使用包内入口脚本安装和验收。不改动工具包内容，不使用仓库中的旧 `wifi/wifi-install.sh`。

## 确定本次范围

从当前对话获取目标 SSH 主机、用户、端口和安装路径。未指定时：

- 本地工具包：`/home/skynit/workspace/driver/be213-offline-installer`。
- 驱动路径：默认使用 `01-backport-driver-install.sh` 源码 backport 路径。
- 远程位置：`/opt/be213-offline-installer-<MANIFEST_HASH_12>`，其中后缀是本地 `MANIFEST.sha256` 文件的 SHA-256 前 12 位。
- 只安装驱动和固件；不自动重启，不自动启动 AP。

目标主机缺失时，先请用户提供 `<USER>@<HOST>`。路径 03 仅在用户明确选择 DKMS 时使用。用户明确要求重启后验收时，才执行重启和重连。用户明确要求开启 AP 时，才运行脚本 02。

## SSH 连接

1. 先使用 `BatchMode=yes`、有限的连接超时和一次尝试检查已有密钥或 SSH 控制连接。
2. 已知有效的私钥或端口时直接使用，不遍历用户目录、历史日志或无关密钥。
3. 需要密码时，让 SSH 在用户可见终端中提示，或请用户安装本机公钥。不在聊天、命令行、环境变量、临时脚本或报告中保存密码。
4. 连接失败时区分认证被拒绝、主机不可达和主机密钥变化，不对同一凭据反复尝试。

目标用户不是 `root` 时，先确认其可以运行 `sudo -n true`。如果 sudo 需要交互密码，使用用户可见终端完成；不把 sudo 密码通过命令参数或标准输入自动注入。

## 本地包检查

上传前：

1. 确认源目录、`MANIFEST.sha256`、三个入口脚本、`lib/common.sh` 和 `resources/` 存在。
2. 在工具包根目录运行 `sha256sum --check --strict MANIFEST.sha256`。任一文件校验失败就停止，不重新生成清单来掩盖差异。
3. 记录 `MANIFEST.sha256` 文件的完整 SHA-256，它是本次包标识。
4. 不修改包内 hostapd 配置、不另行替换固件、不更新固定源码或 DEB。这些更改会破坏清单校验与已定义的验收基线。

这是部署任务，不运行全仓测试。仅在工具包自身发生改动或用户要求时，运行该包现有的定向测试。

## 目标机预检

在一次远程调用中收集并核对：

- `/etc/os-release` 显示 Ubuntu 26.04。
- `uname -r` 和 `uname -m`；当前内核存在 `/lib/modules/$(uname -r)/build/Makefile`。
- `lspci -Dn` 能看到 PCI ID `8086:4d40`。
- `mokutil --sb-state` 的 Secure Boot 状态；`mokutil` 不存在或结果不明时视为未知，不默认放行。
- `modinfo -F filename iwlwifi`、`dkms status`、`df -Pk /opt /tmp`、`df -Pi /opt /tmp`，以及 `/var/lib/be213-offline-installer` 是否已有安装状态。
- 所选路径的依赖命令和当前内核头文件是否齐全。

源码路径需要 `gcc make bc bison flex pkg-config perl tar xz sha256sum`。DKMS 路径需要 `dkms dpkg dpkg-query gcc make sha256sum`、`dkms >= 3.0.11`、`libc6-dev` 或 `libc-dev`。验收需要 `pciutils iw rfkill`。

任一下列情况都应停止而不自动修复：

- 系统或硬件不匹配。
- 缺失依赖、内核头文件或磁盘空间；离线工具包不负责联网补包。源码路径保守要求 `/tmp` 至少 2 GiB 可用，`/opt` 可用空间至少是完整本地包大小的 3 倍，两处可用 inode 均至少 10%；DKMS 路径不需要源码编译的 `/tmp` 2 GiB 余量，但仍需满足 `/opt` 和 inode 要求。
- 已有另一条 backport 路径、不明的 `updates/` 模块、不一致的状态或未完成的回滚。
- Secure Boot 状态未知，或已启用但没有可执行的模块签名方案。单独注册 MOK 不会让未签名模块受信任；模块必须由已注册的受信任密钥签名。`--allow-unsigned` 只绕过安装脚本门禁，不绕过内核验签。

不自动运行 `apt`、不关闭 Secure Boot、不删除未知模块或安装记录。

## 上传完整工具包

1. 用唯一的 run ID 创建远程 `/tmp` 暂存目录。
2. 通过 `tar` 管道、`scp` 或 `rsync` 上传完整 `be213-offline-installer` 目录，包括 `resources/`、`lib/`、`tests/` 和 `MANIFEST.sha256`。不能只上传三个脚本。
3. 在远程暂存目录运行 `sha256sum --check --strict MANIFEST.sha256`，并确认它与本地的包标识一致。
4. 使用 root 权限将校验通过的目录移到版本化的 `/opt/be213-offline-installer-<MANIFEST_HASH_12>`。同名目录已存在时，只有在其清单与内容再次校验通过后才复用；否则停止，不覆盖、合并或删除。
5. 设置目录为 root 所有，只为三个入口脚本补充必要的可执行权限。保留该版本目录，以便重启后 `verify` 和日后 `uninstall`。

远程最终目录安装成功后，可删除本轮 `/tmp` 上传物；不清理版本化目录、安装状态、固件备份或模块。

## 执行安装

始终在远程版本化目录中执行包内脚本。先运行所选路径的 `check`，再运行同一路径的 `install --dry-run --yes`。预检失败就停止，不绕过脚本的冲突、硬件、签名或依赖检查。

包内状态文件在安装真正完成前就可能被写入，且不记录原安装目录或 manifest 哈希。因此：

- 只有本技能在当前任务中亲自观测到远程清单校验通过、正式 `install` 返回 0，并记录了包标识和远程目录时，才能把该状态当作本轮完成的安装，随后进入重启验收。
- 任务开始前已存在的状态一律视为历史状态：只读收集状态文件、模块路径、boot ID 和日志后停止，不根据文件存在就重装、卸载或宣称安装完整。只有用户确认原安装路径和下一步操作后才继续。

预检通过后执行：

- 默认源码路径：`sudo ./01-backport-driver-install.sh install --yes`。用户指定并行数时追加 `--jobs N`。
- DKMS 备选路径：`sudo ./03-dkms-kernel-patch.sh install --yes`。
- Secure Boot 已启用时，只有用户已指定受信任签名密钥与对应的已注册证书，并授权在安装后、重启前签名本轮安装的所有无线模块时，才在 dry-run 和正式安装中同时追加 `--allow-unsigned`。后续必须通过下方重启前门禁。

源码路径可能需要较长时间编译。保留完整命令退出状态，定期告知用户当前阶段，不因 SSH 客户端的短时输出空白重复发起安装。

安装脚本返回非零时，保留现场并报告首个明确错误。不手工删除 `/var/lib/be213-offline-installer`、`/lib/modules/.../updates`、固件或备份目录，也不自行改用另一条安装路径。

### 重启前门禁

正式 `install` 返回 0 后仍不立即重启。先完成：

1. 源码路径要求安装模块清单存在且非空，`modinfo -F filename iwlwifi` 指向当前内核的 `updates/` 路径，目标模块文件存在。
2. DKMS 路径要求 `dkms status -m backport-iwlwifi` 中当前内核和架构的精确状态为 `installed`，而不是 `added`、`built` 或 `broken`；`modinfo -F filename iwlwifi` 指向当前内核中存在的 `updates/dkms/` 模块。
3. Secure Boot 已启用时，按用户已指定的受信任签名方案对本轮安装的全部无线模块签名。模块已压缩时，必须使用该发行版支持的解压、签名、重压流程，不能对压缩文件字节直接运行模块签名工具。逐个确认 `modinfo -F signer` 非空且对应证书已 enrolled。
4. 如果执行过模块签名，必须在签名后再执行 `depmod -a "$(uname -r)"`，然后使用 `update-initramfs -u -k "$(uname -r)"` 刷新 initramfs；目标系统没有 `update-initramfs` 时使用 `dracut --force --kver "$(uname -r)"`。两者都不存在或任一刷新命令失败时，禁止重启。

任一门禁失败时，将状态报告为“已执行安装、但未达到可重启条件”，保留现场并停止。

## 重启和验收

如果用户未授权重启，安装成功后停在“等待重启”状态，报告精确的远程目录和验收命令。不在未重启时声称驱动已验收通过。

用户已授权重启和验收时：

1. 记录重启前的 boot ID，执行 `sudo systemctl reboot`；SSH 断开是预期现象。
2. 在有界等待窗口内重连，每次连接都设置短超时。不使用单次超过 60 秒的阻塞等待；向用户报告正在等待机器恢复。
3. 确认 boot ID 已变更，然后在原远程版本化目录运行同一路径的 `verify`。
4. 不仅依赖包内 `verify`。要求 `/sys/module/iwlwifi/srcversion` 存在，运行中 `srcversion` 和 `modinfo -F srcversion iwlwifi` 都非空且严格相等；任一值缺失都是验收失败。
5. 从 `lspci -Dnnd 8086:4d40` 获取唯一 BE213 PCI BDF，通过 `/sys/bus/pci/devices/<BDF>/driver` 确认绑定 `iwlwifi`，并通过该设备的 `net/` 目录确认其无线接口。日志中必须有绑定该 BDF 的 `loaded firmware version ... bz-b0-wh-b0-cNNN.ucode` 和 `base HW address`，且 `NNN >= 102`；同一 BDF 不能有新的 Fatal、SYSASSERT、固件重启或初始化失败。多块 Intel 无线设备或日志格式无法关联 BDF 时，结果是无法确认，不合并不同设备的证据。
6. DKMS 路径还必须确认 `dkms status -m backport-iwlwifi` 中当前内核和架构的精确状态为 `installed`，而不是 `added`、`built` 或 `broken`；`modinfo -F filename iwlwifi` 必须指向存在的 `updates/dkms/` 模块。
7. 另外记录 `uname -r`、`modinfo -F filename iwlwifi`、`iw dev` 和本次启动中的 `iwlwifi|iwlmld|firmware|fatal|assert|restart|timeout` 关键日志。

只有包内 `verify` 与上述额外检查全部成功时，才声称安装已验收通过。连接超时、机器未恢复或任一验收项失败时，报告实际状态和最后可用证据。

## AP 与卸载

只在用户明确要求时从原远程版本目录执行：

- 开启 AP：`sudo ./02-enable-ap.sh start`。操作前确认 SSH 依赖有线连接或本地控制台，因为无线状态变更可能中断远程会话。不修改包内固定 hostapd 配置，不在报告中回显其 Wi-Fi 密码。
- 停止 AP：`sudo ./02-enable-ap.sh stop`。
- 卸载驱动：先停止 AP，再对原安装路径执行 `uninstall --yes`，最后在用户授权后重启。不用另一路径的脚本卸载。

## 交付报告

简要报告：

- 目标主机和远程版本化目录。
- 包标识、远程清单校验结果和所选 01/03 路径。
- 预检、安装、重启和 `verify` 各自的实际状态。
- 当前内核、`iwlwifi` 模块路径、已加载固件和无线接口。
- 是否启动 AP，以及仍需用户完成的重启、Secure Boot/MOK 或依赖准备。

不报告 SSH、sudo 或 Wi-Fi 明文密码。不把“文件已上传”、“安装命令退出 0”或“日志出现 loaded firmware”单独写成“验收通过”。
