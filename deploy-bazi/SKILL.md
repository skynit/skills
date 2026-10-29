---
name: deploy-bazi
description: 本地构建 bazi 的 Go 后端和 Vue 前端，通过 SSH 上传产物，在服务器用 Docker Compose 装配并部署 MySQL、后端和 Nginx，保留数据库并验证服务。用于“部署 bazi”“更新八字网站”“把 bazi 前后端和数据库部署到服务器”；不用于其他项目部署或默认迁移本地数据库。
---

# 部署 bazi

## 默认环境

以下是 2026-10-09 的部署记录，执行前复核；本次用户指定的目标优先。

| 项目 | 默认值 |
| --- | --- |
| 本地仓库 | `/home/skynit/workspace/bazi` |
| SSH 目标 | `root@47.119.120.17` |
| 部署目录 | `/opt/bazi` |
| Compose 项目名 | `bazi`，更新时保持不变 |
| 服务 | `db`（MySQL）、`backend`（Go）、`frontend`（Nginx + Vue） |
| 发布文件 | `backend/server`、`frontend/dist/`、各自的 Dockerfile、`docker-compose.yml` |
| 数据卷 | `bazi_mysql_data`、`bazi_element_assets`，必须先核实实际挂载 |
| 外部端口 | 前端 80；数据库 3306、后端 8080 仅绑定 `127.0.0.1` |
| 容器内部后端端口 | 8088，必须与 Nginx upstream、健康检查一致 |

目标曾只有约 1.7GB 内存且无 swap，远端源码编译期间 SSH 失去响应。**默认始终本地构建，服务器只 COPY 产物装配镜像**；不要重放仓库中的多阶段源码构建 Dockerfile。不能确认内存抖动是唯一根因，也不能依赖重启作为恢复策略。

## 授权与边界

- 用户要求部署到明确目标，授权本次上传、应用容器切换及正常启动迁移；仅要求创建/修改 skill 时，不连接、不重新部署服务器。
- 读取适用 `AGENTS.md`、`docs/testing.md` 和当前 Git 状态，保留未提交改动，明确产物是否包含它们。不要自行提交、回退或修改源码；部署发现源码缺陷时报告，未获修复授权不得悄悄改动。
- 使用 SSH 密钥或当前任务提供的凭据。**不把密码存入 skill、脚本、命令参数或日志**；优先交互式不回显密码提示。可用受限临时 ControlMaster socket 复用认证；结束时关闭。缺凭据时先询问并继续本地准备，认证失败不循环猜测。
- 不打印 `.env`、认证响应、token、Cookie、数据库密码或 `docker compose config` 展开的环境值；配置校验用 `config --quiet`。
- 既有 `.env` 与密钥保持不变，不因为发版重生成 `JWT_SECRET` 或数据库密码。不得执行 `down -v`、删卷、全局 prune、对部署根目录使用 `rsync --delete`，也不修改安全组、重启主机或更改无关服务。
- 本地 SQLite 不是生产数据来源。默认首次部署使用新 MySQL 库；迁移本地用户/命盘、覆盖远端数据、注册验收用户、创建业务数据或开启外部 RAG API，需要明确的对应授权。

## 1. 预检

本地确认 `src/go.mod`、`vue/package.json`、配置加载器、数据库迁移及 Nginx 配置；只执行当前改动的聚焦测试，不执行全量测试。

远端只读检查：CPU 架构（`x86_64` 对应 `amd64`）、内存、swap、磁盘、Docker/Compose、监听端口、现有 `bazi` 容器和实际数据卷。检查 `/opt/bazi` 是否有未知目录、符号链接或其他应用，存在冲突时先厘清。

读取配置时只输出必要的非敏感值（端口、数据库用户/库名、服务名），不要输出文件全文。对现有容器仅查询状态、镜像、挂载和端口，不完整打印容器环境。

## 2. 本地构建

用 [scripts/build.sh](scripts/build.sh) 创建独立发布目录；脚本只打包，不 SSH、不改业务源码、不跑测试。输出目录必须不存在，架构必须匹配目标。

```bash
bash /home/skynit/.codex/skills/deploy-bazi/scripts/build.sh \
  /home/skynit/workspace/bazi /tmp/bazi-release-UNIQUE amd64
```

脚本执行 MySQL 模式用的 `CGO_ENABLED=0` Go 构建与完整 `npm run build`（包括 vue-tsc），打包 Go 自带的 `zoneinfo.zip`、CA 根证书、Nginx 配置，并生成 SHA-256 清单和非敏感构建记录。产物没有源码、`.env`、本地数据库、浏览器缓存或研究资料。

静态 Go 二进制不能启动 SQLite，也不能直接支持依赖 SQLite CGO 的本地 RAG。不要用空 `DB_HOST` 做这个产物的 smoke；目标默认 `DB_HOST=db`、`RAG_ENABLED=false`。用户要求 SQLite/RAG 时需另行设计 CGO 与镜像依赖并验证。

构建、类型检查或 checksum 失败则停止发布；不拿旧产物顶替，也不安装/更新依赖绕过失败。`node_modules` 缺失时先按 lockfile 安装，必要的网络授权按项目规则处理。

## 3. 暂存与备份

- 新产物传到 `/opt/bazi/releases/唯一发布号/`，只上传生成的发布目录。远端 `sha256sum -c SHA256SUMS` 全部成功后才切换。
- 不能直接把模板覆盖到现有站点。先比较正在使用的 compose、镜像、挂载、端口、`.env` 字段；本次模板仅供首次部署或已确认的布局变更使用。
- 更新前保留当前 `backend/`、`frontend/` 和 compose 为唯一备份，并记录旧镜像 ID。私密 `.env` 如需备份，文件/目录权限必须限制为 root。
- 后端启动会自动执行迁移。更新前对现有 MySQL 做一致性逻辑备份（事务模式，检查退出码并保存受限权限文件），确认素材卷恢复点；只改前端则不用迁移数据库。数据库备份读取容器内凭据，不传密码命令参数，不把 dump 打到工具输出。
- 检查当前状态没有被其他发布改变后，切换应用目录；不要覆盖、删除未知路径。项目目录根文件与历史发布保留，不能用整树同步删除。

## 4. 装配与启动

首次部署参考 [assets/compose.yaml](assets/compose.yaml)。生成 `/opt/bazi/.env` 时设置 `umask 077`，在服务器本地生成强随机 `DB_ROOT_PASS`、`DB_PASS`、`JWT_SECRET`；应用账号默认 `bazi`，不得使用示例密码。首次不擅自创建管理员，需要用户名、邮箱和 12+ 字符密码的完整授权。旧部署使用 root 账号时保留现状，账号收权另作独立变更。

模板使用 MySQL 8.0 系列，基础镜像标签只是本次部署基线，不是“最新/安全版本”的声明。预检核实镜像可拉取及实际版本，记录 digest；应用更新不顺带升级数据库镜像。

```bash
cd /opt/bazi
docker compose -p bazi config --quiet
# 首次部署：
docker compose -p bazi up -d --build
# 已有数据库的应用更新：
docker compose -p bazi up -d --build --no-deps backend frontend
```

只改某个服务时只重建该服务。镜像装配 Dockerfile 来自 skill 产物模板，只有 COPY，不执行 Go/npm 编译。现有数据库必须已健康；数据库与素材卷的 identity 不随发布改变。

设置 SSH 连接/命令超时与 keepalive，读取真实退出码；若用 `tee` 或管道必须 `pipefail`，不以末尾 `tail` 的 0 当部署成功。低内存下 MySQL 可另行按负载调优，不能为本次发布擅自创建 swap 或更改系统配置。

若远端 SSH 连续两次连接超时，停止新上传/启动动作并报告；TCP 能连接但 SSH banner 不响应不能确定故障根因。保留本地产物，请用户检查云控制台，不无限轮询、重启或重复启动构建。

## 5. 验收与回退

- 容器：`docker compose -p bazi ps`，后端和 MySQL 健康，检查新容器日志的迁移、素材注入失败；日志先筛选并脱敏。
- MySQL：通过容器内客户端只读核对迁移版本、业务表和有效素材数量。首次基线曾为 9 张表、40 条素材，这是历史值，实际应对照本次 migrations 与素材 manifest。MySQL `key` 是保留字，素材种子出现 Error 1064 时部署不可视作完整成功；不要现场改单条数据掩盖源码问题。
- 后端：主机回环 `http://127.0.0.1:8080/health` 的响应应为 `{"status":"ok"}`。这只是存活证明，不代表数据库或业务正常。
- 代理：经前端 `/api/auth/me` 未认证返回 401；素材选择的真实路由是 `/api/element-assets/select`，不是 `/api/element-assets` 的 GET。
- 前端：`/`、SPA 深链、实际入口 JS/CSS 与一张实际素材图片；同时校验类型/内容，SPA 的 200 回退页不能冒充静态资源。需要时在浏览器做只读渲染 smoke。
- 公网：从本地再请求 `http://47.119.120.17/` 或本次域名。本机正常但公网超时，只说明入口尚不可达，安全组/防火墙是待排查原因，不直接断言云安全组。报告需要用户放行的端口，不擅改。没有域名/证书则如实说明暂为 HTTP。
- 应用新版本失败时，保存失败现场，确认状态未被第三方改动后，仅回退应用目录/旧镜像一次并验收。迁移过的数据库不能靠回退二进制保证兼容；不自动回滚 schema、导入 dump 或删卷，需明确恢复批准。

交付本地发布目录和 checksum、服务器路径、容器/镜像、数据库后端与持久卷、HTTP/TLS 状态及各层实际证据。注明是否包含未提交修改、未启用的 RAG/管理员、尚未通过的检查。创建 skill 的校验或本地构建不能被说成已经重新部署成功。
