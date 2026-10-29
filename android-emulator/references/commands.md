# 本机操作示例

按需要读取，不默认执行整套命令。示例变量要替换为本次核实的值，不照抄历史设备序号。`task_sdk`、`task_serial` 等只用于当前任务，不覆盖系统环境变量。

## 定位与识别

此机历史 SDK 路径为 `/home/skynit/Android/Sdk`，常见工具为：

- 模拟器：`/home/skynit/Android/Sdk/emulator/emulator`
- ADB：`/home/skynit/Android/Sdk/platform-tools/adb`
- scrcpy：通过 `command -v scrcpy` 查找。

```bash
task_sdk=/home/skynit/Android/Sdk
"$task_sdk/emulator/emulator" -list-avds
"$task_sdk/platform-tools/adb" devices -l
```

从上一步选择实际运行的模拟器后设置设备变量，以下序号仅为历史示例：

```bash
task_serial=emulator-5556
"$task_sdk/platform-tools/adb" -s "$task_serial" emu avd name
"$task_sdk/platform-tools/adb" -s "$task_serial" shell getprop ro.build.version.release
"$task_sdk/platform-tools/adb" -s "$task_serial" shell getprop ro.build.version.sdk
"$task_sdk/platform-tools/adb" -s "$task_serial" shell getprop ro.product.cpu.abilist
"$task_sdk/platform-tools/adb" -s "$task_serial" shell getprop sys.boot_completed
```

`sys.boot_completed` 为 `1` 才表示系统启动完成；为每次检查设置短超时，整体检查有截止时间。设备列表可能同时有实体手机，应结合 `emulator-*` 和 AVD 名称确认目标。

本机曾有 `DSHX_API34` 和 `DSHX_API36` 两个 AVD；后者曾提供 Android 16、x86_64 和 Chromium 133 的网页组件。**这些是 2026-10-21 的历史记录，使用前重新查询。** 对需要 Chromium 126 的应用，不根据 Android API 数字推断网页组件足够新，应读实际版本：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" shell dumpsys webviewupdate
```

## 启动系统

先确认目标 AVD 未在运行。通过执行工具的后台会话运行，返回后保存会话标识和日志位置；不要阻塞等待模拟器进程退出。

```bash
"$task_sdk/emulator/emulator" \
  -avd DSHX_API36 \
  -no-audio \
  -no-snapshot \
  -no-window \
  -gpu swangle
```

此为本机已知渲染故障后的优先组合，原因及适用范围见下节。执行前通过当前版本帮助确认支持；`-no-snapshot` 按是否需要完整启动选择。省略 `-no-window` 可以打开模拟器自带窗口。不要为了复现示例而重启已稳定运行的实例。

需要固定端口时，可以在已确认端口空闲后增加 `-port 5556`，对应示例设备序号 `emulator-5556`；这是历史配置，不是所有任务的固定端口。默认允许模拟器选择空闲端口，启动后重新发现序号。

缺失镜像或 AVD 时，先查看 SDK 与配置，不直接下载。模拟器参数查询：

```bash
"$task_sdk/emulator/emulator" -help-all
```

按已安装的 `sdkmanager`、`avdmanager` 帮助准备具体创建命令；系统 API、镜像类型、架构和磁盘大小由项目约束决定，不预设下载最新版。`sdkmanager` 负责安装 SDK/镜像，`avdmanager` 负责根据已有镜像创建虚拟设备配置，二者不等同于启动系统。

## 本机渲染故障记录

来源：用户提供的 2026-10-21 崩溃诊断；本技能更新时另外只读核对了本机模拟器版本与 `-help-gpu`，没有重新分析 core 或重新执行压力测试。

- **环境**：Android Emulator 37.1.11（build 15917651）；API 36、`google_apis`、x86_64，`DSHX_API36`，无自带窗口；应用使用 Compose/Skia 绘制界面。
- **故障特征**：16:32:31、16:39:32、16:43:46 三次 `qemu-system-x86_64-headless` 在 `RenderThread`（模拟器负责绘制的线程）发生 SIGSEGV/SEGV_MAPERR，即读取了未映射地址。三次指令相同：`movdqu 0x184f0(%rax,%rcx,1),%xmm5`，RIP 低 12 位为 `0xb8b`。报告将匿名可执行内存中的指令定位为 SwiftShader 的着色器 JIT；JIT 是渲染器在运行时生成机器码的过程。
- **路径区别**：SwiftShader 是用 CPU 进行图形渲染的软件。GLES 是 Android 常用图形接口；本次 `swiftshader`、`swiftshader_indirect` 和 `software` 都进入同一套 SwiftShader GLES 路径。`software` 的 Vulkan 后端使用 Lavapipe 时仍命中同一崩溃，所以仅切换这三种模式不构成独立绕过方案。
- **当前绕过**：`swangle` 通过 ANGLE（把图形接口调用转换到其他图形后端的库）将 GLES 转到 Vulkan，再由 SwiftShader 执行，避开本次出错的 GLES 路径。16:44 切换后，用户报告前台应用约 6 分钟、5000 多帧未再崩溃；这是短时有效证据，不是长期稳定承诺。
- **判断界限**：现有报告指向模拟器的软件渲染缺陷，无 OOM 或内核/驱动报错证据。不要把这次故障当成 AVD 配置、内存容量或宿主显卡问题去盲目调参；其他崩溃签名仍需独立诊断。

本机该版本 `-help-gpu` 列出 `swangle`，说明它使用 ANGLE 配合 SwiftShader；旧名称 `swiftshader_indirect` 未在该帮助中列出，不再作为推荐启动示例。

需要性能时可按当前任务范围单独评估 `-gpu host`，它使用宿主显卡驱动；切换后重新验证画面与截图，不将其作为必须执行的第二轮测试。不要声称宿主硬件模式必定可用，也不要为了试它打断现有实例。

只有用户要求上报时才向 Android Emulator 的 Google Issue Tracker 提交。准备可审阅的版本、镜像、最小复现步骤、渲染模式、线程/信号、回溯和故障指令，不直接附数百 MB 的 core。用户报告三个 core 约占 2.6 GB；空间与数量会变，清理前重新核实，未获清理授权不删除。

## 安装和打开应用

已授权构建时，遵守仓库指定的 JDK 和当前模块命令。例如 Android Gradle 项目的 app 模块：

```bash
JAVA_HOME=/usr/lib/jvm/java-17-openjdk ./gradlew :app:assembleDebug
```

JDK 是运行 Gradle 构建工具的 Java 开发环境，版本以项目要求为准。模块名与 APK 路径不是所有项目都叫 `app`。

安装已有 APK：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" install -r /absolute/path/to/app-debug.apk
```

通过 SDK 中已安装的 `aapt`、`aapt2` 或 `apkanalyzer` 查看 APK 包名、启动页面和架构，参数按本机帮助确认。已知包名后，也可以用 Android 包管理器核实启动入口：

```bash
task_package=local.dshx.app
"$task_sdk/platform-tools/adb" -s "$task_serial" shell cmd package resolve-activity --brief "$task_package"
```

从结果取得组件名后启动。以下组件仅为 DSHX 示例，不是其他项目的默认值：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" shell am start -n local.dshx.app/.MainActivity
```

安装错误要区分签名、版本、架构和空间，不自动 `uninstall` 或 `pm clear`；前者卸载应用，后者清空数据，会破坏已有验证数据或会话。

## 打开 scrcpy 本机窗口

```bash
scrcpy --help
scrcpy \
  --serial "$task_serial" \
  --window-title "Android 测试 · $task_serial" \
  --no-audio \
  --no-clipboard-autosync
```

仅观察时额外加 `--no-control`。通过后台会话运行并记录本次会话；窗口已属于当前任务时优先复用。镜像窗口关闭不会结束 Android 系统。

## 界面结构与日志

UI Automator 导出用于定位控件，不是截图：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" shell uiautomator dump /sdcard/current-task-ui.xml
"$task_sdk/platform-tools/adb" -s "$task_serial" shell cat /sdcard/current-task-ui.xml
```

实际执行要为本次任务选唯一文件名，解析时只输出相关控件和 `bounds`（设备坐标中的边界矩形）。根据最新矩形中心点击，不根据 scrcpy 窗口像素或历史截图猜坐标。导出可能含输入内容，先筛选/脱敏再展示。

读取应用进程编号：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" shell pidof "$task_package"
```

取得实际 PID 后，先检查该设备 `logcat --help` 支持的参数，再按 PID 和时间限制读日志。不要直接输出全量 `logcat -d`；访问地址的 token、请求头和密钥可能出现在日志中。

本机界面截图按 [Niri 窗口截图技能](../../niri-window-screenshot/SKILL.md) 执行：查实时窗口 ID，保存后打开检查，不改用设备截图。

## 停止与清理

用户要求关闭整个模拟器时，核对设备身份后执行：

```bash
"$task_sdk/platform-tools/adb" -s "$task_serial" emu avd name
"$task_sdk/platform-tools/adb" -s "$task_serial" emu kill
```

只要求关闭显示窗口就结束本次 scrcpy 会话。只有本次自己创建的临时文件和端口转发才纳入清理；不删除 AVD 数据、共享锁或其他任务的转发。

## 官方资料

- Android Emulator 命令行：https://developer.android.com/studio/run/emulator-commandline
- ADB 与安装命令：https://developer.android.com/tools/adb
- scrcpy 参数与行为：https://github.com/Genymobile/scrcpy/tree/master/doc

文档版本可能与本机不同，执行参数以本机帮助为准。
