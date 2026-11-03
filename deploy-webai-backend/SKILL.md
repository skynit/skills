---
name: deploy-webai-backend
description: "构建并部署官网模型 NAS 上的 CWNAS 后端，配置云端 API 或本地模型，验证相关知识库导入、检索和流式对话。用于更新 webai-kb.cwnas.net 对应模型服务时；知识库网关与 Vue 前端另行处理。"
---

# 部署官网 CWNAS 模型后端

## 目标与边界

- 源码：`/home/skynit/workspace/cw`，使用当前工作区最新源码，保留未提交改动。
- 模型 NAS：`cwnas-ip166` / `192.168.9.166`，设备 ID `f42f3dbe-d6c7-4e16-b8fa-9a221fee4365`。
- 公网 HTTPS：`https://webai-kb.cwnas.net:9081`，公网 IP `113.98.201.233`。
- 公网 SSH `cwnas@113.98.201.233:22` 进入 `.100` 跳板机；再连接 `cwnas@192.168.9.166`。修改前必须核对最终 hostname、IP 和 systemd 路径。
- 若开发机来源被公网入口拒绝，使用 `root@139.196.42.76` 作为前置跳板；核对各层已知主机密钥，连接结束后关闭本轮临时端口转发和控制连接。
- 正式程序 `/opt/cwnas/cwnas`；`cwnas.service` 执行 `/opt/cwnas/cwnas serve`，工作目录 `/var/lib/cwnas`。
- 配置 `/var/lib/cwnas/config/config.json`；官网环境 `/etc/cwnas/webai.env`，由 `/etc/systemd/system/cwnas.service.d/webai.conf` 的 `EnvironmentFile` 注入。
- LanceDB helper `/opt/cwnas/cwnas-lancedb-helper`，监听 `127.0.0.1:9087`，数据目录 `/var/lib/cwnas/data/ai/lancedb`。
- 官网网关位于 `139.196.42.76:/var/local/cw_kb_8000`，健康检查 `http://127.0.0.1:8000/health`。只在连接或端到端验收需要时访问，不顺带发布网关或前端。

部署请求已授权时直接实施。优先使用现有 SSH 密钥或连接；凭据只在运行进程中使用，不输出、不写入本 skill。避免重复尝试错误密码。

## 构建

先阅读仓库规则，检查差异和涉及的包。官网即使使用云端 API，也要保留 NAS 的 `localai` 构建能力。

```sh
go test -tags 'webai localai' ./pkg/webai ./pkg/webai/routes ./pkg/ai/agent/service ./pkg/ai/agent/routes
CGO_ENABLED=1 go build -tags 'webai localai' -buildvcs=false -trimpath -ldflags='-s -w' -o /tmp/cwnas-webai-candidate ./cmd/server
git diff --check
sha256sum /tmp/cwnas-webai-candidate
file /tmp/cwnas-webai-candidate
```

测试包按实际改动调整，禁止全量测试。核对 Linux AMD64、CGO 动态依赖与目标 glibc；构建宿主比目标新时，使用项目现有兼容 Linux 构建环境。仅后端修改且 helper 协议不变时保留目标现有 helper；修改 helper 或协议时按仓库构建流程一并发布并备份。

## 模型配置

- 主入口默认采用 Agent provider/model；`cloud_api_config.enabled=true` 时采用 DeepSeek 和云配置的默认模型。
- `WEBAI_PROVIDER`、`WEBAI_MODEL` 是官网专用的最终覆盖值。云端部署核对其未残留 Ollama 覆盖，或明确设置 `WEBAI_PROVIDER=deepseek` 和当前有效云模型。
- `DEEPSEEK_API_KEY` 环境变量优先于加密配置中的 API Key。保留现有有效凭据，不把明文写入 `encrypted_api_key`。
- `WEBAI_API_KEY` 用于 `X-Webai-Key` 鉴权，`WEBAI_STATIC_SECRET` 用于文件签名，`WEBAI_UPLOAD_DIR` 指定文件落地目录。
- 环境文件权限保持 `0600 root`。改环境后重启服务；改 systemd drop-in 后先 `daemon-reload`。只报告变量是否存在及非秘密的 provider/model。

## 发布与回滚

1. 确认目标身份、磁盘空间、现有服务与 helper 健康；记录旧程序 SHA-256。
2. 在 `/opt/cwnas/backups/webai-<UTC时间>/` 备份程序及本轮要改的环境文件；数据目录保持原位。
3. 上传到 `/opt/cwnas/cwnas.new.<run-id>`，每层跳板传输后核对 SHA-256、ELF 和动态依赖。
4. 在正式程序同一目录内 `mv` 原子替换，设置可执行权限；配置云端或本地模型后重启 `cwnas.service`。无需重新执行安装器。
5. 用有限重试等待 HTTPS 和 helper 就绪；检查 `active/running`、`ExecMainStatus=0`、重启次数和实际进程环境。
6. 若无法及时解决启动或核心接口回归，恢复本轮程序和环境备份并重启；验证恢复状态，报告失败原因。不要让服务停在半发布状态。

丢包链路可用 `rsync --append-verify --compress` 续传候选文件，完成后仍核对完整 SHA-256。大文件上传与管理命令共用多层 SSH 转发时可能阻塞管理请求，避免在未完成身份核对时启动传输。

## 验收

从当前 `pkg/webai` 实现获取入参及响应格式，不能只检查 HTTP 200。

- 公网与 NAS 回环 `GET /api/v1/web-ai` 就绪；无密钥和错误 `X-Webai-Key` 返回 401，正确密钥可访问 `/api/v1/queue/status`。
- 在独立测试 `kb_id` 和唯一 `source_id` 中导入临时 Markdown：`POST /api/v1/process/cw-file` 返回完成和 indexed；`search/retrieve`、`full`、`enhanced` 都命中唯一标记。
- 同 source 更新，新标记命中而旧标记消失；删除后无命中。在 finally 中清理测试文档和本轮上传文件，不删除真实数据。
- 查询 `kb_id=docs_official`、`iSCSI是什么`，确认现有官网文档可检索。已有数据可用时不触发全量同步。
- `POST /api/v1/chat/completions` 和 `POST /agent-rag` 返回 SSE、来源、真实答案、完成信号，无错误事件；域名入口再验收一次。
- 涉及多模态时发送真实图片消息；区分接口透传与云模型是否具备视觉能力，失败应说明具体上游限制。
- 记录正式 SHA-256、实际云 provider/model、服务/helper 状态、备份路径、每项结果及未验证项。报告中不得出现密钥、密码或完整 token。

NAS 或开发机自身可能无法访问该公网地址；公网验收从官网网关所在的 `139.196.42.76` 执行，使用网关现有服务端密钥，不能把内网回环公网失败直接判断为生产服务异常。公网 TLS 证书应验证信任链；自签名验收先核对公网证书与已确认 NAS 的证书指纹一致，不修改官网网关的 TLS 验证策略。

## 来源

历史会话 `codex://threads/01a0a2b2-4fd2-72a2-8897-8549aa1d1233`；详细背景可读 `/home/skynit/workspace/cwnas_kb/backend/docs/webai-deployment-2026-09-22.md`。以本次现场身份、配置和验收为准，历史哈希和模型列表不作为当前事实。
