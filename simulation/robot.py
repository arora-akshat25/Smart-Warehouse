import pygame
import math


class Robot:

    def __init__(self, robot_id, start_position, color, speed=2.0):

        self.robot_id = robot_id

        self.x = float(start_position[0])
        self.y = float(start_position[1])

        self.start_position = start_position

        self.color = color

        self.speed = speed

        self.battery = 100

        self.status = "MOVING"

        self.current_task = None

        self.destination = None

        self.path = []

        self.target_index = 0

        self.trail = []

        self.direction = 0

        self.radius = 11

        self.completed_tasks = 0

    def set_path(self, path):

        self.path = path

        self.target_index = 0

    def update(self, dt):

        if not self.path:
            return

        if self.target_index >= len(self.path):
            self.path.reverse()
            self.target_index = 0
            self.completed_tasks += 1
            return

        target_x, target_y = self.path[self.target_index]

        dx = target_x - self.x
        dy = target_y - self.y

        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance < 0.08:

            self.target_index += 1

            return

        self.direction = math.atan2(dy, dx)

        movement = min(self.speed * dt, distance)

        self.x += (dx / distance) * movement
        self.y += (dy / distance) * movement

        self.battery = max(
            0,
            self.battery - movement * 0.015
        )

        self.trail.append((self.x, self.y))

        if len(self.trail) > 80:

            self.trail.pop(0)

    def draw(self, screen, map_x, map_y, cell_size):

        pixel_x = map_x + (self.x + 0.5) * cell_size

        pixel_y = map_y + (self.y + 0.5) * cell_size

        # Movement trail

        if len(self.trail) > 1:

            points = [

                (
                    map_x + (x + 0.5) * cell_size,
                    map_y + (y + 0.5) * cell_size
                )

                for x, y in self.trail

            ]

            pygame.draw.lines(
                screen,
                self.color,
                False,
                points,
                2
            )

        # Robot body

        pygame.draw.circle(
            screen,
            self.color,
            (int(pixel_x), int(pixel_y)),
            self.radius
        )

        # Robot outline

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (int(pixel_x), int(pixel_y)),
            self.radius,
            2
        )

        # Direction indicator

        end_x = pixel_x + math.cos(self.direction) * 13

        end_y = pixel_y + math.sin(self.direction) * 13

        pygame.draw.line(

            screen,
            (255, 255, 255),

            (pixel_x, pixel_y),

            (end_x, end_y),

            3

        )

        # Robot label

        font = pygame.font.SysFont(
            "Arial", 13, bold=True
        )

        label = font.render(
            self.robot_id,
            True,
            (255, 255, 255)
        )

        screen.blit(
            label,
            (pixel_x - 23, pixel_y - 28)
        )