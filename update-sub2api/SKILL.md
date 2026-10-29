---
name: update-sub2api
description: 通过 SSH 和现有 Docker Compose 更新 NAS 上的 sub2api，只拉取并重建应用服务，核对版本、健康状态及数据库和 Redis 是否保持运行。用于“更新 sub2api”“升级 NAS 上的 sub2api”或在线更新超时后的手动镜像升级；不用于更换代理、配置客户端或更新其他容器。
---

# 更新 sub2api

根据本机 Claude 会话中已验证的更新操作，更新指定 NAS 上的 sub2api。用户只要求创建、修改或解释 skill 时，只处理本地技能文件，不连接 NAS 或执行更新。

## 对象与默认环境

| 名称 | 含义与职责 |
| --- | --- |
| sub2api | 本次更新的 API 中转服务，由部署者通过 Docker 运行；这里更新服务端程序，不修改调用它的客户端。 |
| NAS | 承载服务的网络存储主机；以下 SSH 目标是历史部署地址，执行时必须复核。 |
| SSH | 用于登录远端并执行命令的连接方式，由主机管理员配置账号与认证；本地执行检查不能代替远端检查。 |
| Docker 镜像 | 发布者打包的程序与运行环境；拉取只下载镜像，尚未替换正在运行的服务。 |
| Docker 容器 | Docker 根据镜像创建并运行的实例；本次允许替换 sub2api 实例。 |
| Docker Compose | 按部署者已有配置管理多个服务的工具；服务名来自配置，容器名来自实际运行实例，两者不能未经检查就混用。 |
| PostgreSQL 与 Redis | 部署者为 sub2api 配置的数据库与缓存服务；应用更新不包含它们的镜像升级、容器重建或配置变更。 |

以下值来自 2026-09-14、2026-09-20 的运行记录，并非当前机器状态；本次用户指定的目标优先。

| 项目 | 历史值 |
| --- | --- |
| SSH 目标 | `cwnas@192.168.100.66` |
| Compose 工作目录 | `/home/docker/sub2api` |
| 应用服务名 / 容器名 | `sub2api` / `sub2api` |
| 应用镜像 | `weishaw/sub2api:latest` |
| 依赖容器 | `sub2api-postgres`、`sub2api-redis` |
| 容器内程序 | `/app/sub2api` |
| 远端主机健康接口 | `http://127.0.0.1:8080/health` |

`latest` 是镜像发布者可重新指向的标签，不是固定版本号。程序版本必须从实际运行的容器获取，不把历史版本写成“当前最新版”。

历史在线更新出现过 `download failed: context canceled`，请求耗时约 30 秒；之后通过镜像更新成功。默认使用本流程。该记录不能证明当前所有在线更新都会失败，也不能单凭取消错误断言网络慢是唯一原因。需要追溯时读取 [references/session-evidence.md](references/session-evidence.md)。

## 1. 确认范围与连接

- 用户要求更新 sub2api 时，执行目标核对、单服务更新和验收；不要再次要求确认已经明确授权的普通更新。
- “继续更新”“更新”沿用已明确的 sub2api 目标，不因列出了其他容器就扩大范围。目标存在歧义时，先做相关只读检查，再询问会影响目标选择的缺失信息。
- 只使用现有 SSH 密钥、SSH agent（当前登录会话的密钥代理）或用户本次提供的凭据。缺少凭据时请求补充；不从历史会话复制密码，不把密码放进 skill、命令参数或日志，不默认关闭主机身份校验。
- 本次更新不修改应用源码、代理、客户端、数据库配置或系统配置，也不拉取、重建 Clash、Chrome 等其他服务。

## 2. 远端预检与记录

先确认登录的主机、Docker/Compose 可用性，以及当前 sub2api 容器的 Compose 标签。这些标签由 Compose 创建容器时写入，用于定位所属项目、配置文件和工作目录。沿用原项目名、全部配置文件与原有环境文件选择，不另建一个同名服务的新项目。

```bash
docker inspect sub2api --format 'Project={{index .Config.Labels "com.docker.compose.project"}} Service={{index .Config.Labels "com.docker.compose.service"}} Directory={{index .Config.Labels "com.docker.compose.project.working_dir"}} Files={{index .Config.Labels "com.docker.compose.project.config_files"}}'
```

核实历史默认值仍适用后，在远端工作目录中执行；如需 `-p` 或多个 `-f` 参数，后续所有 Compose 命令保持一致。

```bash
cd /home/docker/sub2api
docker compose config --quiet
docker compose config --services
docker compose ps
docker inspect sub2api sub2api-postgres sub2api-redis --format '{{.Name}} ID={{.Id}} Image={{.Image}} StartedAt={{.State.StartedAt}} Restarts={{.RestartCount}} Status={{.State.Status}}'
docker exec sub2api /app/sub2api -version
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 http://127.0.0.1:8080/health
```

保存上述更新前证据，并只读核对 sub2api 的实际端口、挂载目录及可用磁盘空间。容器名与历史不同则代入实测名称。配置不存在、服务归属不一致、依赖异常或空间不足时先报告具体问题，不通过新建部署或重启依赖绕过。

仅输出需要的镜像、端口、挂载和状态字段；不打印 `.env`、完整容器环境或展开后的 Compose 配置。配置检查用 `config --quiet`。

记录旧容器 `.Image`，它是实际运行镜像的本地 ID，可用于后续定位旧镜像。保留该镜像，不执行镜像清理。检查目标版本的升级说明或已知迁移要求；涉及数据库结构变化时，先确认所需恢复点。数据库容器未重建并不代表应用不会修改数据库结构。

## 3. 只拉取目标应用镜像

读取现有配置中的应用镜像。默认环境仍使用历史标签时，执行：

```bash
docker pull weishaw/sub2api:latest
docker image inspect weishaw/sub2api:latest --format 'ID={{.Id}} Digests={{json .RepoDigests}} Created={{.Created}}'
```

若配置已固定版本或用户指定版本，使用对应镜像引用；不要擅自改成 `latest`。用户明确要求调整版本时，配置变更也只限应用镜像引用，保留其他字段。

让一次拉取任务完整结束，读取真实退出码。历史拉取曾持续十余分钟，可以给单次任务约 20 分钟预算，并按实际进度调整；工具返回后台任务标识时继续等待同一任务，每次等待不超过 60 秒并保持进度沟通。不要因暂时没有输出而并发启动第二次拉取。

超时或 SSH 断开时，先核对远端任务是否还在执行及镜像是否就绪，再决定是否重试。拉取失败时保留旧容器，不进入重建。避免把拉取输出接到 `tail` 后仅检查 `tail` 的退出码；确需管道时在支持的 shell 中启用 `pipefail`，确保前面的失败也能让整条命令失败。

记录新镜像 ID 和仓库 digest。digest 是仓库内容摘要，用来标识下载内容；它与本地镜像 ID 不是同一字段。比较运行镜像与目标镜像时，比较容器 `.Image` 和 `docker image inspect` 的 `.Id`。

目标镜像与运行镜像一致、配置没有待应用变化且当前健康时，无需重建，报告检查完成及实测版本。

## 4. 只重建 sub2api

切换前复核原容器和目标镜像未被其他操作改变。确认目标镜像已完整拉取后，在同一远端工作目录、同一 Compose 项目下执行：

```bash
docker compose up -d --no-deps sub2api
```

这里的 `sub2api` 必须是已核实的 Compose 服务名。`--no-deps` 表示不同时启动或重建它依赖的其他服务；PostgreSQL 和 Redis 应在本次操作前已经正常运行。

不要改用不带服务名的 `docker compose pull` 或 `docker compose up -d`，也不执行 `down`、删卷、全局清理或主机重启。重建失败时保留错误和实际容器状态，进入失败处理，不继续更新其他服务。

## 5. 验收与失败处理

```bash
docker exec sub2api /app/sub2api -version
docker inspect sub2api --format 'Image={{.Image}} Status={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{else}}not_configured{{end}} Restarts={{.RestartCount}}'
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 http://127.0.0.1:8080/health
docker inspect sub2api-postgres sub2api-redis --format '{{.Name}} ID={{.Id}} StartedAt={{.State.StartedAt}} Restarts={{.RestartCount}} Status={{.State.Status}}'
docker compose ps
```

启动可能需要数秒。在约 120 秒的有限窗口内复查启动状态；明确崩溃、持续重启或已输出不可恢复错误时提前结束等待。只检查目标服务的近期启动错误并脱敏，不遍历无关日志或执行全量测试。

完成判定必须同时包含：

- 程序版本从新容器读取成功，运行镜像 ID 与本次目标一致。
- 容器持续运行；已有 Docker 健康检查时结果为 `healthy`。没有配置检查时如实报告，不能把缺失状态称为健康。
- `/health` HTTP 请求成功且响应字段 `status` 为 `ok`；历史响应为 `{"status":"ok"}`。不能只检查退出码或只看 HTTP 200。
- PostgreSQL 和 Redis 的容器 ID、启动时间及重启计数与更新前一致，并保持正常。只有核对过的服务才可声明“未重启”。

健康接口只证明其实际覆盖的服务状态，不据此声称所有模型请求、账号或外部代理均正常。用户需要业务调用验收时，使用其指定的请求与现有凭据，不自行产生收费请求。

新版本失败时，记录版本、镜像、退出码和近期错误。若已确认没有数据库迁移兼容风险，可通过一个临时 Compose 覆盖文件把**应用服务**的 `image` 指向记录的旧镜像 ID，并禁用该服务的拉取；沿用原项目和所有原配置文件，将覆盖文件放在最后，仅执行一次 `up -d --no-deps sub2api`，随后复查版本和健康状态。不要通过重写共享 `latest` 标签回退。

无法确认迁移兼容性、旧镜像缺失或回退失败时，停止新的切换并报告恢复所需信息。恢复数据库、回滚数据库结构或覆盖数据需要相应的明确授权；回退镜像不能自动恢复数据库。

交付时说明目标主机、版本变化、旧/新镜像 ID、重建结果、健康响应，以及依赖是否保持原运行状态。区分“拉取完成”“容器已替换”“验收通过”和“已回退”，不把任一中间步骤当成更新完成。
