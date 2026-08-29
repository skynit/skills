---
name: accept-code
description: 在真实 CWNAS Linux 设备上编译、部署并验收当前代码修改。根据改动范围构建 cwnas 或 cwnas 与 LanceDB helper，处理 SSH 公钥授权，安装到测试机并验证本次涉及的 API。用户提到“验收代码”“真机验收”“部署验收”“在 NAS 上跑一遍”时使用。
---

# 验收代码

先完成本地编译，再处理 SSH 连接，最后部署并验证本次修改涉及的 API。不要把普通后端修改扩展为全量 AI 验收。

## 默认参数

- SSH：`root@192.168.100.247`
- HTTPS：`9081`
- 远端目录：`/home/cwnas/9081`
- CWNAS 仓库：`D:\projects\go\GOPATH\src\cw`
- 主程序产物：`bin\cw\cwnas-linux-amd64`
- LanceDB helper 产物：`bin\cw\cwnas-lancedb-helper-linux-amd64`

用户指定其他主机、端口、目录或仓库时，以用户本次要求为准。

## 1. 先编译

检查当前分支、工作区修改、`git diff --check` 和相关改动文件；保留所有未提交修改，不回退工作区，不运行全量测试。

根据改动范围决定产物数量：

- 非 AI 修改：只构建一份 `cwnas-linux-amd64`。使用现有 Linux AMD64 Docker 构建环境，执行 `go build -buildvcs=false -trimpath -ldflags='-s -w' -o /src/bin/cw/cwnas-linux-amd64 ./cmd/server`。
- AI 修改：构建 `cwnas-linux-amd64` 和 `cwnas-lancedb-helper-linux-amd64` 两份产物。AI 修改包括 `pkg/ai`、`cmd/lancedb-helper`、LanceDB、本地模型或 AI 搜索链路相关代码；使用 `compile-code` 的固定构建脚本和 `localai` 构建配置。

不要因为 LanceDB 静态库缺失而把 AI 修改降级成非 AI 构建。AI 构建条件缺失时停止部署并明确报告。只运行与本次修改直接相关的定向测试或包编译。

记录每个产物的路径、大小和 SHA-256。只有编译和定向验证成功后才继续处理 SSH。

## 2. 检查并处理 SSH 公钥

先检查目标机是否已经授权本机密钥：

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@192.168.100.247 true
```

连接成功就直接进入部署，不重复生成或发送密钥。

连接失败时，检查 `C:\Users\MINI-PC\.ssh\id_rsa` 和 `id_rsa.pub`。在生成密钥、补建公钥文件或向目标机写入 `authorized_keys` 之前，必须向用户展示将执行的 PowerShell 7 命令并等待明确确认。

- 密钥不存在：使用 `ssh-keygen` 在默认路径生成 RSA 密钥；不得覆盖现有私钥。
- 私钥存在但 `.pub` 缺失：使用 `ssh-keygen -y` 从现有私钥恢复公钥，不重新生成私钥。
- 本地公钥存在但目标机未授权：将公钥追加到目标用户的 `~/.ssh/authorized_keys`，设置目录权限 `700`、文件权限 `600`。

发送公钥时允许 SSH 在本地终端提示用户输入目标机密码；不要要求用户在聊天中发送密码。完成后再次使用 `BatchMode=yes` 验证免密连接，仍失败则停止部署并报告。

## 3. 部署和安装

SSH 可用后，确认目标机为 Linux AMD64、远端目录解析结果正确且空间足够。上传产物前为现有文件创建带时间戳的备份。

主程序部署到 `/home/cwnas/9081/cwnas`：

1. 先上传为 `cwnas.new.<run-id>`。
2. 对比本地和远端 SHA-256，并确认是 Linux x86-64 ELF。
3. 备份现有 `cwnas`，再在同一目录内重命名替换。
4. 执行 `chmod +x /home/cwnas/9081/cwnas`。
5. 在 `/home/cwnas/9081` 执行 `./cwnas install`。

AI 修改还要上传 `cwnas-lancedb-helper-linux-amd64`。将其保存为 `cwnas-lancedb-helper`，校验并 `chmod +x`；安装主程序后，把 helper 同步到 systemd 实际执行的 cwnas 所在目录（通常为 `/opt/cwnas`），因为运行时从主程序目录查找 helper。替换已有 helper 前同样备份。

安装失败或新服务无法启动时，采集 `systemctl` 和 `journalctl` 日志；无法立即做出局部修复时恢复本轮备份，不让设备停在半部署状态。

## 4. 验证本次 API

确认正式文件校验和、`cwnas.service` 为 `active/running`、`NRestarts=0` 且 `9081` 正在监听。随后根据代码差异找到本次新增或修改的 API，验证成功路径、关键响应字段和相关日志。

- 非 AI 修改：只测试本次涉及的 CWNAS API 及直接受影响功能。
- AI 修改：额外确认 helper 可执行、相关 AI 服务健康，并测试本次修改涉及的 AI API。
- 只有用户明确要求完整 AI 验收时，才执行全部模型接口、图片入库和搜索闭环。

鉴权信息只在当前进程或浏览器会话中使用，不输出完整 Token、密码或 Cookie。HTTP 200 之外还要检查业务状态和关键字段。

失败时按“日志定位 -> 本地最小修复 -> 定向测试 -> 重新编译 -> 重新部署 -> 重放失败 API”循环处理，不顺手重构无关代码。

## 5. 报告

简要报告目标机、部署目录、分支或 commit、产物 SHA-256、备份位置、服务状态、实际测试的 API 及结果。说明未执行的验收项和仍存在的阻塞或风险。
