import pygame
import json
import os
import math

# CONFIG MANAGER (создаёт config.json автоматически)

DEFAULT_CONFIG = {
    "window": {
        "width": 2000,
        "height": 950
    },

    "colors": {
        "background": [10, 10, 10],          # глубокий чёрный
        "epicycle": [120, 120, 255],         # мягкий голубой для окружностей
        "wave": [255, 80, 80],               # яркая красная/розовая волна
        "line": [180, 180, 180],             # серые линии-связки
        "text": [230, 230, 230]              # беловатый текст
    },

    "animation": {
        "fps": 60,
        "time_speed": 1.0,
        "time_step": 0.0035
    },

    "layout": {
        "epicycle_center": [350, 600],
        "wave_origin_x": 750
    },

    "fourier": {
        "initial_terms": 5,
        "max_terms": 60,
        "function": "square",

        "scale": 150.0,                      # уменьшили окружность, но оставили выразительной
        "wave_speed": 1.6,

        # плавное вращение
        "rotation_speed": 0.22
    }
}


def load_or_create_config(path="config.json"):
    """Создаёт config.json, если его нет, и загружает настройки."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print("Создан новый config.json")

    with open(path, "r") as f:
        return json.load(f)


# FOURIER SERIES
class FourierSeries:
    def __init__(self, series_type="square"):
        self.series_type = series_type

    def toggle(self):
        if self.series_type == "square":
            self.series_type = "sawtooth"
        else:
            self.series_type = "square"

    def name(self):
        return "Square wave" if self.series_type == "square" else "Sawtooth wave"

    def get_term(self, term_index):
        """Возвращает (radius, freq, direction) для term_index."""
        if self.series_type == "square":
            # прямоугольник: нечётные гармоники 1,3,5,...
            n = 2 * term_index + 1
            radius = 4.0 / (math.pi * n)
            freq = n
            direction = 1
        else:  # sawtooth
            n = term_index + 1
            radius = 2.0 / (math.pi * n)
            freq = n
            direction = 1 if n % 2 else -1

        return radius, freq, direction


# WAVE TRACER
class WaveTracer:
    """Хранит и рисует точки волны справа."""

    def __init__(self, origin_x, max_width, color, speed):
        self.origin_x = origin_x
        self.max_width = max_width
        self.color = color
        self.speed = speed
        self.points = []

    def reset(self):
        self.points.clear()

    def add(self, y):
        self.points.insert(0, [self.origin_x, y])

    def update(self):
        for p in self.points:
            p[0] += self.speed
        self.points = [p for p in self.points if p[0] < self.max_width]

    def draw(self, surface):
        if len(self.points) > 1:
            pygame.draw.lines(surface, self.color, False, self.points, 2)


# SIMULATION CORE

class Simulation:
    def __init__(self, config):

        self.config = config
        anim = config["animation"]
        fw = config["fourier"]
        lay = config["layout"]

        self.time = 0.0
        self.paused = False

        self.time_speed = anim["time_speed"]
        self.time_step = anim["time_step"]

        self.num_terms = fw["initial_terms"]
        self.max_terms = fw["max_terms"]
        self.scale = fw["scale"]

        # скорость вращения эпицирклов
        self.rotation_speed = fw["rotation_speed"]

        self.center_x, self.center_y = lay["epicycle_center"]
        self.wave_origin_x = lay["wave_origin_x"]

        self.colors = config["colors"]

        win_w = config["window"]["width"]

        self.fourier = FourierSeries(fw["function"])

        self.wave = WaveTracer(
            origin_x=self.wave_origin_x,
            max_width=win_w,
            color=self.colors["wave"],
            speed=fw["wave_speed"]
        )

        self.epicycles = []
        self.end_point = (0, 0)

        pygame.font.init()
        self.font = pygame.font.SysFont("consolas", 20)

    # управление

    def change_terms(self, d):
        self.num_terms += d
        self.num_terms = max(1, min(self.num_terms, self.max_terms))

    def toggle_pause(self):
        self.paused = not self.paused

    def toggle_function(self):
        self.fourier.toggle()
        self.wave.reset()
        self.time = 0

    def reset(self):
        self.wave.reset()
        self.time = 0

    # шаг симуляции

    def update(self):
        if self.paused:
            return

        # чем меньше time_step и time_speed, тем медленнее вращение
        self.time += self.time_step * self.time_speed

        self._update_epicycles()
        self.wave.update()

    def _update_epicycles(self):

        self.epicycles = []

        x, y = float(self.center_x), float(self.center_y)

        for i in range(self.num_terms):
            radius, freq, direction = self.fourier.get_term(i)

            # НОВОЕ: добавили rotation_speed
            angle = direction * freq * self.time * 2 * math.pi * self.rotation_speed

            x0, y0 = x, y
            x += self.scale * radius * math.cos(angle)
            y += self.scale * radius * math.sin(angle)
            r = abs(self.scale * radius)

            self.epicycles.append((x0, y0, x, y, r))

        self.end_point = (x, y)
        self.wave.add(y)

    # отрисовка

    def draw(self, surface):
        self._draw_epicycles(surface)
        self._draw_line(surface)
        self.wave.draw(surface)
        self._draw_text(surface)

    def _draw_epicycles(self, surface):
        for (sx, sy, ex, ey, r) in self.epicycles:
            pygame.draw.circle(surface, self.colors["epicycle"], (int(sx), int(sy)), int(r), 1)
            pygame.draw.line(surface, self.colors["epicycle"],
                             (int(sx), int(sy)), (int(ex), int(ey)), 2)

    def _draw_line(self, surface):
        ex, ey = self.end_point
        pygame.draw.line(surface, self.colors["line"], (int(ex), int(ey)),
                         (self.wave_origin_x, int(ey)), 1)

        pygame.draw.line(surface, self.colors["line"],
                         (self.wave_origin_x, 0),
                         (self.wave_origin_x, self.config["window"]["height"]), 1)

    def _draw_text(self, surface):
        lines = [
            f"Function: {self.fourier.name()}",
            f"Terms: {self.num_terms}",
            f"Rot speed: {self.rotation_speed:.2f}",
            "Controls:",
            "  + / Up    = add term",
            "  - / Down  = remove term",
            "  F         = switch function",
            "  Space     = pause",
            "  R         = reset",
            "  [ / ]     = rot speed - / +",
            "  ESC       = quit"
        ]

        x, y = 20, 20
        for line in lines:
            img = self.font.render(line, True, self.colors["text"])
            surface.blit(img, (x, y))
            y += 22

# MANAGER / MAIN LOOP

def main():

    config = load_or_create_config()

    pygame.init()
    screen = pygame.display.set_mode(
        (config["window"]["width"], config["window"]["height"])
    )
    pygame.display.set_caption("Fourier Visualization")

    clock = pygame.time.Clock()
    sim = Simulation(config)
    bg = config["colors"]["background"]
    fps = config["animation"]["fps"]

    running = True

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_UP):
                    sim.change_terms(+1)

                if event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_DOWN):
                    sim.change_terms(-1)

                if event.key == pygame.K_SPACE:
                    sim.toggle_pause()

                if event.key == pygame.K_f:
                    sim.toggle_function()

                if event.key == pygame.K_r:
                    sim.reset()

                # НОВОЕ: регулировка скорости вращения эпицирклов
                if event.key == pygame.K_LEFTBRACKET:   # [
                    sim.rotation_speed = max(0.05, sim.rotation_speed - 0.05)
                if event.key == pygame.K_RIGHTBRACKET:  # ]
                    sim.rotation_speed += 0.05

            if event.type == pygame.MOUSEWHEEL:
                sim.change_terms(event.y)

        sim.update()

        screen.fill(bg)
        sim.draw(screen)
        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()


if __name__ == "__main__":
    main()
