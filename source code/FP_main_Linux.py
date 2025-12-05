import os
import sys
import subprocess
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QGroupBox, QTextEdit, QScrollArea, QSplitter)
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np


class SimulationWorker(QObject):
    finished = pyqtSignal()
    output_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, script_content):
        super().__init__()
        self.script_content = script_content
        self.is_running = False

    def run_simulation(self):
        self.is_running = True

        with open("temp_simulation.py", "w", encoding="utf-8") as f:
            f.write(self.script_content)

        self.output_received.emit("Симуляция запущена...")

        process = subprocess.Popen([sys.executable, "temp_simulation.py"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   bufsize=1,
                                   universal_newlines=True)

        while self.is_running:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.output_received.emit(output.strip())

        stdout, stderr = process.communicate()

        if process.returncode == 0:
            self.output_received.emit("Симуляция завершена успешно!")
            self.output_received.emit(stdout)
        else:
            self.error_occurred.emit(f"Ошибка при выполнении симуляции:\n{stderr}")

        self.is_running = False
        self.finished.emit()

    def stop(self):
        self.is_running = False


class ParameterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.setGeometry(100, 100, 1400, 800)
        self.simulation_thread = None
        self.simulation_worker = None
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

        results_group = QGroupBox("Параметры извлечения результатов")
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

        image_path = "planet.png"
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

        params = {key: widget.text() for key, widget in self.params.items()}
        script_content = self.generate_script(params)

        self.simulation_worker = SimulationWorker(script_content)
        self.simulation_thread = threading.Thread(target=self.simulation_worker.run_simulation)

        self.simulation_worker.output_received.connect(self.handle_output)
        self.simulation_worker.finished.connect(self.on_simulation_finished)

        self.simulation_thread.start()

    def handle_output(self, output):
        current_text = self.results_text.toPlainText()
        if current_text and current_text != 'Симуляция запущена...':
            new_text = current_text + "\n" + output
        else:
            new_text = output
        self.results_text.setPlainText(new_text)

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
        with open("FP_logic.py", "r", encoding="utf-8") as f:
            original_script = f.read()

        replacements = {
            "N = 500": f"N = {int(params['N'])}",
            "R = 400": f"R = {int(params['R'])}",
            "Disp = 900": f"Disp = {int(params['Disp'])}",
            "A = 1000": f"A = {int(params['A'])}",
            "spaceships_speed = 0.5": f"spaceships_speed = {float(params['spaceships_speed'])}",
            "t_signal = 3": f"t_signal = {int(params['t_signal'])}",
            "t_stop = 1000": f"t_stop = {int(params['t_stop'])}",
            "clock.tick(100)": f"clock.tick({int(params['FPS'])})",
            "t_range = [int(6000000 / A), int(100000000 / A)]":
                f"t_range = [int({int(params['t_range_min'])} / A), int({int(params['t_range_max'])} / A)]",
            "t_0_range = [int(0 / A), int(100000000 / A)]":
                f"t_0_range = [int({int(params['t_0_range_min'])} / A), int({int(params['t_0_range_max'])} / A)]",
            "t_intel_range = [int(4000000 / A), int(6000000 / A)]":
                f"t_intel_range = [int({int(params['t_intel_range_min'])} / A), int({int(params['t_intel_range_max'])} / A)]",
            "start_record = 0": f"start_record = {int(params['start_record'])}",
            "stop_record = 100000": f"stop_record = {int(params['stop_record'])}",
            "step = 1000": f"step = {int(params['step'])}"
        }

        for old, new in replacements.items():
            original_script = original_script.replace(old, new)

        return original_script

    def closeEvent(self, event):
        if self.simulation_worker and self.simulation_worker.is_running:
            self.simulation_worker.stop()
            if self.simulation_thread and self.simulation_thread.is_alive():
                self.simulation_thread.join(timeout=0.0)
        os._exit(0)


class ResultsWindow(QMainWindow):
    def __init__(self, times, civ_number, detected_number):
        super().__init__()
        self.times = times
        self.civ_number = civ_number
        self.detected_number = detected_number
        self.setWindowTitle("Результаты симуляции")
        self.setGeometry(100, 100, 900, 1000)
        self.initUI()
        self.center()
        self.apply_styles()
        self.calculate_results()

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
            QTextEdit {
                background-color: #424242;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
                font-size: 15px;
                padding: 10px;
            }
            QPushButton {
                background-color: #4fc3f7;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                color: #000;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #29b6f6;
            }
            QPushButton:pressed {
                background-color: #0288d1;
            }
        """)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.figure, self.axes = plt.subplots(3, 1, figsize=(10, 14))
        self.figure.patch.set_facecolor('#2b2b2b')
        for ax in self.axes:
            ax.set_facecolor('#3c3c3c')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
            ax.title.set_fontsize(14)
            ax.xaxis.label.set_fontsize(12)
            ax.yaxis.label.set_fontsize(12)
            for spine in ax.spines.values():
                spine.set_color('white')

        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        self.results_text.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.results_text)

        close_button = QPushButton("Закрыть результаты")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def calculate_results(self):
        X_civ = self.times.reshape(-1, 1)

        k_civ = np.linalg.lstsq(X_civ, self.civ_number, rcond=None)[0][0]
        k_detected = np.linalg.lstsq(X_civ, self.detected_number, rcond=None)[0][0]

        if k_detected * k_civ != 0:
            result_text = f"""Обнаружение одной цивилизации происходит раз в {1 / k_detected:.4f} тыс. лет

Число цивилизаций, появившихся и исчезнувших за это время: {k_civ / k_detected:.4f}

Средняя доля обнаружений на одну цивилизацию: {min(float(k_detected / k_civ), 1):.4f}"""
        else:
            result_text = "За рассматриваемый диапазон времени симуляции обнаружений не произошло"

        self.results_text.setText(result_text)
        self.plot_results()

    def plot_results(self):
        for ax in self.axes:
            ax.clear()

        X_civ = self.times.reshape(-1, 1)
        k_civ = np.linalg.lstsq(X_civ, self.civ_number, rcond=None)[0][0]
        k_detected = np.linalg.lstsq(X_civ, self.detected_number, rcond=None)[0][0]

        data_color = '#bb86fc'
        fit_color = '#03dac6'
        background_color = '#3c3c3c'
        text_color = 'white'

        for ax in self.axes:
            ax.set_facecolor(background_color)
            ax.tick_params(colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)
            ax.title.set_fontsize(14)
            ax.xaxis.label.set_fontsize(12)
            ax.yaxis.label.set_fontsize(12)
            for spine in ax.spines.values():
                spine.set_color(text_color)

        self.axes[0].plot(self.times, self.civ_number, 'o', color=data_color, markersize=3, label='Данные')
        self.axes[0].plot(self.times, k_civ * self.times, '-', color=fit_color, linewidth=2, label='Аппроксимация')
        self.axes[0].set_xlabel("время, тыс. лет", fontsize=12)
        self.axes[0].set_ylabel("число сигналов", fontsize=12)
        self.axes[0].set_title("Рост числа сигналов со временем", fontsize=13)
        self.axes[0].legend(loc='best', fontsize=11)

        self.axes[1].plot(self.times, self.detected_number, 'o', color=data_color, markersize=3, label='Данные')
        self.axes[1].plot(self.times, k_detected * self.times, '-', color=fit_color, linewidth=2, label='Аппроксимация')
        self.axes[1].set_xlabel("время, тыс. лет", fontsize=12)
        self.axes[1].set_ylabel("число обнаружений", fontsize=12)
        self.axes[1].set_title("Динамика обнаружений", fontsize=13)
        self.axes[1].legend(loc='best', fontsize=11)

        self.figure.tight_layout()
        self.canvas.draw()


def main():
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

    if len(sys.argv) > 1 and sys.argv[1] == "--results":
        data = np.load("simulation_results.npz")
        results_window = ResultsWindow(data['times'], data['civ_number'], data['detected_number'])
        results_window.show()
    else:
        param_window = ParameterWindow()
        param_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
