---
name: kotlin-guide
description: "Kotlin 专题统一入口：用于 Java 转 Kotlin、Kotlin 多平台与 Android 构建迁移、Kotlin/Native 构建性能、不可变集合升级、Kotlin Toolchain 使用及插件开发，以及 JPA 实体映射。按任务读取 Kotlin/kotlin-agent-skills 的专题引用；不因普通 Kotlin 编码而启动构建工具迁移，不替代 Compose 界面与动画专项指导。"
license: Apache-2.0
---

# kotlin指南

参照“Go 开发指南”的结构，将 `Kotlin/kotlin-agent-skills` 的全部 10 个专题保存为本地引用。只有本文件是 skill 入口；`references/topics/` 中的文档不会独立注册为技能或工具，也不需要安装上游插件。

## 先明确项目和任务

先读取用户目标、项目规范及相关配置，确定所需专题。Gradle 是由项目构建脚本和 wrapper 配置的构建工具，负责依赖、编译和任务执行；本指南不改变项目已经选定的构建工具。

上游部分专题中的 **Kotlin Toolchain** 指 JetBrains 的一套构建工具，使用 `project.yaml`、`module.yaml` 和项目的 `./kotlin` wrapper 配置并运行任务；它与 Gradle/Maven 不同，也不是泛指 Kotlin 编译器或 Java 工具链。只有项目确实使用它，或用户明确要求评估、迁移或创建相关项目时，才采用对应指导。

本副本以构建和迁移专题为主。普通 Kotlin 语法、协程、Compose 界面或动画问题若未落入下表范围，不要硬套迁移流程，也不要宣称本副本已覆盖相应能力。Compose 是由应用代码与项目依赖配置的声明式界面框架；需要时配合已安装的 `compose-expert` 等专项技能。

## 按任务读取

下面的名称是引用文档名。先读取直接相关的 `guide.md`；已确定多个专题时可并行读取。完整范围、每个专题的版本和附属资源见[专题索引](references/catalog.md)。

| 当前任务 | 读取专题 | 适用边界 |
| --- | --- | --- |
| Java 源文件转为 Kotlin | [Java 转 Kotlin](references/topics/kotlin-tooling-java-to-kotlin/guide.md) | 先识别项目使用的框架，按授权文件或当前模块转换；保留注解、序列化和 Java 调用语义 |
| 多平台项目升级 Android Gradle Plugin 9 | [AGP 9 迁移](references/topics/kotlin-tooling-agp9-migration/guide.md) | Kotlin Multiplatform（KMP）由项目配置共享代码和各平台目标；AGP 是 Google 的 Android Gradle 构建插件。先核实版本和模块类型，再选择迁移路径 |
| Apple 平台依赖从 CocoaPods 转为 Swift Package Manager | [CocoaPods 迁移](references/topics/kotlin-tooling-cocoapods-spm-migration/guide.md) | 两者都是由项目配置的依赖管理工具；按项目实际依赖和平台能力处理，不因使用 Kotlin 自动迁移 |
| 不可变集合升级到 0.5.x | [不可变集合迁移](references/topics/kotlin-tooling-immutable-collections-0-5-x-migration/guide.md) | 仅用于 `kotlinx.collections.immutable` 的相应升级；根据项目版本及编译提示确定改法 |
| iOS 共享模块编译或链接慢 | [Kotlin/Native 构建性能](references/topics/kotlin-tooling-native-build-performance/guide.md) | Kotlin/Native 将 Kotlin 编译为本机代码；先区分本地与持续集成、调试与发布，再按实际任务测量 |
| 已有 Kotlin Toolchain 项目的构建与配置 | [Kotlin Toolchain](references/topics/kotlin-tooling-kotlin-toolchain/guide.md) | 使用该项目现有 wrapper 和配置；上游新项目默认选型属于参考建议，不覆盖用户选择 |
| 整个 Gradle 项目迁到 Kotlin Toolchain | [项目迁移](references/topics/kotlin-tooling-gradle-to-kotlin-toolchain-project/guide.md) | 需要明确的项目迁移目标；不是日常修复 Gradle 构建问题的默认路径 |
| 将已有单个 Gradle 插件迁到 Kotlin Toolchain | [插件迁移](references/topics/kotlin-tooling-gradle-to-kotlin-toolchain-plugin/guide.md) | 只迁移目标插件；需要时补读 Toolchain 基础指导 |
| 从零编写 Kotlin Toolchain 本地插件 | [插件编写](references/topics/kotlin-tooling-kotlin-toolchain-plugin-authoring/guide.md) | 先判断声明式配置是否已能表达需求；与迁移已有 Gradle 插件区分 |
| Kotlin 后端的数据库实体映射 | [JPA 实体映射](references/topics/kotlin-backend-jpa-entity-mapping/guide.md) | JPA 是将对象映射到数据库记录的规范，通常由 Spring Data JPA 与 Hibernate 依赖和项目配置启用；只用于采用这类持久化方案的项目 |

专题中的 `references/`、`assets/`、`scripts/` 和 `evals/` 保留原目录结构。需要具体框架规则、迁移清单或案例时，再读取正文中的附属链接。上游提到“调用另一个 skill”时，通过本地索引读取对应文档，不调用或安装同名独立技能。

## 使用脚本和验证

保留的两个 Shell 脚本用于静态读取项目文件；它们随本指南分发，但不会因加载入口而自动执行。执行前先阅读脚本，并明确传入授权项目路径。正文中的脚本相对路径基于该专题目录，不是用户项目目录。例如：

```bash
bash /home/skynit/.codex/skills/kotlin-guide/references/topics/kotlin-tooling-agp9-migration/scripts/analyze-project.sh /path/to/project
bash /home/skynit/.codex/skills/kotlin-guide/references/topics/kotlin-tooling-native-build-performance/scripts/audit-native-build.sh /path/to/project
```

`/path/to/project` 需要替换为本次实际项目路径；迁移本指南到其他位置时，以当前 `SKILL.md` 所在目录定位脚本，不依赖上述本机路径。脚本可能扫描整个项目；用户限定当前模块或文件时，先检查其参数是否支持该范围，不支持就直接读取允许范围内的文件，不扩大扫描。

- 用户指令、项目规范和已有授权优先。只读审查不改源码；引用中的升级、安装、下载、删除和 Git 提交示例不是执行授权。
- 不因读取指导安装 Gradle、Kotlin Toolchain、Android SDK 或额外插件，不改项目构建工具。需要变更时遵循本次任务的实际授权。
- 验证只使用当前模块、包或受影响文件的必要检查。上游 `./gradlew build`、`allTests`、`kotlin check` 等宽范围示例必须服从项目限制；优先确认模块任务，再执行具体任务。不得为使用指南而运行全仓测试或无关构建。
- iOS 编译、链接及 Xcode 验收需要实际可用的平台和工具。只有静态文件或日志证据时，明确说明验证范围，不声称已经通过构建。
- 引用包含固定版本的迁移建议；涉及当前兼容矩阵、弃用状态、下载地址及依赖版本时，核实相应官方文档。上游元数据中记载的测试模型与评估时间仅是来源记录，不代表本地验证结果。

## 来源和更新

上游为 `Kotlin/kotlin-agent-skills`，插件声明版本 **1.0.0**；本地副本固定到提交 **c2f90697bf71966a117a13340d5fff787f004140**，引入日期 **2026-10-30**。不同专题有各自版本，以[索引](references/catalog.md)与[来源清单](references/source.json)为准。Apache-2.0 许可证见 [LICENSE](references/LICENSE)。

原 `SKILL.md` 已改为普通 `guide.md`，移除用于注册技能的 YAML 元数据，保留作者与版本记录，并调整实际文档链接；修改过的文件有本地修改说明。所有附属资料和脚本完整保留，上游插件注册配置不导入。本指南是本地整合版，不是上游发布的独立产品。

后续升级时从明确选定的上游提交重新导入，核对新增或移除的专题，保留许可证与归属说明，更新索引和文件校验清单，检查相对链接及脚本语法。普通使用不自动刷新资料。
