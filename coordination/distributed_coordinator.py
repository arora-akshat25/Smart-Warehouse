import math
import random


class CommunicationNetwork:

    def __init__(self, latency=0.1, packet_loss=0.0):

        self.latency = latency
        self.packet_loss = packet_loss

        self.messages_sent = 0
        self.messages_dropped = 0

    def send_message(self, sender, receiver, message):

        self.messages_sent += 1

        if random.random() < self.packet_loss:

            self.messages_dropped += 1
            return None

        return {
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "latency": self.latency
        }


class RobotAgent:

    def __init__(self, robot, planner):

        self.robot = robot
        self.planner = planner

        self.known_bids = {}

        self.assigned_task = None

    def calculate_bid(self, task):

        start = (
            round(self.robot.x),
            round(self.robot.y)
        )

        path = self.planner.find_path(
            start,
            task["destination"]
        )

        if not path:
            return float("inf")

        distance = len(path) - 1

        # Faster robots receive a lower travel-time cost.
        travel_time = distance / max(self.robot.speed, 0.1)

        # Low battery increases the cost of accepting a task.
        battery_penalty = (
            100 - self.robot.battery
        ) * 0.15

        # A robot already handling a task is less available.
        workload_penalty = (
            20 if self.assigned_task is not None else 0
        )

        total_bid = (
            travel_time
            + battery_penalty
            + workload_penalty
        )

        return round(total_bid, 2)

    def create_bid(self, task):

        bid = self.calculate_bid(task)

        return {
            "robot_id": self.robot.robot_id,
            "task_id": task["task_id"],
            "bid": bid
        }

    def receive_bid(self, bid):

        task_id = bid["task_id"]

        if task_id not in self.known_bids:
            self.known_bids[task_id] = []

        self.known_bids[task_id].append(bid)


class DistributedCoordinator:

    def __init__(self, robots, planner):

        self.robots = robots
        self.planner = planner

        self.network = CommunicationNetwork(
            latency=0.1,
            packet_loss=0.0
        )

        self.agents = [
            RobotAgent(robot, planner)
            for robot in robots
        ]

        self.activity_log = []

        self.assignments = {}
    def negotiate_tasks(self, tasks):

        self.assignments = {}

        self.activity_log.append(
            "Distributed task negotiation started"
        )

        # ----------------------------------
        # PHASE 1: ROBOTS CALCULATE THEIR BIDS
        # ----------------------------------

        all_bids = []

        for agent in self.agents:

            for task in tasks:

                bid = agent.create_bid(task)

                if math.isfinite(bid["bid"]):

                    all_bids.append(bid)

        # ----------------------------------
        # PHASE 2: EXCHANGE BID INFORMATION
        # ----------------------------------

        for bid in all_bids:

            for agent in self.agents:

                if agent.robot.robot_id == bid["robot_id"]:
                    continue

                message = self.network.send_message(
                    bid["robot_id"],
                    agent.robot.robot_id,
                    bid
                )

                if message is not None:

                    agent.receive_bid(
                        message["message"]
                    )

        # Each robot retains its own bids.
        for bid in all_bids:

            for agent in self.agents:

                if agent.robot.robot_id == bid["robot_id"]:

                    agent.receive_bid(bid)

        # ----------------------------------
        # PHASE 3: ROBOTS RANK THEIR TASKS
        # ----------------------------------

        preferences = {}

        for agent in self.agents:

            robot_id = agent.robot.robot_id

            own_bids = [

                bid for bid in all_bids

                if bid["robot_id"] == robot_id

            ]

            preferences[robot_id] = sorted(
                own_bids,
                key=lambda b: (
                    b["bid"],
                    b["task_id"]
                )
            )

        # ----------------------------------
        # PHASE 4: DISTRIBUTED NEGOTIATION
        # ----------------------------------

        # Each task temporarily holds one robot.
        task_holders = {}

        # Track the next task each robot can propose to.
        next_choice = {
            agent.robot.robot_id: 0
            for agent in self.agents
        }

        # Robots initially have no assigned task.
        free_robots = [
            agent.robot.robot_id
            for agent in self.agents
        ]

        # Maximum proposals prevent infinite loops.
        max_proposals = sum(
            len(bids)
            for bids in preferences.values()
        )

        proposal_count = 0

        while free_robots and proposal_count < max_proposals:

            robot_id = free_robots.pop(0)

            robot_preferences = preferences[robot_id]

            index = next_choice[robot_id]

            # No more tasks available for this robot.
            if index >= len(robot_preferences):
                continue

            # Select the robot's next preferred task.
            proposal = robot_preferences[index]

            next_choice[robot_id] += 1

            task_id = proposal["task_id"]

            proposal_count += 1

            self.activity_log.append(
                f"{robot_id} proposed for {task_id}"
            )

            # Task is currently unassigned.
            if task_id not in task_holders:

                task_holders[task_id] = proposal

                continue

            # Compare the new proposal with current holder.
            current_holder = task_holders[task_id]

            if (
                proposal["bid"],
                proposal["robot_id"]
            ) < (
                current_holder["bid"],
                current_holder["robot_id"]
            ):

                # Task accepts the better proposal.
                rejected_robot = current_holder["robot_id"]

                task_holders[task_id] = proposal

                # Previously accepted robot becomes free.
                free_robots.append(rejected_robot)

                self.activity_log.append(
                    f"{task_id} accepted {robot_id} "
                    f"and rejected {rejected_robot}"
                )

            else:

                # Current holder remains.
                # New robot can propose to another task.
                free_robots.append(robot_id)

                self.activity_log.append(
                    f"{task_id} rejected {robot_id}"
                )

        # ----------------------------------
        # PHASE 5: FINAL TASK ASSIGNMENTS
        # ----------------------------------

        for task_id, winning_bid in task_holders.items():

            robot_id = winning_bid["robot_id"]

            self.assignments[task_id] = robot_id

            self.activity_log.append(
                f"{robot_id} won {task_id} "
                f"with bid {winning_bid['bid']}"
            )

        self.activity_log.append(
            f"Negotiation completed: "
            f"{len(self.assignments)} tasks assigned"
        )

        return self.assignments