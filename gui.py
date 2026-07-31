#!/usr/bin/env python3
"""DJI LUT 批量转换工具 - PySide6 GUI."""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import (
    DEFAULT_LUT,
    app_home,
    available_luts,
    find_ffmpeg,
    get_video_files,
    import_lut,
    pick_encoder,
    convert,
)

APP_NAME = "DJI LUT 批量转换工具"
APP_VERSION = "1.1.0"
SUPPORTED_TEXT = "支持的格式：mp4 / mov / m4v / avi / mkv"

ENCODER_CHOICES = [
    "自动检测",
    "libx264",
    "h264_videotoolbox",
    "h264_nvenc",
    "h264_amf",
    "h264_vaapi",
]

ENCODER_HINTS = {
    "自动检测": "将根据当前系统自动选择最快可用的编码器。",
    "libx264": "通用软件编码器，兼容性最好，但转码速度较慢。",
    "h264_videotoolbox": "Apple 硬件加速（macOS），速度快、功耗低。",
    "h264_nvenc": "NVIDIA 硬件加速（Windows / Linux）。",
    "h264_amf": "AMD 硬件加速（Windows）。",
    "h264_vaapi": "Intel / AMD 硬件加速（Linux）。",
}

STYLE = """
* { outline: none; }
QMainWindow, QWidget#central { background: #F3F5F7; }
QGroupBox {
    background: #FFFFFF;
    border: 1px solid #E3E8EE;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1F2937;
}
QLineEdit, QComboBox, QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #D4DBE3;
    border-radius: 6px;
    padding: 6px 8px;
    color: #1F2937;
    selection-background-color: #0B84C8;
    selection-color: #FFFFFF;
}
QLineEdit:hover, QComboBox:hover { border-color: #9FB3C8; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #0B84C8; background: #FFFFFF; }
QLineEdit[state="ok"] { border: 1px solid #30A46C; background: #F6FCF9; }
QLineEdit[state="error"] { border: 1px solid #E5484D; background: #FEF5F5; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #5B6B7E;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #D4DBE3;
    selection-background-color: #E5F4FB;
    selection-color: #1F2937;
    padding: 4px;
}
QPushButton {
    background: #FFFFFF;
    border: 1px solid #C6D0DA;
    border-radius: 6px;
    padding: 6px 14px;
    color: #1F2937;
    font-weight: 500;
}
QPushButton:hover { background: #F1F5F9; border-color: #0B84C8; color: #0B84C8; }
QPushButton:pressed { background: #E3ECF3; }
QPushButton:disabled { color: #9AA5B1; background: #F2F4F7; border-color: #E2E7EC; }
QPushButton#primaryButton {
    background: #0B84C8;
    color: #FFFFFF;
    border: 1px solid #0B84C8;
    padding: 8px 24px;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #0A74AF; border-color: #0A74AF; color: #FFFFFF; }
QPushButton#primaryButton:pressed { background: #09669C; }
QPushButton#primaryButton:disabled {
    background: #9CC7E0; border-color: #9CC7E0; color: #FFFFFF;
}
QPushButton#dangerButton { color: #E5484D; border-color: #E7B8BA; }
QPushButton#dangerButton:hover { background: #FEF0F0; border-color: #E5484D; color: #E5484D; }
QPushButton#dangerButton:disabled {
    color: #D9A2A4; background: #F7F0F0; border-color: #EFD8D9;
}
QProgressBar {
    background: #E8EDF2;
    border: none;
    border-radius: 6px;
    min-height: 14px;
    max-height: 14px;
    text-align: center;
    color: #1F2937;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B84C8, stop:1 #29B3F0);
    border-radius: 6px;
}
QPlainTextEdit { background: #FAFBFC; font-size: 12px; }
QToolTip {
    background: #1C2333;
    color: #F5F6FA;
    border: 1px solid #1C2333;
    padding: 6px 8px;
    border-radius: 4px;
}
QLabel#infoBanner {
    background: #E5F4FB;
    color: #0A5F8F;
    border: 1px solid #B8E0F5;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
}
QLabel#errorLabel { color: #E5484D; font-size: 12px; }
QLabel#fieldHint { color: #8A97A6; font-size: 11px; }
QLabel#currentFile { color: #5B6B7E; font-size: 12px; }
QLabel#videoCount { color: #5B6B7E; font-size: 12px; }
QLabel#titleLabel { font-size: 17px; font-weight: 700; color: #1F2937; }
QLabel#versionLabel { color: #8A97A6; font-size: 12px; }
QStatusBar { background: #ECF0F4; color: #5B6B7E; }
QStatusBar QLabel { color: #5B6B7E; font-size: 12px; }
"""


class DropLineEdit(QLineEdit):
    """QLineEdit that accepts dropped folders (or a single file)."""

    dropped = Signal(str)

    def __init__(self, accept_dirs=True, parent=None):
        super().__init__(parent)
        self.accept_dirs = accept_dirs
        self.setAcceptDrops(True)

    def _drop_path(self, event):
        if not event.mimeData().hasUrls():
            return None
        path = event.mimeData().urls()[0].toLocalFile()
        if not path:
            return None
        p = Path(path)
        if self.accept_dirs and p.is_dir():
            return path
        if not self.accept_dirs and p.is_file():
            return path
        return None

    def dragEnterEvent(self, event):
        if self._drop_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._drop_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        path = self._drop_path(event)
        if path:
            self.setText(path)
            self.dropped.emit(path)
            event.acceptProposedAction()


class EnvCheckThread(QThread):
    """Background detection of ffmpeg and the best available encoder."""

    result_signal = Signal(object, object, object)

    def run(self):
        ffmpeg, source = find_ffmpeg()
        encoder = pick_encoder(ffmpeg) if ffmpeg else None
        self.result_signal.emit(ffmpeg, source, encoder)


class Worker(QThread):
    log_signal = Signal(str)
    file_signal = Signal(str, int, int)
    progress_signal = Signal(int)
    done_signal = Signal(int, int, int, int)

    def __init__(self, input_dir, output_dir, lut, encoder, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.lut = lut
        self.encoder = encoder
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        ffmpeg, source = find_ffmpeg()
        if not ffmpeg:
            self.log_signal.emit("错误：找不到 ffmpeg，请检查安装。")
            self.done_signal.emit(0, 0, 0, 1)
            return
        self.log_signal.emit(f"使用 ffmpeg（{source}）：{ffmpeg}")
        encoder = self.encoder if self.encoder else pick_encoder(ffmpeg)
        self.log_signal.emit(f"视频编码器：{encoder}")

        videos = get_video_files(self.input_dir)
        if not videos:
            self.log_signal.emit(f"错误：{self.input_dir} 中没有找到视频文件。")
            self.done_signal.emit(0, 0, 0, 1)
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_signal.emit(f"找到 {len(videos)} 个视频，LUT：{self.lut.name}\n")

        succeeded = skipped = failed = cancelled = 0
        for idx, video in enumerate(videos, start=1):
            if self._stop:
                cancelled += 1
                break
            self.file_signal.emit(video.name, idx, len(videos))
            self.progress_signal.emit(0)
            self.log_signal.emit(f"[转换] {video.name}（{encoder}）")

            def on_progress(duration, processed):
                if duration and processed is not None:
                    pct = min(100, int(processed / duration * 100))
                    self.progress_signal.emit(pct)

            result = convert(
                video, self.output_dir, ffmpeg, encoder, self.lut,
                on_progress=on_progress, should_stop=lambda: self._stop,
            )
            if result == "ok":
                succeeded += 1
                self.log_signal.emit(f"[完成] {video.name}\n")
            elif result == "skipped":
                skipped += 1
                self.log_signal.emit(f"[跳过] {video.name}（输出已存在）\n")
            elif result == "cancelled":
                cancelled += 1
                self.log_signal.emit(f"[取消] {video.name}（已终止并清理半成品文件）\n")
                break
            else:
                failed += 1
                self.log_signal.emit(f"[失败] {video.name}\n")

        self.done_signal.emit(succeeded, skipped, failed, cancelled)


def open_in_file_manager(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def make_app_icon():
    pix = QPixmap(64, 64)
    pix.fill(QColor("#0B84C8"))
    painter = QPainter(pix)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Arial", 30, QFont.Bold))
    painter.drawText(pix.rect(), Qt.AlignCenter, "L")
    painter.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(make_app_icon())
        self.resize(760, 620)
        self.setMinimumSize(680, 500)
        self.setAcceptDrops(True)

        self.settings = QSettings("DJI_LUT_Tools", "BatchConverter")
        self.worker = None
        self.running = False
        self.ffmpeg_ok = False
        self.detected_encoder = None
        self._errors = []

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("central")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(10)

        content_layout.addLayout(self._build_header())
        content_layout.addWidget(self._build_info_banner())
        content_layout.addWidget(self._build_path_group())
        content_layout.addWidget(self._build_params_group())
        content_layout.addWidget(self._build_progress_group())
        content_layout.addWidget(self._build_log_group())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

        self._build_status_bar()
        self._load_settings()
        self._connect_signals()
        self._refresh_luts(select=self.restore_lut)
        self._refresh_encoder_hint()

        self.env_thread = EnvCheckThread(self)
        self.env_thread.result_signal.connect(self._on_env_checked)
        self.env_thread.start()

        self._validate()

    # ---------- UI construction ----------

    def _build_header(self):
        header = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("versionLabel")
        header.addWidget(title)
        header.addSpacing(10)
        header.addWidget(version, 0, Qt.AlignBottom)
        header.addStretch()
        return header

    def _build_info_banner(self):
        banner = QLabel(
            "将 DJI D-Log M 视频批量应用 LUT（默认 DJI OSMO Pocket 3 D-Log M → "
            "Rec.709）并转码为 H.264 MP4。已内置 ffmpeg 与 LUT，开箱即用。"
            "输出文件命名为「原名_rec709.mp4」，已存在的文件会自动跳过。"
        )
        banner.setObjectName("infoBanner")
        banner.setWordWrap(True)
        return banner

    def _build_path_group(self):
        group = QGroupBox("输入 / 输出")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.input_edit = self._path_field(
            form, "输入文件夹",
            self.settings.value("input_dir", str(app_home() / "input")),
            hint=SUPPORTED_TEXT,
            tooltip="存放待转换视频的文件夹，支持拖拽文件夹到此处",
        )
        self.video_count_label = QLabel("")
        self.video_count_label.setObjectName("videoCount")
        form.addRow("", self.video_count_label)

        self.output_edit = self._path_field(
            form, "输出文件夹",
            self.settings.value("output_dir", str(app_home() / "output")),
            hint="输出文件为「原名_rec709.mp4」；已存在则自动跳过；目录不存在会自动创建",
            tooltip="转换结果输出到此文件夹，支持拖拽文件夹到此处",
        )
        return group

    def _build_params_group(self):
        group = QGroupBox("转换参数")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.lut_combo = QComboBox()
        self.lut_combo.setToolTip("选择要应用的 LUT 文件（.cube）")
        import_btn = QPushButton("导入 LUT…")
        import_btn.setToolTip("从本地导入 .cube LUT 文件")
        import_btn.clicked.connect(self._import_lut)
        lut_row = QHBoxLayout()
        lut_row.addWidget(self.lut_combo, stretch=1)
        lut_row.addWidget(import_btn)
        form.addRow("LUT 文件", lut_row)
        form.addRow("", self._make_hint(
            "将 D-Log M 色彩转换为 Rec.709。可点击「导入 LUT…」添加其他 .cube 文件，"
            "也可将 .cube 文件直接拖入窗口。"))

        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems(ENCODER_CHOICES)
        self.encoder_combo.setToolTip("视频编码器，默认自动检测")
        form.addRow("视频编码器", self.encoder_combo)
        self.encoder_hint = self._make_hint("")
        form.addRow("", self.encoder_hint)
        return group

    def _build_progress_group(self):
        group = QGroupBox("转换进度")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("")
        self.progress.setToolTip("当前文件的转换进度")
        layout.addWidget(self.progress)

        self.current_label = QLabel("")
        self.current_label.setObjectName("currentFile")
        layout.addWidget(self.current_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("取消当前转换，正在处理的视频会被终止并清理半成品文件")
        self.cancel_btn.clicked.connect(self._cancel_convert)
        self.start_btn = QPushButton("开始转换")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.setToolTip("开始批量转换")
        self.start_btn.clicked.connect(self.start_convert)
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.start_btn)
        layout.addLayout(btn_row)
        return group

    def _build_log_group(self):
        group = QGroupBox("运行日志")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 6, 8, 8)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setPlaceholderText("转换日志将显示在这里…")
        self.log.setFont(QFont("Menlo", 11))
        self.log.setFixedHeight(180)
        layout.addWidget(self.log)
        return group

    def _build_status_bar(self):
        self.status_label = QLabel("正在检测 ffmpeg…")
        self.status_label.setObjectName("statusLabel")
        self.statusBar().addWidget(self.status_label, 1)

    def _path_field(self, form, label, default, hint, tooltip):
        edit = DropLineEdit()
        edit.setText(str(default))
        edit.setToolTip(tooltip)
        button = QPushButton("浏览…")
        button.setToolTip("选择文件夹")
        button.clicked.connect(lambda: self._browse(edit))
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        row.addWidget(button)
        form.addRow(label, row)
        form.addRow("", self._make_hint(hint))
        return edit

    def _make_hint(self, text):
        label = QLabel(text)
        label.setObjectName("fieldHint")
        label.setWordWrap(True)
        return label

    def _connect_signals(self):
        self.input_edit.textChanged.connect(self._validate)
        self.input_edit.dropped.connect(lambda _: self._validate())
        self.output_edit.textChanged.connect(self._validate)
        self.output_edit.dropped.connect(lambda _: self._validate())
        self.lut_combo.currentIndexChanged.connect(self._on_lut_changed)
        self.encoder_combo.currentIndexChanged.connect(self._refresh_encoder_hint)

    # ---------- settings ----------

    def _load_settings(self):
        self.restore_lut = self.settings.value("lut", str(DEFAULT_LUT))
        encoder = self.settings.value("encoder", "自动检测")
        idx = self.encoder_combo.findText(encoder)
        if idx >= 0:
            self.encoder_combo.setCurrentIndex(idx)

    def _save_settings(self):
        self.settings.setValue("input_dir", self.input_edit.text())
        self.settings.setValue("output_dir", self.output_edit.text())
        lut = self.lut_combo.currentData()
        if lut:
            self.settings.setValue("lut", str(lut))
        self.settings.setValue("encoder", self.encoder_combo.currentText())

    # ---------- helpers ----------

    def _browse(self, edit):
        path = QFileDialog.getExistingDirectory(
            self, "选择文件夹", edit.text() or str(Path.home()))
        if path:
            edit.setText(path)
            self._validate()

    def _on_lut_changed(self):
        self._refresh_lut_tooltip()
        self._validate()

    def _refresh_lut_tooltip(self):
        lut = self.lut_path()
        self.lut_combo.setToolTip(str(lut) if lut else "暂无可用 LUT")

    def lut_path(self):
        data = self.lut_combo.currentData()
        return Path(data) if data else None

    def _refresh_luts(self, select=None):
        self.lut_combo.blockSignals(True)
        self.lut_combo.clear()
        for lut in available_luts():
            label = f"内置：{lut.name}" if lut == DEFAULT_LUT else lut.name
            self.lut_combo.addItem(label, str(lut))
        if select:
            idx = self.lut_combo.findData(str(select))
            if idx >= 0:
                self.lut_combo.setCurrentIndex(idx)
        self.lut_combo.blockSignals(False)
        self._refresh_lut_tooltip()

    def _import_lut(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 LUT 文件", "", "LUT 文件 (*.cube);;所有文件 (*)")
        if not path:
            return
        try:
            dest = import_lut(Path(path))
        except OSError as e:
            QMessageBox.warning(self, "提示", f"导入失败：{e}")
            return
        self._refresh_luts(select=dest)
        self.log.appendPlainText(f"已导入 LUT：{dest.name}")
        self.statusBar().showMessage(f"已导入 LUT：{dest.name}", 4000)
        self._validate()

    def _refresh_encoder_hint(self):
        selected = self.encoder_combo.currentText()
        if selected == "自动检测":
            if self.detected_encoder:
                self.encoder_hint.setText(
                    f"将自动使用检测到的编码器：{self.detected_encoder}")
            else:
                self.encoder_hint.setText("正在检测可用编码器…")
        else:
            self.encoder_hint.setText(ENCODER_HINTS.get(selected, ""))

    # ---------- environment check ----------

    def _on_env_checked(self, ffmpeg, source, encoder):
        self.ffmpeg_ok = bool(ffmpeg)
        self.detected_encoder = encoder
        if ffmpeg:
            builtin = source in ("bundled", "bundled-asset")
            note = "（已内置，开箱即用）" if builtin else ""
            self.status_label.setText(f"ffmpeg{note}：{ffmpeg}")
            self.log.appendPlainText(
                f"已就绪：使用 ffmpeg（{source}）{note}，无需单独安装。")
        else:
            self.status_label.setText("未找到 ffmpeg，请先安装")
            self.statusBar().setStyleSheet(
                "QStatusBar QLabel { color: #E5484D; }")
            self.log.appendPlainText(
                "错误：未找到 ffmpeg。可运行 `pip install -r requirements.txt` "
                "或使用系统包管理器安装（如 `brew install ffmpeg`）。")
        self._refresh_encoder_hint()
        self._validate()

    # ---------- validation ----------

    def _set_state(self, widget, state):
        widget.setProperty("state", state or "")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_video_count(self, videos):
        if videos is None:
            self.video_count_label.setText("")
            self.video_count_label.setToolTip("")
            return
        if not videos:
            self.video_count_label.setText("该文件夹中没有找到视频文件")
            self.video_count_label.setToolTip("")
            return
        total = sum(f.stat().st_size for f in videos if f.is_file())
        mb = total / (1024 * 1024)
        self.video_count_label.setText(
            f"找到 {len(videos)} 个视频（合计 {mb:.1f} MB）")
        self.video_count_label.setToolTip(
            "\n".join(f.name for f in videos[:200]))

    def _validate(self):
        errors = []
        input_dir = Path(self.input_edit.text().strip())
        if not input_dir.is_dir():
            errors.append("输入文件夹不存在或不可访问")
            self._set_state(self.input_edit, "error")
            self._set_video_count(None)
        else:
            videos = get_video_files(input_dir)
            self._set_video_count(videos)
            if videos:
                self._set_state(self.input_edit, "ok")
            else:
                errors.append(f"输入文件夹中没有视频文件（{SUPPORTED_TEXT}）")
                self._set_state(self.input_edit, "error")

        output = Path(self.output_edit.text().strip())
        if output.exists() and not output.is_dir():
            errors.append("输出路径不是文件夹")
            self._set_state(self.output_edit, "error")
        else:
            self._set_state(self.output_edit, "ok")

        lut = self.lut_path()
        if lut is None or not lut.is_file():
            errors.append("所选 LUT 文件不存在")

        self._errors = errors
        if errors:
            self.error_label.setText("· " + "\n· ".join(errors))
            self.error_label.show()
        else:
            self.error_label.clear()
            self.error_label.hide()
        self._update_start_btn()
        return not errors

    def _update_start_btn(self):
        if self.running:
            self.start_btn.setEnabled(False)
            return
        self.start_btn.setEnabled(self.ffmpeg_ok and not self._errors)

    # ---------- drag & drop (whole window) ----------

    def dragEnterEvent(self, event):
        if self._accepted_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._accepted_drop(event):
            return
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile() or "")
            if p.is_dir():
                self.input_edit.setText(str(p))
            elif p.suffix.lower() == ".cube":
                try:
                    dest = import_lut(p)
                    self._refresh_luts(select=dest)
                    self.log.appendPlainText(f"已导入 LUT：{dest.name}")
                except OSError as e:
                    QMessageBox.warning(self, "提示", f"导入失败：{e}")
        event.acceptProposedAction()
        self._validate()

    def _accepted_drop(self, event):
        if not event.mimeData().hasUrls():
            return False
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile() or "")
            if p.is_dir() or p.suffix.lower() == ".cube":
                return True
        return False

    # ---------- conversion ----------

    def start_convert(self):
        if self.running:
            return
        if not self._validate():
            QMessageBox.warning(self, "无法开始", "\n".join(self._errors))
            return

        input_dir = Path(self.input_edit.text().strip())
        output_dir = Path(self.output_edit.text().strip())
        lut = self.lut_path()
        encoder = None if self.encoder_combo.currentText() == "自动检测" \
            else self.encoder_combo.currentText()
        self._save_settings()

        self.running = True
        self.log.clear()
        self.progress.setValue(0)
        self.progress.setFormat("准备中…")
        self.current_label.clear()
        self.start_btn.setText("转换中…")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("取消")

        self.worker = Worker(input_dir, output_dir, lut, encoder)
        self.worker.log_signal.connect(self.log.appendPlainText)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.file_signal.connect(self._on_file)
        self.worker.done_signal.connect(self._on_done)
        self.worker.start()

    def _cancel_convert(self):
        if self.worker:
            self.worker.stop()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("正在取消…")
            self.log.appendPlainText("正在取消，等待当前视频终止…")

    def _on_file(self, name, idx, total):
        self.progress.setFormat(f"{idx}/{total} {name} - %p%")
        self.current_label.setText(f"正在处理：{name}（{idx}/{total}）")
        self.log.appendPlainText(f"（{idx}/{total}）")

    def _on_done(self, succeeded, skipped, failed, cancelled):
        self.running = False
        self.start_btn.setText("开始转换")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("取消")
        self.progress.setFormat("")
        self.progress.setValue(100)
        self.current_label.clear()
        self.log.appendPlainText(
            f"\n处理结束：成功 {succeeded}，跳过 {skipped}，"
            f"失败 {failed}，取消 {cancelled}")
        self._update_start_btn()
        self._show_summary(succeeded, skipped, failed, cancelled)

    def _show_summary(self, succeeded, skipped, failed, cancelled):
        box = QMessageBox(self)
        box.setWindowTitle("转换已取消" if cancelled else "转换完成")
        box.setInformativeText(
            f"成功 {succeeded}，跳过 {skipped}，失败 {failed}，取消 {cancelled}")
        if failed or cancelled:
            box.setIcon(QMessageBox.Warning)
            box.setText("转换结束（存在未成功项）")
        else:
            box.setIcon(QMessageBox.Information)
            box.setText("全部转换完成")
        open_btn = box.addButton("打开输出文件夹", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Close)
        box.exec()
        if box.clickedButton() is open_btn:
            open_in_file_manager(Path(self.output_edit.text().strip()))

    def closeEvent(self, event):
        if self.running and self.worker:
            answer = QMessageBox.question(
                self, "确认退出",
                "转换仍在进行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.stop()
            self.worker.wait(3000)
        self._save_settings()
        event.accept()


def main():
    QApplication.setStyle("Fusion")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("DJI_LUT_Tools")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
