# 上游来源

以下是本仓库采用的上游版本。技能可能保留本地触发规则、路径和说明，不一定与上游逐字相同。

| 技能 | 上游版本 | 上游许可 |
| --- | --- | --- |
| `compose-expert` | [aldefy/compose-skill `v2.5.2`](https://github.com/aldefy/compose-skill/releases/tag/v2.5.2) | [MIT](licenses/aldefy-compose-skill.txt) |
| Addy Osmani 的 11 个工程技能 | [addyosmani/agent-skills `0.6.17`](https://github.com/addyosmani/agent-skills/releases/tag/0.6.17) | [MIT](licenses/addyosmani-agent-skills.txt) |
| Emil Kowalski 的 13 个技能 | [emilkowalski/skills `64eb3de`](https://github.com/emilkowalski/skills/commit/64eb3deb9a5fbfa041faf783e0bc3fd635872e9c) | [MIT](licenses/emilkowalski-skills.txt) |
| `software-factory` | [mattpocock/skills `abeeaf9`](https://github.com/mattpocock/skills/tree/abeeaf95660ba9e8b7c753eb38f441ca707a8823/skills/in-progress/software-factory) | [MIT](licenses/mattpocock-skills.txt) |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill `e8b065f`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/commit/e8b065f0f3aaf2e680fd125f000e4f5e351ed108) | [MIT](licenses/nextlevelbuilder-ui-ux-pro-max-skill.txt) |
| `impeccable` | [pbakaus/impeccable `skill-v4.10.0`](https://github.com/pbakaus/impeccable/releases/tag/skill-v4.10.0) | [Apache-2.0](impeccable/LICENSE)、[第三方声明](impeccable/NOTICE.md) |
| `reverse-engineer-anything` | [morluto/rea `rea-agents-6.10.1`](https://github.com/morluto/rea/releases/tag/rea-agents-6.10.1) | [MIT](reverse-engineer-anything/LICENSE) |

## 运行时依赖

- `impeccable` 保留本地触发规则。仓库不包含引擎二进制；找不到本机引擎时，启动脚本会下载并校验配套引擎 [`0.1.27`](https://github.com/pbakaus/impeccable/releases/tag/engine-v0.1.27)。
- `reverse-engineer-anything` 的技能文件和参考资料已纳入仓库。命令行回退示例固定使用 REA `6.10.1`；克隆仓库不等于安装 REA 或配置工具连接。
