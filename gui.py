#!/usr/bin/env python3
"""DJI LUT 批量转换工具 - PySide6 GUI."""

import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
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

ENCODER_CHOICES = [
    "自动检测",
    "libx264",
    "h264_videotoolbox",
    "h264_nvenc",
    "h264_amf",
    "h264_vaapi",
]


class Worker(QThread):
    log_signal = Signal(str)
    file_signal = Signal(str, int, int)
    progress_signal = Signal(int)
    done_signal = Signal(int, int)

    def __init__(self, input_dir, output_dir, lut, encoder, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.lut = lut
        self.encoder = encoder

    def run(self):
        ffmpeg, source = find_ffmpeg()
        if not ffmpeg:
            self.log_signal.emit("错误：找不到 ffmpeg，请检查安装。")
            self.done_signal.emit(0, 1)
            return
        self.log_signal.emit(f"使用 ffmpeg ({source}): {ffmpeg}")
        encoder = self.encoder if self.encoder else pick_encoder(ffmpeg)
        self.log_signal.emit(f"视频编码器: {encoder}")

        videos = get_video_files(self.input_dir)
        if not videos:
            self.log_signal.emit(f"错误：{self.input_dir} 中没有找到视频文件。")
            self.done_signal.emit(0, 1)
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_signal.emit(
            f"找到 {len(videos)} 个视频，LUT: {self.lut.name}\n")

        succeeded = failed = 0
        for idx, video in enumerate(videos, start=1):
            self.file_signal.emit(video.name, idx, len(videos))
            self.progress_signal.emit(0)
            self.log_signal.emit(f"[转换] {video.name} ({encoder})")

            def on_progress(duration, processed):
                if duration and processed is not None:
                    pct = min(100, int(processed / duration * 100))
                    self.progress_signal.emit(pct)

            ok = convert(video, self.output_dir, ffmpeg, encoder,
                         self.lut, on_progress=on_progress)
            if ok == "ok":
                succeeded += 1
                self.log_signal.emit(f"[完成] {video.name}\n")
            elif ok == "skipped":
                self.log_signal.emit(f"[跳过] {video.name}（输出已存在）\n")
            else:
                failed += 1
                self.log_signal.emit(f"[失败] {video.name}\n")

        self.done_signal.emit(succeeded, failed)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DJI LUT 批量转换工具")
        self.resize(720, 520)
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        form = QFormLayout()
        home = app_home()
        self.input_edit = self._path_field(form, "输入文件夹",
                                           str(home / "input"),
                                           is_dir=True)
        self.output_edit = self._path_field(form, "输出文件夹",
                                            str(home / "output"),
                                            is_dir=True)
        self.lut_combo = QComboBox()
        self._refresh_luts()
        import_btn = QPushButton("导入 LUT…")
        import_btn.clicked.connect(self._import_lut)
        lut_row = QHBoxLayout()
        lut_row.addWidget(self.lut_combo, stretch=1)
        lut_row.addWidget(import_btn)
        form.addRow("LUT 文件", lut_row)
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems(ENCODER_CHOICES)
        form.addRow("视频编码器", self.encoder_combo)
        layout.addLayout(form)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        layout.addWidget(self.log, stretch=1)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("开始转换")
        self.start_btn.clicked.connect(self.start_convert)
        btn_row.addStretch()
        btn_row.addWidget(self.start_btn)
        layout.addLayout(btn_row)

    def _path_field(self, form, label, default, is_dir):
        edit = QLineEdit(default)
        button = QPushButton("浏览…")
        button.clicked.connect(
            lambda: self._browse(edit, is_dir))
        row = QHBoxLayout()
        row.addWidget(edit, stretch=1)
        row.addWidget(button)
        form.addRow(label, row)
        return edit

    def _browse(self, edit, is_dir):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, "选择文件夹", edit.text())
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择 LUT 文件", edit.text(), "LUT 文件 (*.cube);;所有文件 (*)")
        if path:
            edit.setText(path)

    def _refresh_luts(self, select=None):
        self.lut_combo.clear()
        for lut in available_luts():
            label = f"内置: {lut.name}" if lut == DEFAULT_LUT else lut.name
            self.lut_combo.addItem(label, str(lut))
        if select:
            idx = self.lut_combo.findData(str(select))
            if idx >= 0:
                self.lut_combo.setCurrentIndex(idx)

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

    def start_convert(self):
        if self.worker and self.worker.isRunning():
            return
        input_dir = Path(self.input_edit.text())
        output_dir = Path(self.output_edit.text())
        if not input_dir.is_dir():
            QMessageBox.warning(self, "提示", "输入文件夹不存在")
            return
        lut = Path(self.lut_combo.currentData())
        if not lut.is_file():
            QMessageBox.warning(self, "提示", "LUT 文件不存在")
            return

        selected = self.encoder_combo.currentText()
        encoder = None if selected == "自动检测" else selected

        self.log.clear()
        self.progress.setValue(0)
        self.start_btn.setEnabled(False)
        self.worker = Worker(input_dir, output_dir, lut, encoder)
        self.worker.log_signal.connect(self.log.appendPlainText)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.file_signal.connect(self._on_file)
        self.worker.done_signal.connect(self._on_done)
        self.worker.start()

    def _on_file(self, name, idx, total):
        self.progress.setFormat(f"{idx}/{total} {name} - %p%")
        self.log.appendPlainText(f"({idx}/{total})")

    def _on_done(self, succeeded, failed):
        self.start_btn.setEnabled(True)
        self.progress.setFormat("")
        self.progress.setValue(100)
        self.log.appendPlainText(f"\n全部完成：成功 {succeeded}，失败 {failed}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
