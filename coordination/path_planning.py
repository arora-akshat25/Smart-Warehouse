import heapq


class AStarPlanner:

    def __init__(self, rows, cols, obstacles):

        self.rows = rows
        self.cols = cols

        self.obstacles = set(obstacles)

    def heuristic(self, a, b):

        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, node):

        x, y = node

        directions = [
            (0, 1),
            (0, -1),
            (1, 0),
            (-1, 0)
        ]

        neighbors = []

        for dx, dy in directions:

            nx = x + dx
            ny = y + dy

            if (
                0 <= nx < self.cols
                and 0 <= ny < self.rows
                and (nx, ny) not in self.obstacles
            ):

                neighbors.append((nx, ny))

        return neighbors

    def find_path(self, start, goal, reserved_cells=None):

        start = tuple(start)
        goal = tuple(goal)

        if reserved_cells is None:
            reserved_cells = set()

        if start in self.obstacles or goal in self.obstacles:
            return []

        open_list = []

        heapq.heappush(
            open_list,
            (0, start)
        )

        came_from = {}

        g_score = {
            start: 0
        }

        while open_list:

            _, current = heapq.heappop(open_list)

            if current == goal:

                path = [current]

                while current in came_from:

                    current = came_from[current]

                    path.append(current)

                return path[::-1]

            for neighbor in self.get_neighbors(current):

                # Prefer routes not already allocated
                route_penalty = 0

                if neighbor in reserved_cells:

                    route_penalty = 8

                tentative_g = (
                    g_score[current]
                    + 1
                    + route_penalty
                )

                if tentative_g < g_score.get(
                    neighbor, float("inf")
                ):

                    came_from[neighbor] = current

                    g_score[neighbor] = tentative_g

                    f_score = (
                        tentative_g
                        + self.heuristic(neighbor, goal)
                    )

                    heapq.heappush(
                        open_list,
                        (f_score, neighbor)
                    )

        return []