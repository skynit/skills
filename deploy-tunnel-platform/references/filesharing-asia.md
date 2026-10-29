# filesharing.asia 已有平台

以下服务器连接与部署布局于 2026-10-28 核对，用于快速定位，后续发布需再次确认；本地源码路径以当前会话工作区为准。

| 项目 | 已核对值 |
| --- | --- |
| SSH | `root@47.119.120.17`，22 端口；已验证可使用现有 SSH 密钥登录 |
| 平台入口 | `https://filesharing.asia/web/` |
| 后端仓库 | `/home/skynit/workspace/cw` |
| 前端仓库 | `/home/skynit/workspace/cwnas_client` |
| 目标架构 | Linux amd64 / x86_64 |
| systemd | `cwnas.service` |
| ExecStart | `/opt/cwnas/cwnas serve` |
| WorkingDirectory | `/var/lib/cwnas` |
| Web 目录 | `/opt/cwnas/root/web` |
| 配置、身份和数据库目录 | `/var/lib/cwnas/config` |
| 平台用量数据库 | `/var/lib/cwnas/config/cw.db` |
| HTTPS | 443 |
| TURN 控制监听 | TCP/UDP 9087 |
| TURN 中继 UDP 范围 | 50000–60000；每次核对配置及云安全组实际状态 |
| 发布与备份目录 | `/opt/cwnas-deployments/<本次唯一标识>/`，权限 0700 |

目标地址由用户于 2026-10-28 确认，且当日 `filesharing.asia` 解析为 `47.119.120.17`。直接使用该 IP 探测 SSH；后续域名解析与记录不一致时先核实目标，不回退到历史 IP，也不跳过主机密钥校验。

不在这里保存 SSH 密码、登录密码、Token 或 TURN 签名密钥。在当前会话已有授权和凭据时直接使用；没有可用方式时，第一轮限时 SSH 探测后立即用异步问答弹窗收集密码，同时构建。不要等构建完成才报告认证失败。

## 构建依据

后端 `.goreleaser.yaml` 的 Linux amd64 配置使用 `CGO_ENABLED=0`。在后端仓库执行，产物路径由本次发布目录指定：

```sh
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o "$release_dir/cwnas" ./cmd/server
```

需要项目正式 ZIP 时使用前端项目构建入口：

```sh
dart run build.dart web
```

脚本使用 `lib/web_main.dart`，关闭 Web 资源 CDN 和 WASM 预检查，设置 Skia 渲染相关编译参数，复制 `assets/fonts/ffb` 后生成压缩包。上传完整 `build/web`，不只上传 `main.dart.js`。`web/index.html` 的基路径为 `/web/`。该脚本会清理旧 Web 构建和对应旧发布 ZIP；执行前核对本次工作区脚本，必要时先保存需要保留的产物。

快速部署只需要 Web 目录，可直接执行脚本中已确认的构建步骤，跳过 ZIP 包装和旧发布 ZIP 清理：

```sh
flutter build web --target=lib/web_main.dart --no-web-resources-cdn --no-wasm-dry-run --dart-define=FLUTTER_WEB_USE_SKIA=true --dart-define=FLUTTER_WEB_USE_SKWASM=false
mkdir -p build/web/assets/fonts/ffb
cp -a assets/fonts/ffb/. build/web/assets/fonts/ffb/
```

后端与前端并行构建，前端构建成功后才复制字体。仅在两侧产物准备好后打包一次；已有有效 `payload.tar.gz` 时直接复用，不重打包。

## 可选验收命令

仅在用户要求测试/验收或本次修改源码时按实际范围选择；不是每次部署的必经步骤：

```sh
go test ./pkg/net/http/tunnel ./pkg/net/http/tunnel/platform ./pkg/net/http/tunnel/routes ./pkg/net/webrtc ./pkg/net/webrtc/signaling ./pkg/net/webrtc/turn ./pkg/auth/rbac/permission ./cmd/server/appconfig ./cmd/server/internal/networkruntime
```

在前端仓库：

```sh
flutter test test/base/api/tunnel_platform_api_test.dart test/net/webrtc/web_rtc_session_manager_test.dart test/net/webrtc_signaling_protocol_spec_test.dart test/pages/remote_access_panel_test.dart
```

## 服务和接口定位

- `GET /.well-known/cwnas-tunnel-platform`：公开平台发现，响应 `protocol=cwnas-tunnel-platform`，信令入口为 `wss://filesharing.asia/api/v1/signaling`。
- `GET /api/v1/tunnel/stats`、`/api/v1/tunnel/stats/history`、`/api/v1/tunnel/stats/usage`：受保护统计 API。没有应用登录态时只能验证访问控制响应，不能声称已验证统计页面数据。
- 源码 `pkg/net/http/tunnel/routes/status.go` 定义查询和权限；不要根据旧文档猜测参数。
- 用量表 `tunnel_traffic`：`bucket=0` 为累计，其他 bucket 为 UTC 小时，`receive`/`send` 是十进制 TEXT，使用 Python `int` 或等价无符号解析比较，避免 SQL 浮点汇总误差。
- 相关状态表有 `tunnel_stats_state`、`tunnel_sample_hours`，字段以后端当前实现与远程 schema 为准。
- 程序直接提供 HTTPS；核对实际监听前不要假设一定存在 Nginx。服务器不必安装 Go 编译器，默认核对新进程的启动时间和 `/proc/<pid>/exe` 路径即可。

## 启动等待与端口重合

2026-09-14 发布时，启动流程先初始化 AI 索引再开始 HTTPS 监听。服务器缺少 LanceDB helper，且默认 helper 地址 `http://127.0.0.1:9087` 与 TURN TCP 监听重合，HTTP 请求会等待配置中的 120 秒超时。旧版本重启也出现此行为。

遇到 systemd active 但 443 尚未监听时，结合日志和实际进程连接判断是否仍在初始化。对此已确认的布局使用至少覆盖 120 秒超时的有限检查窗口，例如 180 秒，不要每 30 秒重启一次使其始终无法完成启动。确认超时原因前不要盲目延长。每次工具等待不超过 60 秒，期间继续报告进展。不要为了部署自动修改 AI、TURN 端口或安装额外 helper；如用户另行要求解决冲突，再单独实施。

## 既有探测工具

以下仅供用户要求深入验收时使用；普通快速部署跳过。

`/home/skynit/workspace/build/turn-vm-20260911/server-control.go` 曾验证注册、目标凭据签发、UDP/TCP TURN 分配和无效凭据拒绝；它的目标与 ID 是固定值，复用前阅读并为新测试使用唯一 ID。公网模式仅证明分配及拒绝，本地模式另有少量双向数据校验，不能据此宣称完成 NAS WebRTC HTTP 验收。

不要直接执行旧 VM `start.sh` 或 `deploy.py`：它们可能重建覆盖盘或修改测试机。普通平台发布不需要启动虚拟机。
