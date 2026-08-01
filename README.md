# DJI LUT 批量转换工具

将 DJI D-Log M 视频批量应用 LUT 并转码为 H.264 MP4 的跨平台工具，提供 PySide6 图形界面（GUI）和命令行（CLI）两种使用方式。内置 ffmpeg 与 LUT，开箱即用。

## 功能特性

- **批量转换**：将输入文件夹中的视频（mp4 / mov / m4v / avi / mkv）批量应用 LUT
- **LUT 管理**：内置 DJI OSMO Pocket 3 D-Log M → Rec.709 LUT，支持导入 / 拖拽添加自定义 `.cube` 文件，也可从 [DJI 官网下载](https://www.dji.com/cn/lut)
- **智能编码器**：自动检测当前平台实际可用的编码器（macOS 的 `h264_videotoolbox`、Windows 的 NVIDIA `h264_nvenc` / AMD `h264_amf` 等），界面只显示 ffmpeg 真正支持的选项，也可手动指定
- **通用兼容输出**：DJI 素材为 10-bit HEVC，转码时强制下采样为 8-bit `yuv420p` 标准 H.264 High，任意播放器（Windows 媒体播放器、浏览器、手机等）均可直接打开
- **进度展示**：实时显示每个文件的转换进度与运行日志
- **可中断转换**：随时取消，自动清理半成品文件
- **自动跳过**：输出文件（`原名_rec709.mp4`）已存在时自动跳过，避免重复转换
- **配置记忆**：记住上次使用的输入 / 输出目录、LUT 与编码器
- **跨平台**：支持 macOS、Windows、Linux，可打包为免安装应用

## 安装

需要 Python 3.9+。

```bash
pip install -r requirements.txt
```

依赖：
- `PySide6`：GUI
- `static-ffmpeg`：macOS / Linux 开发时自动获取静态 ffmpeg（OSS 开源构建，含 `h264_videotoolbox` / `h264_vaapi`）
- Windows 打包时改用 gyan.dev 的完整构建（`build/download_ffmpeg.py` 自动下载），内置 NVIDIA `h264_nvenc`、AMD `h264_amf`、Intel `h264_qsv`、VAAPI 硬件编码器

ffmpeg 的获取优先级（无需手动安装）：
1. 打包应用内置的 ffmpeg
2. 系统 PATH 中的 ffmpeg
3. `build/assets/` 下的静态 ffmpeg（由 `python build/download_ffmpeg.py` 生成）
4. `static-ffmpeg` / `imageio-ffmpeg` 自动下载

## 使用方法

### GUI

```bash
python gui.py
```

操作步骤：
1. 选择「输入文件夹」（可直接拖拽到输入框）
2. 选择「输出文件夹」
3. 选择 LUT 文件（默认内置 LUT，可点击「导入 LUT…」或直接拖入 `.cube` 文件；点击「DJI LUT 下载」可一键打开或复制 [DJI 官方 LUT 下载链接](https://www.dji.com/cn/lut)）
4. 选择视频编码器（默认自动检测）
5. 点击「开始转换」

### CLI

```bash
python batch_lut.py [-i 输入目录] [-o 输出目录] [--lut LUT文件] [--encoder 编码器]
```

示例：

```bash
# 使用默认的 input/ 和 output/ 目录
python batch_lut.py

# 指定目录与 LUT
python batch_lut.py -i /path/to/videos -o /path/to/output --lut my_lut.cube
```

### 目录结构

```
input/    # 默认输入目录，放置待转换的视频
output/   # 默认输出目录，转换结果（原名_rec709.mp4）
lib/      # 内置 LUT 文件
luts/     # 用户导入的 LUT 文件
```

## 打包发布

提供 PyInstaller 打包脚本，支持三个平台，产出「解压即用」的应用目录与压缩包。

### macOS / Linux

```bash
bash build/build.sh
```

产物：`dist/DJI LUT.app`（macOS，并生成 zip）、`dist/DJI LUT`（Linux，并生成 zip）

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File build/build.ps1
```

产物：`dist/DJI LUT` 及 `dist/DJI-LUT-Converter-Windows.zip`

打包前会先通过 `build/download_ffmpeg.py` 下载静态 ffmpeg 并随包内置，因此应用完全离线可用。Windows 会下载 gyan.dev 的完整构建（含 `h264_nvenc` / `h264_amf` 硬件编码器）；macOS 打包后会自动执行 ad-hoc 签名以减少 Gatekeeper 拦截。

也可以直接使用：

```bash
pyinstaller batch_lut.spec
```

### GitHub Actions

`.github/workflows/build.yml` 会在推送 `main` / `master` 或打 `v*` 标签时自动在三个平台构建并上传构建产物；推送标签时还会自动创建 GitHub Release。

## 技术说明

- 使用 ffmpeg 的 `lut3d` 滤镜应用 `.cube` LUT，视频转码为 H.264（码率 50M，像素格式强制 `yuv420p`），音频转码为 AAC（码率 192k）
- 转换核心逻辑位于 `core.py`，CLI（`batch_lut.py`）与 GUI（`gui.py`）共用
- 内置 LUT：`lib/DJI OSMO Pocket 3 D-Log M to Rec.709 V1.cube`
- Windows 打包的 ffmpeg 来自 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)（含硬件编码器）；macOS / Linux 使用 `static-ffmpeg` OSS 构建

## 相关链接

- [DJI 官网 LUT 下载](https://www.dji.com/cn/lut)：DJI 各机型官方 LUT 文件下载

## 许可证

本工具仅用于个人学习与使用，请遵守 DJI 及 LUT 版权方的相关许可。
