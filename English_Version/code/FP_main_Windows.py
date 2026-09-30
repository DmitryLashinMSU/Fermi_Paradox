import os
import sys
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QGroupBox, QTextEdit, QScrollArea, QSplitter)
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import multiprocessing
import queue

import io
import contextlib
import FP_logic


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    return os.path.join(base_path, relative_path)


def run_simulation_process(params, output_queue):
    try:
        FP_logic.set_params(params)

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            FP_logic.main()

        output = f.getvalue()
        output_queue.put(("output", output))

    except Exception as e:
        import traceback
        error_msg = f"Execution error: {str(e)}\n{traceback.format_exc()}"
        output_queue.put(("error", error_msg))


class SimulationWorker(QObject):
    finished = pyqtSignal()
    output_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.is_running = False
        self.process = None
        self.output_queue = multiprocessing.Queue()

    def run_simulation(self):
        self.is_running = True
        try:
            self.process = multiprocessing.Process(
                target=run_simulation_process,
                args=(self.params, self.output_queue),
                daemon=True
            )
            self.process.start()

            self.reader_thread = threading.Thread(target=self.read_output, daemon=True)
            self.reader_thread.start()

        except Exception as e:
            self.error_occurred.emit(f"Launch error: {str(e)}")
            self.is_running = False

    def read_output(self):
        while self.is_running:
            try:
                msg_type, content = self.output_queue.get(timeout=0.1)
                if msg_type == "output":
                    self.output_received.emit(content)
                elif msg_type == "error":
                    self.error_occurred.emit(content)
            except queue.Empty:
                if self.process and not self.process.is_alive():
                    break
                continue
            except Exception as e:
                self.error_occurred.emit(f"Output read error: {str(e)}")
                break

        self.is_running = False
        self.finished.emit()

    def stop(self):
        self.is_running = False
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=0.1)
            if self.process.is_alive():
                self.process.kill()


class ParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 1350, 700)
        self.simulation_worker = None
        self.has_error = False

        self.initUI()
        self.center()
        self.apply_styles()

    def center(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        if window_geometry.top() < screen_geometry.top():
            window_geometry.moveTop(screen_geometry.top())
        if window_geometry.left() < screen_geometry.left():
            window_geometry.moveLeft(screen_geometry.left())
        self.move(window_geometry.topLeft())

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3c3c;
                color: #fff;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4fc3f7;
                font-size: 13px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #424242;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: #fff;
                selection-background-color: #4fc3f7;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #4fc3f7;
            }
            QPushButton {
                background-color: #4fc3f7;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                color: #000;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #29b6f6;
            }
            QPushButton:pressed {
                background-color: #0288d1;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QTextEdit {
                background-color: #424242;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
                font-size: 13px;
                padding: 10px;
            }
        """)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Vertical)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)

        self.params = {}

        main_group = QGroupBox("Main simulation parameters")
        main_layout_group = QVBoxLayout()

        main_parameters = [
            ("N", "Number of habitable systems", "500"),
            ("R", "Galaxy radius (thousand light-years)", "300"),
            ("Disp", "Display size", "700"),
            ("A", "Evolution acceleration", "1000"),
            ("spaceships_speed", "Spaceship speed (fraction of the speed of light)", "0.5"),
            ("t_signal", "Signal generation time (thousand years)", "3"),
            ("t_stop", "Signal lifetime (thousand years)", "700"),
            ("FPS", "Maximum FPS", "100")
        ]

        for param_name, label_text, default_value in main_parameters:
            param_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(300)
            line_edit = QLineEdit(default_value)
            line_edit.setMaximumWidth(150)
            self.params[param_name] = line_edit
            param_layout.addWidget(label)
            param_layout.addStretch()
            param_layout.addWidget(line_edit)
            main_layout_group.addLayout(param_layout)

        main_group.setLayout(main_layout_group)
        scroll_layout.addWidget(main_group)

        time_group = QGroupBox("Time ranges (thousand years)")
        time_layout = QVBoxLayout()

        time_parameters = [
            ("t_range_min", "Minimum stellar lifetime", "6_000_000"),
            ("t_range_max", "Maximum stellar lifetime", "100_000_000"),
            ("t_0_range_min", "Minimum starting age of first stars", "0"),
            ("t_0_range_max", "Maximum starting age of first stars", "100_000_000"),
            ("t_intel_range_min", "Minimum civilization emergence time", "4_000_000"),
            ("t_intel_range_max", "Maximum civilization emergence time", "6_000_000")
        ]

        for param_name, label_text, default_value in time_parameters:
            param_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(300)
            line_edit = QLineEdit(default_value)
            line_edit.setMaximumWidth(150)
            self.params[param_name] = line_edit
            param_layout.addWidget(label)
            param_layout.addStretch()
            param_layout.addWidget(line_edit)
            time_layout.addLayout(param_layout)

        time_group.setLayout(time_layout)
        scroll_layout.addWidget(time_group)

        results_group = QGroupBox("Result extraction parameters (thousand years)")
        results_layout = QVBoxLayout()

        params_container = QWidget()
        params_layout = QVBoxLayout(params_container)
        params_layout.setSpacing(5)

        results_parameters = [
            ("start_record", "Data recording start time", "0"),
            ("stop_record", "Data recording stop time", "100_000"),
            ("step", "Calculation step", "1000")
        ]

        for param_name, label_text, default_value in results_parameters:
            param_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(300)
            line_edit = QLineEdit(default_value)
            line_edit.setMaximumWidth(150)
            self.params[param_name] = line_edit
            param_layout.addWidget(label)
            param_layout.addStretch()
            param_layout.addWidget(line_edit)
            params_layout.addLayout(param_layout)

        results_layout.addWidget(params_container)

        image_container = QWidget()
        image_layout = QHBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        image_label.setScaledContents(True)
        image_label.setFixedSize(250, 250)

        image_path = resource_path("planet.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(300, 200,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("Image not found")
            image_label.setStyleSheet("color: #ff5555;")

        image_layout.addWidget(image_label)
        results_layout.addWidget(image_container)

        results_group.setLayout(results_layout)
        scroll_layout.addWidget(results_group)

        scroll_area.setWidget(scroll_content)
        splitter.addWidget(scroll_area)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)

        results_label = QLabel("Simulation Results")
        results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4fc3f7; padding: 13px;")
        results_layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Simulation results will appear here upon completion...")
        self.results_text.setStyleSheet("font-size: 15px;")
        results_layout.addWidget(self.results_text)

        splitter.addWidget(results_widget)
        splitter.setSizes([800, 250])

        main_layout.addWidget(splitter)

        self.run_button = QPushButton("Run simulation")
        self.run_button.clicked.connect(self.run_simulation)
        main_layout.addWidget(self.run_button)

    def run_simulation(self):
        self.has_error = False
        self.results_text.clear()
        self.run_button.setEnabled(False)

        try:
            params = {key: widget.text() for key, widget in self.params.items()}
        except Exception:
            params = {}

        self.simulation_worker = SimulationWorker(params)
        self.simulation_worker.output_received.connect(self.handle_output)
        self.simulation_worker.error_occurred.connect(self.handle_error)
        self.simulation_worker.finished.connect(self.on_simulation_finished)

        threading.Thread(target=self.simulation_worker.run_simulation, daemon=True).start()

    def handle_output(self, output):
        self.results_text.append(output)

    def handle_error(self, err_text):
        self.has_error = True
        self.results_text.append(err_text)
        self.run_button.setEnabled(True)

    def on_simulation_finished(self):
        self.run_button.setEnabled(True)
        if not getattr(self, "has_error", False):
            self.parse_simulation_results(self.results_text.toPlainText())

    def parse_simulation_results(self, output):
        lines = output.split('\n')
        results_text = ""

        detection_found = False

        for line in lines:
            line = line.strip()
            if line.startswith("Detection of one civilization occurs once every"):
                results_text += line + "\n"
                detection_found = True
            elif line.startswith("Number of civilizations that appeared and disappeared during this time:"):
                results_text += line + "\n"
                detection_found = True
            elif line.startswith("Average fraction of detections per civilization:"):
                results_text += line
                detection_found = True

        if not detection_found:
            for line in lines:
                if "No detections occurred" in line:
                    results_text = line
                    break
            else:
                results_text = "Failed to extract simulation results"

        self.results_text.setPlainText(results_text)

    def closeEvent(self, event):
        try:
            if self.simulation_worker and getattr(self.simulation_worker, "is_running", False):
                self.simulation_worker.stop()
        except Exception:
            pass
        event.accept()


def main():
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark_palette)

    param_window = ParameterWindow()
    param_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
