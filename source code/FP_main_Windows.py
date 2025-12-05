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


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    return os.path.join(base_path, relative_path)


def run_simulation_process(script_content, output_queue):
    try:
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        script_path = os.path.join(script_dir, "FP_logic_temp.py")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        sys.path.insert(0, script_dir)

        import FP_logic_temp

        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            FP_logic_temp.main()

        output = f.getvalue()
        output_queue.put(("output", output))

        try:
            os.remove(script_path)
            os.remove(os.path.join(script_dir, "__pycache__", "FP_logic_temp.cpython-310.pyc"))
        except:
            pass

    except Exception as e:
        import traceback
        error_msg = f"Ошибка выполнения: {str(e)}\n{traceback.format_exc()}"
        output_queue.put(("error", error_msg))


class SimulationWorker(QObject):
    finished = pyqtSignal()
    output_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, script_path, modified_content, original_content):
        super().__init__()
        self.modified_content = modified_content
        self.is_running = False
        self.process = None
        self.output_queue = multiprocessing.Queue()

    def run_simulation(self):
        self.is_running = True
        try:
            self.process = multiprocessing.Process(
                target=run_simulation_process,
                args=(self.modified_content, self.output_queue),
                daemon=True
            )
            self.process.start()

            self.reader_thread = threading.Thread(target=self.read_output, daemon=True)
            self.reader_thread.start()

        except Exception as e:
            self.error_occurred.emit(f"Ошибка запуска: {str(e)}")
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
                self.error_occurred.emit(f"Ошибка чтения вывода: {str(e)}")
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
        self.setWindowTitle("Настройки")
        self.setGeometry(100, 100, 1400, 800)
        self.simulation_worker = None

        self.script_path = "FP_logic.py"
        script_path = resource_path("FP_logic.py")
        with open(script_path, "r", encoding="utf-8") as f:
            self.original_script = f.read()

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

        main_group = QGroupBox("Основные параметры симуляции")
        main_layout_group = QVBoxLayout()

        main_parameters = [
            ("N", "Количество благоприятных систем", "500"),
            ("R", "Радиус галактики (тыс. св. лет)", "400"),
            ("Disp", "Размер дисплея", "900"),
            ("A", "Ускорение эволюции", "1000"),
            ("spaceships_speed", "Скорость кораблей в долях от скорости света", "0.5"),
            ("t_signal", "Время генерации сигнала (тыс. лет)", "3"),
            ("t_stop", "Время существования сигнала (тыс. лет)", "1000"),
            ("FPS", "Максимальная величина FPS", "100")
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

        time_group = QGroupBox("Временные диапазоны (тыс. лет)")
        time_layout = QVBoxLayout()

        time_parameters = [
            ("t_range_min", "Минимальное время существования звезд", "6000000"),
            ("t_range_max", "Максимальное время существования звезд", "100000000"),
            ("t_0_range_min", "Минимальный стартовый возраст первых звезд", "0"),
            ("t_0_range_max", "Максимальный стартовый возраст первых звезд", "100000000"),
            ("t_intel_range_min", "Минимальное время появления цивилизации", "4000000"),
            ("t_intel_range_max", "Максимальное время появления цивилизации", "6000000")
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

        results_group = QGroupBox("Параметры извлечения результатов (тыс. лет)")
        results_layout = QVBoxLayout()

        params_container = QWidget()
        params_layout = QVBoxLayout(params_container)
        params_layout.setSpacing(5)

        results_parameters = [
            ("start_record", "Время начала записи данных", "0"),
            ("stop_record", "Время остановки записи данных", "100000"),
            ("step", "Шаг подсчетов", "1000")
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
            image_label.setText("Изображение не найдено")
            image_label.setStyleSheet("color: #ff5555;")

        image_layout.addWidget(image_label)
        results_layout.addWidget(image_container)

        results_group.setLayout(results_layout)
        scroll_layout.addWidget(results_group)

        scroll_area.setWidget(scroll_content)
        splitter.addWidget(scroll_area)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)

        results_label = QLabel("Итоги симуляции")
        results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4fc3f7; padding: 13px;")
        results_layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Результаты симуляции появятся здесь после завершения...")
        self.results_text.setStyleSheet("font-size: 15px;")
        results_layout.addWidget(self.results_text)

        splitter.addWidget(results_widget)
        splitter.setSizes([800, 250])

        main_layout.addWidget(splitter)

        self.run_button = QPushButton("Запустить симуляцию")
        self.run_button.clicked.connect(self.run_simulation)
        main_layout.addWidget(self.run_button)

    def run_simulation(self):
        self.results_text.clear()
        self.run_button.setEnabled(False)

        try:
            params = {key: widget.text() for key, widget in self.params.items()}
        except Exception:
            params = {}

        modified_content = self.generate_script(params)
        self.simulation_worker = SimulationWorker(self.script_path, modified_content, self.original_script)
        self.simulation_worker.output_received.connect(self.handle_output)
        self.simulation_worker.error_occurred.connect(self.handle_error)
        self.simulation_worker.finished.connect(self.on_simulation_finished)

        threading.Thread(target=self.simulation_worker.run_simulation, daemon=True).start()

    def handle_output(self, output):
        self.results_text.append(output)

    def handle_error(self, err_text):
        self.results_text.append(err_text)
        self.run_button.setEnabled(True)

    def on_simulation_finished(self):
        self.run_button.setEnabled(True)
        self.parse_simulation_results(self.results_text.toPlainText())

    def parse_simulation_results(self, output):
        lines = output.split('\n')
        results_text = ""

        detection_found = False

        for line in lines:
            line = line.strip()
            if line.startswith("Обнаружение одной цивилизации происходит раз в"):
                results_text += line + "\n"
                detection_found = True
            elif line.startswith("Число цивилизаций, появившихся и исчезнувших за это время:"):
                results_text += line + "\n"
                detection_found = True
            elif line.startswith("Средняя доля обнаружений на одну цивилизацию:"):
                results_text += line
                detection_found = True

        if not detection_found:
            for line in lines:
                if "обнаружений не произошло" in line:
                    results_text = line
                    break
            else:
                results_text = "Не удалось извлечь результаты симуляции"

        self.results_text.setPlainText(results_text)

    def generate_script(self, params):
        script_content = self.original_script
        try:
            replacements = {
                "N = 500": f"N = {int(params.get('N', 500))}",
                "R = 400": f"R = {int(params.get('R', 400))}",
                "Disp = 900": f"Disp = {int(params.get('Disp', 900))}",
                "A = 1000": f"A = {int(params.get('A', 1000))}",
                "spaceships_speed = 0.5": f"spaceships_speed = {float(params.get('spaceships_speed', 0.5))}",
                "t_signal = 3": f"t_signal = {int(params.get('t_signal', 3))}",
                "t_stop = 1000": f"t_stop = {int(params.get('t_stop', 1000))}",
                "clock.tick(100)": f"clock.tick({int(params.get('FPS', 100))})",
                "t_range = [int(6000000 / A), int(100000000 / A)]":
                    f"t_range = [int({int(params.get('t_range_min', 1000000))} / A), int({int(params.get('t_range_max', 100000000))} / A)]",
                "t_0_range = [int(0 / A), int(100000000 / A)]":
                    f"t_0_range = [int({int(params.get('t_0_range_min', 0))} / A), int({int(params.get('t_0_range_max', 100000000))} / A)]",
                "t_intel_range = [int(4000000 / A), int(6000000 / A)]":
                    f"t_intel_range = [int({int(params.get('t_intel_range_min', 4000000))} / A), int({int(params.get('t_intel_range_max', 6000000))} / A)]",
                "start_record = 0": f"start_record = {int(params.get('start_record', 0))}",
                "stop_record = 100000": f"stop_record = {int(params.get('stop_record', 100000))}",
                "step = 1000": f"step = {int(params.get('step', 1000))}"
            }
            for old, new in replacements.items():
                script_content = script_content.replace(old, new)
        except Exception:
            script_content = self.original_script
        return script_content

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
