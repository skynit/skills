# kotlin指南全部专题索引

覆盖上游提交 `c2f90697bf71966a117a13340d5fff787f004140` 的全部 10 个专题，插件声明版本为 1.0.0；专题版本单独记录。每项都是普通引用文档，只通过 `$kotlin-guide` 入口按任务读取。

| 专题 | 适用任务 | 上游专题版本 |
| --- | --- | --- |
| [kotlin-backend-jpa-entity-mapping](topics/kotlin-backend-jpa-entity-mapping/guide.md) | Kotlin 后端的 JPA 实体、标识与相等性、唯一约束、关联关系和查询加载策略 | 1.0.0 |
| [kotlin-tooling-agp9-migration](topics/kotlin-tooling-agp9-migration/guide.md) | Kotlin 多平台项目迁移到 Android Gradle Plugin 9，按模块类型选择拆分和配置迁移路径 | 1.0.0 |
| [kotlin-tooling-cocoapods-spm-migration](topics/kotlin-tooling-cocoapods-spm-migration/guide.md) | 多平台项目的 Apple 平台依赖从 CocoaPods 转到 Swift Package Manager | 1.0.0 |
| [kotlin-tooling-gradle-to-kotlin-toolchain-plugin](topics/kotlin-tooling-gradle-to-kotlin-toolchain-plugin/guide.md) | 将单个已有 Gradle 插件的构建任务和配置迁移到 Kotlin Toolchain 本地插件 | 0.1.0 |
| [kotlin-tooling-gradle-to-kotlin-toolchain-project](topics/kotlin-tooling-gradle-to-kotlin-toolchain-project/guide.md) | 将整个 Gradle Kotlin 项目及其持续集成配置迁移到 Kotlin Toolchain | 0.1.0 |
| [kotlin-tooling-immutable-collections-0-5-x-migration](topics/kotlin-tooling-immutable-collections-0-5-x-migration/guide.md) | kotlinx.collections.immutable 升级到 0.5.x，依据编译提示迁移返回新集合的方法 | 2.4.0 |
| [kotlin-tooling-java-to-kotlin](topics/kotlin-tooling-java-to-kotlin/guide.md) | 将 Java 转为 Kotlin，按 Spring、Hibernate、Jackson 等项目框架保留行为 | 1.0.0 |
| [kotlin-tooling-kotlin-toolchain](topics/kotlin-tooling-kotlin-toolchain/guide.md) | 使用已选定的 Kotlin Toolchain 构建工具，处理项目配置、模块、构建和验证 | 0.1.0 |
| [kotlin-tooling-kotlin-toolchain-plugin-authoring](topics/kotlin-tooling-kotlin-toolchain-plugin-authoring/guide.md) | 从零编写 Kotlin Toolchain 本地插件，扩展声明式配置无法表达的构建步骤 | 0.1.0 |
| [kotlin-tooling-native-build-performance](topics/kotlin-tooling-native-build-performance/guide.md) | 定位 Kotlin/Native 的 iOS 编译、链接、缓存、目标选择与生成代码成本 | 1.0.0 |

## 附属分析脚本

- [AGP 9 迁移分析脚本](topics/kotlin-tooling-agp9-migration/scripts/analyze-project.sh)：静态读取指定项目的构建配置和模块布局。
- [Kotlin/Native 构建分析脚本](topics/kotlin-tooling-native-build-performance/scripts/audit-native-build.sh)：静态查找可能拖慢构建的配置，输出位置与参考资料。

脚本不会自动运行。使用前读取脚本并确认允许的读取范围；用户只授权当前模块而脚本会扫描整个项目时，改为直接检查授权文件。文档里的相对脚本和参考路径按所在专题目录解析。

完整来源、作者、版本和文件校验记录见 [source.json](source.json)，许可证见 [LICENSE](LICENSE)。
