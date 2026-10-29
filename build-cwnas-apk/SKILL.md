---
name: build-cwnas-apk
description: 为 CWNAS Flutter 客户端构建并验收用于扫码绑定的 Android Release APK。用户要求“打包扫码 APK”“构建 CWNAS 安卓包”或需要指定穿透平台域名的移动端安装包时使用；不用于 Web 前端、Go 后端或应用商店签名发布。
---

# CWNAS Android APK

在 `/home/skynit/workspace/cwnas_client` 构建移动端扫码 APK。默认平台域名为 `filesharing.asia`，用户指定其他域名时以用户输入为准。

## 边界

- 使用 `lib/mobile_main.dart`，不要把 Web 入口或 `isPlatformWeb=true` 带入原生 APK。
- 只构建和验收 APK，不修改客户端源码、Gradle 配置或依赖版本；若构建必须改源码，停止并说明原因。
- 保留工作区现有未提交修改，不执行 `flutter clean`、依赖升级、全量测试、提交或推送。
- 平台域名使用不带协议和路径的 authority，例如 `filesharing.asia`。
- 默认生成同时包含 `arm64-v8a`、`armeabi-v7a` 和 `x86_64` 的通用 APK。

## 执行

直接运行随技能提供的脚本：

```bash
/home/skynit/.codex/skills/build-cwnas-apk/scripts/build_apk.sh \
  --repo /home/skynit/workspace/cwnas_client \
  --host filesharing.asia
```

用户指定平台域名时替换 `--host`；用户指定客户端目录时替换 `--repo`。脚本会：

1. 检查 Flutter、Android SDK、rustup stable 和 Android Rust targets。
2. 隔离误用系统 `/usr` Rust sysroot 的 Cargokit 可再生缓存，但不删除缓存或源码。
3. 使用 `--release --target lib/mobile_main.dart --dart-define=CW_PLATFORM_WEB_HOST=<host>` 构建。
4. 在 `build/releases/` 生成带版本、域名和 `scan` 标识的 APK 副本。
5. 验证 APK 签名、zipalign、包名、版本、相机权限、ABI、内嵌平台域名和 SHA-256。
6. 比较构建前后的 Git 状态；若源码状态变化则验收失败，但不自动回滚用户文件。

脚本失败时先根据实际错误定位环境或依赖问题，不通过修改源码掩盖工具链故障。NDK、Gradle、AGP 或第三方插件的弃用提示若未导致非零退出，仅作为警告记录。

## 交付

向用户提供 `build/releases/` 下 APK 的绝对可点击路径，并报告：

- 构建类型、目标平台域名、应用 ID、版本和文件大小；
- 支持的 ABI、相机权限、签名与对齐验证结果；
- SHA-256；
- 签名证书身份。若为 Android Debug 证书，明确说明仅适合安装验收，不能作为正式商店发布包；
- 是否修改源码、是否运行测试，以及未进行真机扫码验证时的剩余验证范围。
