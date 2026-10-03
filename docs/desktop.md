# 桌面管理器

> 面向维护者与贡献者：它是本仓库的评测与质量控制台，需要**克隆本仓库**并装好 Python（评测脚本）与 Node.js（`bin/cli.mjs`）。
> 只想用祖师的话，不需要它——`npx master-skill install --all` 即可，见 [install.md](install.md)。

原生桌面控制台(纯 Rust,egui,单二进制,无 Electron),统一查看预置技能的安装状态、fidelity 评测覆盖率、运行追踪与质量门禁:

![Master-skill Desktop Manager](assets/desktop-manager.png)

**下载**：[Releases](https://github.com/xr843/Master-skill/releases) 提供 Linux（x86_64）/ Windows（x86_64）/ macOS（仅 Apple Silicon，aarch64）预编译二进制，需在本仓库克隆的根目录运行（它会调用仓库里的 `scripts/` 与 `bin/`）。v0.12.1 起，Linux / macOS 建议下载对应的 `.tar.gz`，解包后保留可执行位；裸二进制仍保留以兼容旧链接，使用时需先 `chmod +x`。每个 release（v0.12.1 起）附带 `SHA256SUMS`，可用 `sha256sum --check --ignore-missing SHA256SUMS` 核对下载文件，并附构建溯源证明，可用 `gh attestation verify <文件> --repo xr843/Master-skill` 验证（需较新版本的 gh CLI：实测 2.51 报 `unsupported tlog public key type`，2.100 正常）。**v0.12.1 之前没有可用的 Windows 桌面二进制**（更早的版本无法调用 Python 与 npm，v0.12.0 未能构建出 Windows 版）；v0.12.1 起改为按平台解析；v0.12.2 起，发布流水线会在 Linux、Windows、macOS 三个平台上实际运行打包好的桌面端（`--help` 与 `--baseline`），如仍找不到解释器，可用环境变量 `MASTER_SKILL_PYTHON` / `MASTER_SKILL_NPM` 指定。Windows 版是控制台程序，双击启动时会同时出现一个控制台窗口：改成图形界面程序虽可去掉它，但实测会让 PowerShell 下重定向或管道输出命令行结果时崩溃。macOS 二进制未签名，首次运行需右键“打开”或执行 `xattr -d com.apple.quarantine <文件名>` 解除隔离。

**从源码构建**（需要 Rust 1.95+）：

```bash
cd desktop && cargo build --release
./target/release/master-skill-desktop            # 图形界面
./target/release/master-skill-desktop --baseline # 无头跑 fidelity dry-run 基线
```
