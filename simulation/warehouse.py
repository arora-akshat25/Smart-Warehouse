import pygame
import math
from datetime import datetime

from simulation.robot import Robot
from coordination.path_planning import AStarPlanner
from coordination.traffic_negotiator import TrafficNegotiator

class Warehouse:

    def __init__(self):

        pygame.init()

        # WINDOW
        self.WIDTH = 1400
        self.HEIGHT = 850

        self.screen = pygame.display.set_mode(
            (self.WIDTH, self.HEIGHT)
        )

        pygame.display.set_caption(
            "AMR Fleet Intelligence System"
        )

        self.clock = pygame.time.Clock()

        # COLORS
        self.BG = (15, 20, 30)
        self.PANEL = (25, 32, 45)
        self.WHITE = (235, 240, 245)
        self.GRAY = (130, 145, 165)

        self.BLUE = (50, 145, 255)
        self.CYAN = (0, 210, 220)
        self.GREEN = (40, 210, 130)
        self.RED = (245, 75, 75)
        self.YELLOW = (255, 190, 60)

        self.FLOOR = (30, 39, 52)
        self.GRID = (48, 60, 75)

        self.RACK = (80, 95, 115)

        # FONTS
        self.font_small = pygame.font.SysFont(
            "Arial", 15
        )

        self.font_medium = pygame.font.SysFont(
            "Arial", 19, bold=True
        )

        self.font_large = pygame.font.SysFont(
            "Arial", 27, bold=True
        )

        self.font_title = pygame.font.SysFont(
            "Arial", 30, bold=True
        )

        # MAP CONFIGURATION
        self.map_x = 25
        self.map_y = 115

        self.cell = 30

        self.cols = 28
        self.rows = 20

        self.map_width = self.cols * self.cell
        self.map_height = self.rows * self.cell

        # STORAGE RACKS
        self.racks = [

            (4, 3, 3, 3),
            (9, 3, 3, 3),
            (15, 3, 3, 3),
            (21, 3, 3, 3),

            (4, 9, 3, 3),
            (9, 9, 3, 3),
            (15, 9, 3, 3),
            (21, 9, 3, 3),

            (4, 15, 3, 2),
            (9, 15, 3, 2),
            (15, 15, 3, 2),
            (21, 15, 3, 2)

        ]

        # STATIONS
        self.pickup = (1, 5)
        self.delivery = (26, 5)
        self.charging = (1, 17)

        # ZONES
        self.zones = [
            ("ZONE A", 1, 1, 6, 18),
            ("ZONE B", 7, 1, 7, 18),
            ("ZONE C", 14, 1, 7, 18),
            ("ZONE D", 21, 1, 6, 18)
        ]

        # CONTROLS
        self.running = True
        self.show_grid = True
        self.show_zones = True

        # ROBOT FLEET
        self.robots = [

            Robot(
                "AMR-01",
                (2, 6),
                (40, 150, 255),
                2.0
            ),

            Robot(
                "AMR-02",
                (2, 7),
                (0, 220, 200),
                1.8
            ),

            Robot(
                "AMR-03",
                (2, 8),
                (180, 100, 255),
                2.2
            ),

            Robot(
                "AMR-04",
                (2, 12),
                (255, 170, 40),
                1.7
            ),

            Robot(
                "AMR-05",
                (2, 13),
                (255, 90, 120),
                2.0
            )

        ]

        # ==========================================
        # A* COORDINATED PATH PLANNING
        # ==========================================

        # 1. Identify warehouse rack obstacles

        obstacles = set()

        for x, y, w, h in self.racks:

            for dx in range(w):

                for dy in range(h):

                    obstacles.add((x + dx, y + dy))


        # 2. Initialize A* planner

        self.path_planner = AStarPlanner(
            self.rows,
            self.cols,
            obstacles
        )


        # 3. Assign different destinations

        robot_destinations = [

            (26, 5),
            (26, 7),
            (26, 11),
            (26, 13),
            (26, 17)

        ]


        # 4. Coordinate route allocation

        # ==========================================
        # DISTRIBUTED TASK NEGOTIATION
        # ==========================================

        from coordination.distributed_coordinator import (
            DistributedCoordinator
        )

        # Create warehouse tasks.
        warehouse_tasks = [

            {
                "task_id": "TASK-01",
                "destination": (26, 5)
            },

            {
                "task_id": "TASK-02",
                "destination": (26, 7)
            },

            {
                "task_id": "TASK-03",
                "destination": (26, 11)
            },

            {
                "task_id": "TASK-04",
                "destination": (26, 13)
            },

            {
                "task_id": "TASK-05",
                "destination": (26, 17)
            }

        ]

        # Initialize distributed coordination.
        self.coordinator = DistributedCoordinator(
            self.robots,
            self.path_planner
        )
        
        # Initialize distributed traffic negotiation.
        self.traffic_negotiator = TrafficNegotiator(
            self.coordinator.network
        )
        
        

        # Let robots negotiate tasks.
        assignments = self.coordinator.negotiate_tasks(
            warehouse_tasks
        )

        # Apply negotiated assignments.
        for task in warehouse_tasks:

            task_id = task["task_id"]

            if task_id not in assignments:
                continue

            robot_id = assignments[task_id]

            robot = next(
                r for r in self.robots
                if r.robot_id == robot_id
            )

            destination = task["destination"]

            start = (
                round(robot.x),
                round(robot.y)
            )

            path = self.path_planner.find_path(
                start,
                destination
            )

            if path:

                robot.set_path(path)

                robot.current_task = task_id

                robot.destination = destination

                print(
                    f"{robot.robot_id} assigned "
                    f"{task_id} | "
                    f"Destination: {destination}"
                )

        # Print negotiation activity.
        for activity in self.coordinator.activity_log:

            print("[COORDINATION]", activity)

        print(
            "Messages exchanged:",
            self.coordinator.network.messages_sent
        )
    # ==========================================
    # TEXT DRAWING
    # ==========================================

    def draw_text(
        self,
        text,
        x,
        y,
        color=None,
        font=None
    ):

        if color is None:
            color = self.WHITE

        if font is None:
            font = self.font_small

        surface = font.render(
            str(text),
            True,
            color
        )

        self.screen.blit(surface, (x, y))

    # ==========================================
    # CARD DRAWING
    # ==========================================

    def draw_card(self, x, y, width, height):

        rect = pygame.Rect(
            x, y, width, height
        )

        pygame.draw.rect(
            self.screen,
            self.PANEL,
            rect,
            border_radius=10
        )

    # ==========================================
    # HEADER
    # ==========================================

    def draw_header(self):

        pygame.draw.rect(
            self.screen,
            self.PANEL,
            (0, 0, self.WIDTH, 85)
        )

        self.draw_text(
            "AMR FLEET INTELLIGENCE",
            30, 18,
            self.CYAN,
            self.font_title
        )

        self.draw_text(
            "DISTRIBUTED SMART WAREHOUSE MANAGEMENT SYSTEM",
            32, 55,
            self.GRAY
        )

        pygame.draw.circle(
            self.screen,
            self.GREEN,
            (1120, 35),
            7
        )

        self.draw_text(
            "SYSTEM ONLINE",
            1135, 27,
            self.GREEN,
            self.font_medium
        )

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.draw_text(
            current_time,
            1290, 30,
            self.WHITE,
            self.font_medium
        )

    # ==========================================
    # WAREHOUSE MAP
    # ==========================================

    def draw_warehouse(self):

        area = pygame.Rect(
            self.map_x,
            self.map_y,
            self.map_width,
            self.map_height
        )

        pygame.draw.rect(
            self.screen,
            self.FLOOR,
            area,
            border_radius=8
        )

        if self.show_zones:

            zone_colors = [
                (45, 65, 85),
                (40, 70, 80),
                (55, 65, 90),
                (65, 60, 80)
            ]

            for i, zone in enumerate(self.zones):

                name, x, y, w, h = zone

                rect = pygame.Rect(
                    self.map_x + x * self.cell,
                    self.map_y + y * self.cell,
                    w * self.cell,
                    h * self.cell
                )

                pygame.draw.rect(
                    self.screen,
                    zone_colors[i],
                    rect
                )

                self.draw_text(
                    name,
                    rect.x + 5,
                    rect.y + 5,
                    self.GRAY
                )

        if self.show_grid:

            for x in range(self.cols + 1):

                px = self.map_x + x * self.cell

                pygame.draw.line(
                    self.screen,
                    self.GRID,
                    (px, self.map_y),
                    (px, self.map_y + self.map_height)
                )

            for y in range(self.rows + 1):

                py = self.map_y + y * self.cell

                pygame.draw.line(
                    self.screen,
                    self.GRID,
                    (self.map_x, py),
                    (self.map_x + self.map_width, py)
                )

        pygame.draw.rect(
            self.screen,
            self.CYAN,
            area,
            2,
            border_radius=8
        )

    # ==========================================
    # STORAGE RACKS
    # ==========================================

    def draw_racks(self):

        for x, y, w, h in self.racks:

            rect = pygame.Rect(
                self.map_x + x * self.cell,
                self.map_y + y * self.cell,
                w * self.cell,
                h * self.cell
            )

            pygame.draw.rect(
                self.screen,
                self.RACK,
                rect,
                border_radius=4
            )

            pygame.draw.rect(
                self.screen,
                self.PANEL,
                rect,
                2,
                border_radius=4
            )

            for i in range(1, w):

                px = rect.x + i * self.cell

                pygame.draw.line(
                    self.screen,
                    self.WHITE,
                    (px, rect.y),
                    (px, rect.bottom)
                )

            for i in range(1, h):

                py = rect.y + i * self.cell

                pygame.draw.line(
                    self.screen,
                    self.WHITE,
                    (rect.x, py),
                    (rect.right, py)
                )

    # ==========================================
    # STATIONS
    # ==========================================

    def draw_station(self, position, color, label):

        x, y = position

        rect = pygame.Rect(
            self.map_x + x * self.cell,
            self.map_y + y * self.cell,
            self.cell,
            self.cell
        )

        pygame.draw.rect(
            self.screen,
            color,
            rect,
            border_radius=5
        )

        self.draw_text(
            label,
            rect.x - 8,
            rect.y - 22
        )

    def draw_stations(self):

        self.draw_station(
            self.pickup,
            self.GREEN,
            "PICKUP"
        )

        self.draw_station(
            self.delivery,
            self.RED,
            "DELIVERY"
        )

        self.draw_station(
            self.charging,
            self.YELLOW,
            "CHARGING"
        )
    # ==========================================
    # ROBOT MOVEMENT AND COLLISION AVOIDANCE
    # ==========================================

    def predict_next_position(self, robot, dt):

        # No movement if the robot has no path
        if not robot.path:
            return robot.x, robot.y

        if robot.target_index >= len(robot.path):
            return robot.x, robot.y

        target_x, target_y = robot.path[robot.target_index]

        dx = target_x - robot.x
        dy = target_y - robot.y

        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance < 0.08:
            return robot.x, robot.y

        movement = min(robot.speed * dt, distance)

        next_x = robot.x + (dx / distance) * movement
        next_y = robot.y + (dy / distance) * movement

        return next_x, next_y

    def update_robots(self, dt):

        # -----------------------------------
        # PHASE 1: PREDICT ROBOT MOVEMENTS
        # -----------------------------------

        predicted_positions = {}

        for robot in self.robots:

            predicted_positions[robot.robot_id] = (
                self.predict_next_position(robot, dt)
            )

        # -----------------------------------
        # PHASE 2: NEGOTIATE TRAFFIC
        # -----------------------------------

        allowed = self.traffic_negotiator.resolve(
            self.robots,
            predicted_positions,
            dt
        )

        # Attempt recovery for robots waiting too long.
        self.traffic_negotiator.recover_stalled_robots(
            self.robots,
            self.path_planner,
            dt
        )

        # -----------------------------------
        # PHASE 3: EXECUTE APPROVED MOVEMENTS
        # -----------------------------------

        for robot in self.robots:

            can_move = allowed[robot.robot_id]

            robot.update(
                dt,
                allow_move=can_move
            )

            if can_move:
                robot.status = "MOVING"
            else:
                robot.status = "WAITING"
                
        # -----------------------------------
        # TRAFFIC MONITORING
        # -----------------------------------

        self.traffic_update_timer = getattr(
            self, "traffic_update_timer", 0
        )

        self.traffic_update_timer += dt

        if self.traffic_update_timer >= 2:

            self.traffic_update_timer = 0

            waiting = sum(
                1 for robot in self.robots
                if robot.status == "WAITING"
            )

            print("\n========== TRAFFIC REPORT ==========")

            print(
                "Total conflict episodes:",
                self.traffic_negotiator.total_conflict_episodes
            )

            print(
                "Resolved conflict episodes:",
                self.traffic_negotiator.total_resolved_episodes
            )

            print(
                "Currently active conflicts:",
                len(self.traffic_negotiator.active_conflicts)
            )

            print(
                "Communication failures:",
                self.traffic_negotiator.communication_failures
            )

            waiting_robots = [
                robot.robot_id
                for robot in self.robots
                if robot.status == "WAITING"
            ]

            print("Waiting robots:", waiting_robots)
            
            print(
                "Deadlocks detected:",
                self.traffic_negotiator.deadlocks_detected
            )

            print(
                "Recovery attempts:",
                self.traffic_negotiator.recovery_attempts
            )

            print(
                "Successful recoveries:",
                self.traffic_negotiator.successful_recoveries
            )

            print("====================================")
                    
                    
    # ==========================================
    # ROBOT DISPLAY
    # ==========================================

    def draw_robots(self):

        for robot in self.robots:

            robot.draw(
                self.screen,
                self.map_x,
                self.map_y,
                self.cell
            )

    # ==========================================
    # FLEET SIDEBAR
    # ==========================================

    def draw_sidebar(self):

        x = 880
        width = 490

        self.draw_card(x, 115, width, 145)

        self.draw_text(
            "FLEET OVERVIEW",
            x + 20, 130,
            self.CYAN,
            self.font_large
        )

        active = sum(
            1 for r in self.robots
            if r.status == "MOVING"
        )

        stats = [
            ("TOTAL ROBOTS", len(self.robots), self.BLUE),
            ("ACTIVE ROBOTS", active, self.GREEN),
            ("PENDING TASKS", 0, self.YELLOW),
            (
                "CONFLICTS",
                self.traffic_negotiator.conflicts_detected,
                self.RED
            )
        ]

        for i, (label, value, color) in enumerate(stats):

            px = x + 20 + (i % 2) * 225
            py = 175 + (i // 2) * 48

            self.draw_text(label, px, py, self.GRAY)

            self.draw_text(
                str(value),
                px + 145,
                py - 3,
                color,
                self.font_medium
            )

        # Robot status panel

        self.draw_card(x, 275, width, 270)

        self.draw_text(
            "ROBOT FLEET STATUS",
            x + 20, 290,
            self.CYAN,
            self.font_large
        )

        for i, robot in enumerate(self.robots):

            py = 340 + i * 38

            self.draw_text(
                robot.robot_id,
                x + 20,
                py
            )

            if robot.status == "MOVING":
                color = self.BLUE

            elif robot.status == "WAITING":
                color = self.YELLOW

            else:
                color = self.GREEN

            self.draw_text(
                robot.status,
                x + 130,
                py,
                color
            )

            pygame.draw.rect(
                self.screen,
                (48, 60, 78),
                (x + 285, py + 2, 110, 12),
                border_radius=5
            )

            battery_width = int(
                max(0, min(100, robot.battery)) * 1.1
            )

            pygame.draw.rect(
                self.screen,
                self.GREEN,
                (x + 285, py + 2, battery_width, 12),
                border_radius=5
            )

            self.draw_text(
                f"{int(robot.battery)}%",
                x + 405,
                py - 3
            )

        # Activity panel

        self.draw_card(x, 560, width, 165)

        self.draw_text(
            "SYSTEM ACTIVITY",
            x + 20, 575,
            self.CYAN,
            self.font_large
        )

        activities = [
            "Fleet monitoring initialized",
            "Warehouse zones loaded",
            "Robot simulation active",
            "Computer vision awaiting input"
        ]

        for i, activity in enumerate(activities):

            self.draw_text(
                "> " + activity,
                x + 20,
                625 + i * 23,
                self.GRAY
            )

    # ==========================================
    # FOOTER
    # ==========================================

    def draw_footer(self):

        pygame.draw.rect(
            self.screen,
            self.PANEL,
            (0, 770, self.WIDTH, 80)
        )

        self.draw_text(
            "CONTROLS",
            25, 785,
            self.CYAN,
            self.font_medium
        )

        self.draw_text("G - Toggle Grid", 160, 785)

        self.draw_text("Z - Toggle Zones", 320, 785)

        self.draw_text("ESC - Exit", 490, 785)

        self.draw_text(
            "AMR SMART WAREHOUSE | SOFTWARE SIMULATION",
            850, 785,
            self.GRAY
        )

    # ==========================================
    # EVENT HANDLING
    # ==========================================

    def handle_events(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                self.running = False

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    self.running = False

                elif event.key == pygame.K_g:

                    self.show_grid = not self.show_grid

                elif event.key == pygame.K_z:

                    self.show_zones = not self.show_zones

    # ==========================================
    # MAIN LOOP
    # ==========================================

    def run(self):

        while self.running:

            dt = min(
                self.clock.tick(60) / 1000.0,
                0.05
            )

            self.handle_events()

            self.update_robots(dt)

            self.screen.fill(self.BG)

            self.draw_header()

            self.draw_warehouse()

            self.draw_racks()

            self.draw_stations()

            self.draw_robots()

            self.draw_sidebar()

            self.draw_footer()

            pygame.display.flip()

        pygame.quit()