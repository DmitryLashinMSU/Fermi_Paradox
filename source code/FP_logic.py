#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import random
import math
import numpy as np
import matplotlib.pyplot as plt
from numba import njit

N = 500
R = 400
Disp = 900
A = 1000
t_range = [int(6000000 / A), int(100000000 / A)]
t_0_range = [int(0 / A), int(100000000 / A)]
t_intel_range = [int(4000000 / A), int(6000000 / A)]
t_signal = 3
t_stop = 1000
spaceships_speed = 0.5

start_record = 0
stop_record = 100000
step = 1000
arrays_size = int(stop_record / step + 1)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)


@njit(fastmath=True)
def generate_random_point_in_circle(radius):
    while True:
        x = random.uniform(Disp / 2 - R - radius, Disp / 2 - R + radius)
        y = random.uniform(Disp / 2 - R - radius, Disp / 2 - R + radius)
        if math.sqrt((Disp / 2 - R - x) ** 2 + (Disp / 2 - R - y) ** 2) <= radius:
            return x, y


@njit(fastmath=True)
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


@njit(fastmath=True)
def normalize_vector(x, y, distance):
    if distance > 0:
        return x / distance, y / distance
    return 0.0, 0.0


class Spaceship:
    def __init__(self, start_x, start_y, target_x, target_y, speed=spaceships_speed):
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = speed
        self.active = True
        self.distance = calculate_distance(start_x, start_y, target_x, target_y)
        self.traveled = 0
        self.direction_x, self.direction_y = normalize_vector(target_x - start_x, target_y - start_y, self.distance)
        self.animation_frame = 0
        self.animation_speed = 5
        self.animation_counter = 0
        self.glider_patterns = [
            [(-1, 0), (0, -1), (0, -2), (-1, -2), (-2, -2)],
            [(-2, 0), (0, 0), (0, -1), (-1, -1), (-1, -2)],
            [(-2, -1), (-1, -2), (0, 0), (0, -1), (0, -2)],
            [(-2, 0), (-2, -2), (-1, -2), (-1, -1), (0, -1)]
        ]

    def update(self):
        if self.active:
            self.x += self.direction_x * self.speed
            self.y += self.direction_y * self.speed
            self.traveled += self.speed
            self.animation_counter += 1
            if self.animation_counter >= self.animation_speed:
                self.animation_counter = 0
                self.animation_frame = (self.animation_frame + 1) % 4
            current_distance = calculate_distance(self.x, self.y, self.target_x, self.target_y)
            if current_distance <= self.speed:
                self.active = False
                return True
        return False

    def draw(self, screen):
        if self.active:
            angle = math.atan2(self.direction_y, self.direction_x)
            pattern = self.glider_patterns[self.animation_frame]
            for dx, dy in pattern:
                rotated_x = dx * math.cos(angle) - dy * math.sin(angle)
                rotated_y = dx * math.sin(angle) + dy * math.cos(angle)
                cell_size = 2
                pygame.draw.rect(screen, YELLOW,
                                 (int(self.x + R + rotated_x * cell_size - cell_size / 2),
                                  int(self.y + R + rotated_y * cell_size - cell_size / 2),
                                  cell_size, cell_size))


class Civilization:
    def __init__(self, x, y, t_0, time):
        self.x = x
        self.y = y
        self.t_0 = t_0
        self.t_intel = random.randint(*t_intel_range)
        self.t_start = time
        self.t_end = random.randint(*t_range)
        self.t = t_0
        self.signal_radius = 0
        self.signal_active = False
        self.signals_emitted = 0
        self.detected_civs = []
        self.was_detected = False
        self.detected_others = False
        self.spaceships = []

    def update(self, time):
        self.t = self.t_0 + time - self.t_start
        if self.t > self.t_intel and not self.signal_active:
            self.signal_active = True
        if self.signal_active:
            self.signal_radius += 1
            if self.signal_radius > t_stop:
                self.signal_active = False
        for spaceship in self.spaceships[:]:
            if spaceship.update():
                self.spaceships.remove(spaceship)
                return spaceship
        return None

    def send_spaceship(self, target_civ):
        spaceship = Spaceship(self.x, self.y, target_civ.x, target_civ.y)
        self.spaceships.append(spaceship)
        return spaceship

    def draw(self, screen):
        point_color = GREEN if self.was_detected else WHITE
        pygame.draw.circle(screen, point_color, (int(self.x + R), int(self.y + R)), 2)
        if self.detected_others:
            pygame.draw.circle(screen, BLUE, (int(self.x + R), int(self.y + R)), 4, 2)
        if self.signal_active and self.t_intel > self.t_0:
            pygame.draw.circle(screen, RED, (int(self.x + R), int(self.y + R)), self.signal_radius, t_signal)
        for spaceship in self.spaceships:
            spaceship.draw(screen)


@njit(fastmath=True)
def check_detection_conditions(distance, outer_edge, inner_edge, signal_active):
    return distance <= outer_edge and distance >= inner_edge and signal_active


def process_detections(civilizations):
    global find_count
    n = len(civilizations)
    for i in range(n):
        civ1 = civilizations[i]
        for j in range(i + 1, n):
            civ2 = civilizations[j]
            if (civ2 not in getattr(civ1, 'detected_civs', [])) and (civ1 not in getattr(civ2, 'detected_civs', [])):
                if (civ1.signal_active and civ2.signal_active and civ1.t_intel > civ1.t_0 and civ2.t_intel > civ2.t_0):
                    distance = calculate_distance(civ1.x, civ1.y, civ2.x, civ2.y)
                    outer_edge_1 = civ1.signal_radius
                    inner_edge_1 = max(0, civ1.signal_radius - t_signal)
                    outer_edge_2 = civ2.signal_radius
                    inner_edge_2 = max(0, civ2.signal_radius - t_signal)
                    detection_1 = check_detection_conditions(distance, outer_edge_2, inner_edge_2,
                                                             civ1.signal_radius <= t_signal)
                    detection_2 = check_detection_conditions(distance, outer_edge_1, inner_edge_1,
                                                             civ2.signal_radius <= t_signal)
                    if detection_1:
                        find_count += 1
                        civ1.detected_civs.append(civ2)
                        civ1.detected_others = True
                        civ2.was_detected = True
                        civ1.send_spaceship(civ2)
                    if detection_2:
                        find_count += 1
                        civ2.detected_civs.append(civ1)
                        civ2.detected_others = True
                        civ1.was_detected = True
                        civ2.send_spaceship(civ1)

def main():
    global find_count, signals_emitted_count, contact_count, visit_count
    global times, civ_number, detected_number, next_step, array_count

    find_count = 0
    signals_emitted_count = 0
    contact_count = 0
    visit_count = 0

    times = np.zeros(arrays_size)
    civ_number = np.zeros(arrays_size)
    detected_number = np.zeros(arrays_size)
    next_step = start_record
    array_count = 0

    pygame.init()
    screen = pygame.display.set_mode((Disp, Disp))
    pygame.display.set_caption("Симуляция парадокса Ферми")
    clock = pygame.time.Clock()

    civilizations = []
    for _ in range(10 * N):
        x, y = generate_random_point_in_circle(R)
        civilizations.append(Civilization(x, y, random.randint(*t_0_range), 0))

    running = True
    time = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        civilizations = [civ for civ in civilizations if civ.t < civ.t_end]
        if time == 0:
            civilizations = civilizations[:N]

        if time == next_step and time <= stop_record:
            times[array_count] = time
            civ_number[array_count] = signals_emitted_count
            detected_number[array_count] = find_count
            array_count += 1
            next_step += step

        if len(civilizations) < N:
            while len(civilizations) - N < 0:
                x, y = generate_random_point_in_circle(R)
                civilizations.append(Civilization(x, y, 0, time))

        arrived_spaceships = []
        for civilization in civilizations:
            arrived_ship = civilization.update(time)
            if arrived_ship:
                arrived_spaceships.append((civilization, arrived_ship))

        for civ, spaceship in arrived_spaceships:
            for target_civ in civilizations:
                if (abs(target_civ.x - spaceship.target_x) < 1 and abs(target_civ.y - spaceship.target_y) < 1):
                    if target_civ.signal_radius <= t_signal and target_civ.t_intel > target_civ.t_0:
                        contact_count += 1
                        visit_count += 1
                    else:
                        visit_count += 1
                    break

        for k in range(len(civilizations)):
            civ3 = civilizations[k]
            if civ3.signal_active and civ3.signal_radius == 1 and civ3.t_intel > civ3.t_0:
                signals_emitted_count += 1

        process_detections(civilizations)

        screen.fill(BLACK)
        for civilization in civilizations:
            civilization.draw(screen)

        font = pygame.font.Font(None, 36)
        text = font.render(f"Обнаружения: {find_count}", True, WHITE)
        screen.blit(text, (10, 60))
        text = font.render(f"Сигналы: {signals_emitted_count}", True, WHITE)
        screen.blit(text, (10, 110))
        text = font.render(f"Контакты: {contact_count}", True, WHITE)
        screen.blit(text, (10, Disp - 40))
        text = font.render(f"Визиты: {visit_count}", True, WHITE)
        screen.blit(text, (10, Disp - 90))
        text = font.render(f"Время: {time} тыс. лет", True, WHITE)
        screen.blit(text, (10, 10))

        font2 = pygame.font.Font(None, 30)
        if time < stop_record:
            progress_percent = int((time / stop_record) * 100)
            record_text = f"идет запись данных: {progress_percent}%"
        else:
            record_text = "данные симуляции записаны"
        text = font2.render(record_text, True, GRAY)
        text_rect = text.get_rect(center=(screen.get_width() // 2, Disp - 25))
        screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(100)
        time += 1


    pygame.display.quit()
    pygame.quit()

    X_civ = times.reshape(-1, 1)
    k_civ = np.linalg.lstsq(X_civ, civ_number, rcond=None)[0][0]
    k_detected = np.linalg.lstsq(X_civ, detected_number, rcond=None)[0][0]

    if k_detected * k_civ != 0:
        print(f"Обнаружение одной цивилизации происходит раз в {1 / k_detected:.4f} тыс. лет")
        print(f"Число цивилизаций, появившихся и исчезнувших за это время: {k_civ / k_detected:.4f}")
        print(f"Средняя доля обнаружений на одну цивилизацию: {float(k_detected / k_civ):.4f}")
    else:
        print("За рассматриваемый диапазон времени симуляции обнаружений не произошло")

    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title("Отображение полученных данных")

    axes[0].plot(times, civ_number, 'o', color='gray', markersize=3, label='Данные')
    axes[0].plot(times, k_civ * times, '-', color='C0', linewidth=2, label='Аппроксимация')
    axes[0].set_xlabel("время, тыс. лет", fontsize=10)
    axes[0].set_ylabel("число сигналов", fontsize=10)
    axes[0].set_title("Рост числа сигналов со временем", fontsize=15)
    axes[0].legend(loc='best', fontsize=9)

    axes[1].plot(times, detected_number, 'o', color='gray', markersize=3, label='Данные')
    axes[1].plot(times, k_detected * times, '-', color='g', linewidth=2, label='Аппроксимация')
    axes[1].set_xlabel("время, тыс. лет", fontsize=10)
    axes[1].set_ylabel("число обнаружений", fontsize=10)
    axes[1].set_title("Динамика обнаружений", fontsize=15)
    axes[1].legend(loc='best', fontsize=9)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
