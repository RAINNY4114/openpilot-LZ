# ajouatom_c3-v9 WSL修复落地文档

## 1. 文档目的

这份文档是给 `E:\openpilot_ajouatom_c3-v9` 专门准备的。

目标不是讲原理，而是保证以后重新拉取 `ajouatom/openpilot` 的 `c3-v9` 分支后，可以按本文档一步一步把环境修到可编译、可继续开发，并且能把文档直接给 GPT，让 GPT 按这里的步骤和代码继续修复。

这份文档只针对本地 WSL 开发链路，不允许破坏以下内容：

- `E:\openpilot` 当前稳定主分支
- 现有 NAS 推送链路
- 当前外网设备正在使用的分支

## 2. 已验证环境

- 验证日期：2026-04-10
- Windows 路径：`E:\openpilot_ajouatom_c3-v9`
- WSL 路径：`/mnt/e/openpilot_ajouatom_c3-v9`
- 架构：`x86_64`
- WSL：`WSL2`
- Python：`3.11`

说明：

- 本文档实测环境是 WSL2 + Ubuntu x86_64。
- Ubuntu 24.04 已实测能按本文档修通。
- Ubuntu 22.04 大概率也能用同样思路，但系统包名称和默认工具链可能需要二次确认。

## 3. 分支来源与基本原则

上游目标分支：

- `https://github.com/ajouatom/openpilot/tree/c3-v9`

推荐做法：

1. 主仓库 `E:\openpilot` 继续保持稳定。
2. `E:\openpilot_ajouatom_c3-v9` 只作为单独分支工作目录。
3. 所有修复优先只落在 `E:\openpilot_ajouatom_c3-v9`。

## 4. 重新拉取分支的推荐方式

### 4.1 推荐：从主仓库建立 worktree

在 PowerShell 里执行：

```powershell
git -C E:\openpilot fetch --all
git -C E:\openpilot worktree add E:\openpilot_ajouatom_c3-v9 -B ajouatom_c3-v9 ajouatom/c3-v9
```

如果目录已存在，先确认里面没有要保留的内容，再删除旧目录后重建。

### 4.2 如果不用 worktree，也可以普通 clone

```powershell
git clone -b c3-v9 https://github.com/ajouatom/openpilot.git E:\openpilot_ajouatom_c3-v9
```

普通 clone 更简单，但和主仓库的对象库不共享，磁盘占用更大。

## 5. Worktree 的 `.git` 路径检查

这是最容易复发的问题之一。

### 5.1 正常状态

`E:\openpilot_ajouatom_c3-v9\.git` 内容应该类似：

```text
gitdir: ../openpilot/.git/worktrees/openpilot_ajouatom_c3-v9
```

### 5.2 异常现象

如果在 WSL 里执行某些命令时出现下面这种错误：

```text
fatal: not a git repository: /mnt/e/openpilot_ajouatom_c3-v9/E:/openpilot/.git/worktrees/openpilot_ajouatom_c3-v9
```

说明 `.git` 或内部 worktree 指向了 Windows 绝对路径，WSL 不能直接用。

### 5.3 修复方法

在 PowerShell 里强制改回相对路径：

```powershell
Set-Content E:\openpilot_ajouatom_c3-v9\.git 'gitdir: ../openpilot/.git/worktrees/openpilot_ajouatom_c3-v9'
```

然后在 WSL 里验证：

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
git status
```

## 6. 初次环境安装

### 6.1 进入 WSL

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
```

### 6.2 先同步子模块

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

### 6.3 安装依赖

这个分支有 `tools/op.sh`，优先使用：

```bash
tools/op.sh setup
```

如果 `tools/op.sh setup` 有问题，再执行：

```bash
tools/ubuntu_setup.sh
```

## 7. 常见安装错误与处理

### 7.1 `metadrive-simulator` hash mismatch

典型错误：

```text
Hash mismatch for metadrive-simulator ...
```

这类问题通常是上游 wheel 文件变化、镜像差异或者本地缓存污染导致。

推荐顺序：

```bash
uv cache clean
rm -rf ~/.cache/uv
tools/op.sh setup
```

如果重新跑一遍后恢复正常，就不必再额外改源码。

### 7.2 `rednose found where directory expected`

典型错误：

```text
TypeError: File /mnt/e/openpilot_ajouatom_c3-v9/rednose found where directory expected
```

本质原因通常是 `rednose` / `tinygrad` 这类路径没有正确指向仓库内真实目录。

正确状态应该是：

```bash
ls -ld rednose tinygrad rednose_repo tinygrad_repo
```

期望看到：

```text
rednose -> rednose_repo/rednose
tinygrad -> tinygrad_repo/tinygrad
```

如果不对，执行：

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
rm -f rednose tinygrad
ln -s rednose_repo/rednose rednose
ln -s tinygrad_repo/tinygrad tinygrad
git submodule update --init --recursive
```

## 8. 本分支已验证的 WSL源码修复

下面这些是已经实测过的修复点。以后重新拉取分支后，如果又出现同样问题，可以让 GPT 按这里的代码重新落补丁。

### 8.1 `selfdrive/SConscript`

目的：

- WSL 下跳过 `navd/SConscript`
- 避免桌面环境缺少地图相关依赖时整仓编译被卡住

关键代码：

```python
def is_running_on_wsl2():
  try:
    with open('/proc/version', 'r') as f:
      contents = f.read()
      return 'WSL2' in contents or 'microsoft' in contents.lower()
  except FileNotFoundError:
    return False

SConscript(['pandad/SConscript'])
SConscript(['controls/lib/lateral_mpc_lib/SConscript'])
SConscript(['controls/lib/longitudinal_mpc_lib/SConscript'])
SConscript(['locationd/SConscript'])
SConscript(['modeld/SConscript'])
SConscript(['ui/SConscript'])
if not is_running_on_wsl2():
  SConscript(['navd/SConscript'])
```

### 8.2 `selfdrive/modeld/SConscript`

目的：

- 解决 WSL x86_64 下 tinygrad/LLVM 编译模型时的 CPU LLVM 指针错误
- 典型错误是：

```text
RuntimeError: src:14:33: error: '%v5' defined with type '<2 x ptr>' but expected 'ptr'
```

修复思路：

- 在 WSL 下不要继续走 `CPU_LLVM=1`
- 改为 `CPU_LLVM=0 IMAGE=0 FLOAT16=1`
- 再通过自定义 clang 包装脚本加 `-ffast-math`

关键代码：

```python
import platform

def is_wsl():
  if os.environ.get("WSL_DISTRO_NAME"):
    return True
  try:
    return "microsoft" in platform.release().lower()
  except Exception:
    return False

flags = {
  'larch64': 'DEV=QCOM FLOAT16=1 NOLOCALS=1 IMAGE=2 JIT_BATCH_SIZE=0',
  'Darwin': f'DEV=CPU HOME={os.path.expanduser("~")}',
}.get(
  arch,
  f'DEV=CPU CPU_LLVM=0 IMAGE=0 FLOAT16=1 CC={File("#tools/wsl_clang_fastmath.sh").abspath}'
  if is_wsl() else 'DEV=CPU CPU_LLVM=1'
)
```

### 8.3 `tools/wsl_clang_fastmath.sh`

文件内容：

```bash
#!/usr/bin/env bash
set -e

exec clang -ffast-math "$@"
```

用途：

- 给 WSL 模型编译提供稳定一点的 clang 参数

### 8.4 `selfdrive/ui/SConscript`

目的：

- WSL 下去掉 `OmxCore`
- 去掉 screen recorder
- 去掉 maps / MapLibre 相关构建

关键代码：

```python
def is_running_on_wsl2():
  ...

wsl2 = is_running_on_wsl2()
maps = arch in ['larch64', 'aarch64', 'x86_64'] and not wsl2

if wsl2:
  qt_env.Append(CXXFLAGS=['-DWSL2'])
  base_libs.remove('OmxCore')
  qt_libs.remove('OmxCore')
  qt_src.remove("qt/screenrecorder/screenrecorder.cc")
  qt_src.remove("qt/screenrecorder/omx_encoder.cc")
  print("Building for WSL2. Removing Screen Recorder and MapLibre build")
```

## 9. 编译命令

进入仓库后执行：

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
source .venv/bin/activate
scons -u -j8
```

说明：

- `-j8` 是为了避免 PowerShell 对 `$(nproc)` 的转义影响。
- 如果你已经在纯 WSL bash 里，也可以用 `-j$(nproc)`。

## 10. 启动与验证

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
source .venv/bin/activate
./launch_openpilot.sh
```

验证点：

1. `scons -u -j8` 能完成。
2. `./launch_openpilot.sh` 能启动 UI。
3. 点击基础设置页面不应立即退出。

## 11. 常见错误对照表

### 11.1 `.git` 路径错

错误：

```text
fatal: not a git repository: ... E:/openpilot/.git/worktrees/...
```

处理：

- 修复 `.git` 为相对路径

### 11.2 `rednose found where directory expected`

处理：

- 修复 `rednose` / `tinygrad` 软链接
- 重新同步子模块

### 11.3 tinygrad LLVM 指针错误

错误：

```text
defined with type '<2 x ptr>' but expected 'ptr'
```

处理：

- 使用本文档第 8.2 节的 WSL patch

### 11.4 WSL 图形/地图/录屏相关编译失败

处理：

- 用本文档第 8.4 节 patch

## 12. 给 GPT 的固定提示模板

以后如果重新拉取后又出问题，建议直接把下面这段发给 GPT：

```text
当前仓库路径是 /mnt/e/openpilot_ajouatom_c3-v9，对应 Windows 路径 E:\openpilot_ajouatom_c3-v9。
这是 ajouatom/openpilot 的 c3-v9 分支，本地开发环境是 WSL2 Ubuntu x86_64。
禁止修改 E:\openpilot 稳定主分支，也不要影响 NAS 推送链路。
请优先按仓库内《ajouatom_c3-v9_WSL修复落地文档.md》执行：
1. 先检查 .git worktree 路径是否是相对路径。
2. 检查 rednose 和 tinygrad 是否为正确软链接。
3. 检查 selfdrive/SConscript、selfdrive/modeld/SConscript、selfdrive/ui/SConscript、tools/wsl_clang_fastmath.sh 是否已按文档修改。
4. 在 source .venv/bin/activate 后执行 scons -u -j8。
5. 如果失败，先根据报错匹配文档里的错误对照表，不要直接大改。
```

## 13. 每一步执行后的预期结果

这一节非常重要。

以后不管是你手工修，还是 GPT 修，都不要只执行命令，一定要对照“预期结果”。

### 13.1 `git status`

命令：

```bash
cd /mnt/e/openpilot_ajouatom_c3-v9
git status
```

预期结果：

- 能正常显示当前分支状态
- 不能出现 `not a git repository`

如果失败：

- 先回到第 5 节修 `.git` worktree 路径

### 13.2 `git submodule update --init --recursive`

预期结果：

- 不报 git 仓库路径错误
- `rednose_repo`、`tinygrad_repo` 等目录能正常出现

如果失败：

- 先检查 `.git`
- 再检查网络

### 13.3 `ls -ld rednose tinygrad`

命令：

```bash
ls -ld rednose tinygrad
```

预期结果：

```text
rednose -> rednose_repo/rednose
tinygrad -> tinygrad_repo/tinygrad
```

如果不是软链接：

- 回到第 7.2 节重新建立链接

### 13.4 `tools/op.sh setup`

预期结果：

- 依赖安装完成
- 不出现长期卡死

允许出现但不一定致命的问题：

- 某些下载重试
- 某些 wheel 缓存重建

如果出现 `hash mismatch`：

- 回到第 7.1 节清理 `uv` 缓存

### 13.5 `scons -u -j8`

预期结果：

- 最终看到：

```text
scons: done building targets.
```

如果失败：

- 优先看报错是否属于第 11 节已有对照项
- 不要先重装整个系统环境

### 13.6 `./launch_openpilot.sh`

预期结果：

- 可以进入 UI
- 不会一启动就退出

## 14. 故障分支处理表

以后重拉分支后，建议严格按下面顺序排。

### 14.1 第一层：仓库是否正常

检查：

```bash
git status
```

如果失败：

- 修 `.git` worktree 路径

### 14.2 第二层：子模块和软链接是否正常

检查：

```bash
git submodule update --init --recursive
ls -ld rednose tinygrad
```

如果失败：

- 修 `rednose` / `tinygrad` 软链接

### 14.3 第三层：依赖是否装好

检查：

```bash
tools/op.sh setup
```

如果失败：

- 先清 `uv` 缓存
- 再重跑 setup

### 14.4 第四层：是否是 WSL tinygrad / LLVM 问题

如果编译报：

```text
defined with type '<2 x ptr>' but expected 'ptr'
```

处理：

- 检查 `selfdrive/modeld/SConscript`
- 检查 `tools/wsl_clang_fastmath.sh`

### 14.5 第五层：是否是 WSL UI/地图/录屏问题

如果编译报 Qt、MapLibre、Omx、screen recorder 相关错误：

- 检查 `selfdrive/SConscript`
- 检查 `selfdrive/ui/SConscript`

## 15. 最终验收清单

只有下面这些都通过，才算这条分支在 WSL 本地修复完成。

### 15.1 基础验收

- `git status` 正常
- `git submodule update --init --recursive` 正常
- `rednose` 和 `tinygrad` 是正确软链接

### 15.2 编译验收

- `source .venv/bin/activate` 后环境正常
- `scons -u -j8` 结束时出现 `scons: done building targets.`

### 15.3 启动验收

- `./launch_openpilot.sh` 能启动 UI
- UI 不会立即退出

## 16. 这份文档的维护原则

以后如果这个分支又踩到新坑，更新这份文档时要遵守下面规则：

1. 先记录错误原文。
2. 再记录根因。
3. 再记录实际落地命令和改动文件。
4. 最后补一个“如何验证修好”。

只有这样，下一次重新拉分支时，GPT 才能真正照着文档一步一步修到落地。
