import math
from coordination.path_planning import AStarPlanner

class TrafficNegotiator:

    def __init__(self, communication_network):

        self.network = communication_network

        self.min_distance = 0.82

        self.wait_frames = {}
        self.wait_time = {}

        self.active_conflicts = set()

        self.total_conflict_episodes = 0
        self.total_resolved_episodes = 0

        self.conflicts_detected = 0
        self.conflicts_resolved = 0

        self.communication_failures = 0

        self.deadlocks_detected = 0
        self.recovery_attempts = 0
        self.successful_recoveries = 0

        self.recovery_cooldown = {}

        self.activity_log = []

        self.deadlock_threshold = 3.0
        self.recovery_interval = 2.0

    def closest_approach(self, robot_a, next_a, robot_b, next_b):

        rx = robot_a.x - robot_b.x
        ry = robot_a.y - robot_b.y

        vx = (next_a[0] - robot_a.x) - (next_b[0] - robot_b.x)
        vy = (next_a[1] - robot_a.y) - (next_b[1] - robot_b.y)

        denominator = vx * vx + vy * vy

        if denominator == 0:
            t = 0
        else:
            t = -(rx * vx + ry * vy) / denominator

        t = max(0, min(1, t))

        closest_x = rx + t * vx
        closest_y = ry + t * vy

        return math.sqrt(closest_x ** 2 + closest_y ** 2)

    def exchange_intentions(self, robot_a, robot_b):

        intent_a = {
            "robot_id": robot_a.robot_id,
            "position": (robot_a.x, robot_a.y),
            "destination": robot_a.destination
        }

        intent_b = {
            "robot_id": robot_b.robot_id,
            "position": (robot_b.x, robot_b.y),
            "destination": robot_b.destination
        }

        message_a = self.network.send_message(
            robot_a.robot_id,
            robot_b.robot_id,
            intent_a
        )

        message_b = self.network.send_message(
            robot_b.robot_id,
            robot_a.robot_id,
            intent_b
        )

        if message_a is None or message_b is None:
            self.communication_failures += 1
            return False

        return True

    def select_priority(self, robot_a, robot_b):

        wait_a = self.wait_time.get(robot_a.robot_id, 0)
        wait_b = self.wait_time.get(robot_b.robot_id, 0)

        if wait_a > wait_b:
            return robot_a

        if wait_b > wait_a:
            return robot_b

        return min(
            [robot_a, robot_b],
            key=lambda robot: robot.robot_id
        )

    def resolve(self, robots, predicted_positions, dt=1 / 60):

        allowed = {
            robot.robot_id: True
            for robot in robots
        }

        current_conflicts = set()

        # Detect potential conflicts.

        for i in range(len(robots)):

            for j in range(i + 1, len(robots)):

                robot_a = robots[i]
                robot_b = robots[j]

                next_a = predicted_positions[robot_a.robot_id]
                next_b = predicted_positions[robot_b.robot_id]

                separation = self.closest_approach(
                    robot_a, next_a,
                    robot_b, next_b
                )

                if separation >= self.min_distance:
                    continue

                pair_id = tuple(sorted([
                    robot_a.robot_id,
                    robot_b.robot_id
                ]))

                current_conflicts.add(pair_id)

                communication_ok = self.exchange_intentions(
                    robot_a,
                    robot_b
                )

                if not communication_ok:

                    allowed[robot_a.robot_id] = False
                    allowed[robot_b.robot_id] = False

                    self.activity_log.append(
                        f"Communication failure: "
                        f"{robot_a.robot_id} and {robot_b.robot_id}"
                    )

                    continue

                winner = self.select_priority(
                    robot_a,
                    robot_b
                )

                loser = (
                    robot_b if winner == robot_a else robot_a
                )

                allowed[loser.robot_id] = False

        # Final safety validation.

        changed = True

        while changed:

            changed = False

            for i in range(len(robots)):

                for j in range(i + 1, len(robots)):

                    robot_a = robots[i]
                    robot_b = robots[j]

                    next_a = (
                        predicted_positions[robot_a.robot_id]
                        if allowed[robot_a.robot_id]
                        else (robot_a.x, robot_a.y)
                    )

                    next_b = (
                        predicted_positions[robot_b.robot_id]
                        if allowed[robot_b.robot_id]
                        else (robot_b.x, robot_b.y)
                    )

                    separation = self.closest_approach(
                        robot_a, next_a,
                        robot_b, next_b
                    )

                    if separation < self.min_distance:

                        if allowed[robot_a.robot_id]:
                            allowed[robot_a.robot_id] = False
                            changed = True

                        if allowed[robot_b.robot_id]:
                            allowed[robot_b.robot_id] = False
                            changed = True

        # Update waiting time.

        for robot in robots:

            robot_id = robot.robot_id

            if allowed[robot_id]:

                self.wait_time[robot_id] = 0
                self.wait_frames[robot_id] = 0

            else:

                self.wait_time[robot_id] = (
                    self.wait_time.get(robot_id, 0) + dt
                )

                self.wait_frames[robot_id] = (
                    self.wait_frames.get(robot_id, 0) + 1
                )

        # Count conflict episodes rather than individual frames.

        new_conflicts = current_conflicts - self.active_conflicts

        resolved_conflicts = self.active_conflicts - current_conflicts

        self.total_conflict_episodes += len(new_conflicts)

        self.total_resolved_episodes += len(resolved_conflicts)

        self.active_conflicts = current_conflicts

        self.conflicts_detected = self.total_conflict_episodes

        self.conflicts_resolved = self.total_resolved_episodes

        return allowed

    def recover_stalled_robots(self, robots, planner, dt):

        for robot in robots:

            robot_id = robot.robot_id

            waiting_time = self.wait_time.get(robot_id, 0)

            self.recovery_cooldown[robot_id] = max(
                0,
                self.recovery_cooldown.get(robot_id, 0) - dt
            )

            if waiting_time < self.deadlock_threshold:
                continue

            if self.recovery_cooldown[robot_id] > 0:
                continue

            if robot.destination is None:
                continue

            self.deadlocks_detected += 1
            self.recovery_attempts += 1

            self.activity_log.append(
                f"Deadlock recovery started for {robot_id}"
            )

            # Identify cells occupied by other robots.

            dynamic_obstacles = set(planner.obstacles)

            for other_robot in robots:

                if other_robot.robot_id == robot_id:
                    continue

                other_cell = (
                    int(round(other_robot.x)),
                    int(round(other_robot.y))
                )

                dynamic_obstacles.add(other_cell)

            # Create a temporary planner.

            recovery_planner = AStarPlanner(
                planner.rows,
                planner.cols,
                dynamic_obstacles
            )

            start = (
                int(round(robot.x)),
                int(round(robot.y))
            )

            goal = tuple(robot.destination)

            # Calculate an alternative path.

            new_path = recovery_planner.find_path(
                start,
                goal
            )

            if new_path and len(new_path) > 1:

                robot.set_path(new_path)
                
                robot.recovery_count += 1

                robot.previous_distance = None
                robot.stuck_time = 0

                self.successful_recoveries += 1

                self.wait_time[robot_id] = 0
                self.wait_frames[robot_id] = 0

                self.activity_log.append(
                    f"Alternative route assigned to {robot_id}"
                )

            else:

                self.activity_log.append(
                    f"No alternative route found for {robot_id}"
                )

            # Prevent repeated replanning every frame.

            self.recovery_cooldown[robot_id] = (
                self.recovery_interval
            )