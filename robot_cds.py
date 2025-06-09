import random
import math
import copy

BROADCAST_LIFETIME = 40
BROADCAST_RANGE = 500.0

OPERATOR_X = 1000
OPERATOR_Y = 360

SWARM_SIZE = 15

all_robots = []

relay_counter = 0
#### BROADCAST STUFF

class Broadcast:
    all_broadcasts = {}
    id_counter = 0

    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int):
        self.x = x
        self.y = y
        self.age = 0
        self.id = Broadcast.id_counter
        Broadcast.id_counter += 1

        self.robot_id = robot_id
        self.msg_id = msg_id
        self.last_robot_id = last_robot_id

        # Assign random times for all robots in range to receive 
        self.rx_times = []
        for robot in all_robots:
            distance = math.sqrt((x - robot.x)**2 + (y - robot.y)**2)
            if distance < BROADCAST_RANGE and distance > 0.0001:
                # Time varies with distance
                self.rx_times.append(int(distance / BROADCAST_RANGE * BROADCAST_LIFETIME + random.randint(0, int(BROADCAST_LIFETIME / 8))))
            else:
                self.rx_times.append(-1)

    def tick(self) -> list:
        new_broadcasts = []

        # Robot receives message if the time is right
        for i in range(len(self.rx_times)):
            if self.rx_times[i] == self.age:
                new_broadcasts.append(all_robots[i].receive_message(self))

        self.age += 1
        self.color[3] = 100 - (100 * self.age / BROADCAST_LIFETIME)

        return new_broadcasts

class GPSBroadcast (Broadcast):
    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int, location: tuple):
        self.location = location
        self.color = [255, 190, 100, 100]
        super().__init__(x, y, robot_id, msg_id, last_robot_id)

class GreedyBroadcast (Broadcast):
    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int):
        self.color = [150, 255, 50, 100]
        super().__init__(x, y, robot_id, msg_id, last_robot_id)

class CDSBroadcast (Broadcast):
    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int, neighbors: list):
        self.neighbors = neighbors
        self.color = [100, 100, 255, 100]
        super().__init__(x, y, robot_id, msg_id, last_robot_id)

class RobotState:
    gps_location = tuple
    last_message_id = int
    status = "ready"
    battery = 1.0
    last_message_id = -1

    def __init__(self, gps_location: tuple, last_message_id: int, status: str, battery: float):
        self.gps_location = gps_location
        self.last_message_id = last_message_id
        self.status = status
        self.battery = battery

class Robot:
    def __init__(self, id: int, x: float, y: float):
        self.id = id
        self.x = x
        self.y = y
        self.msg_count = 0
        self.neighbors = []     # Adjacency list, 0 = disconnected, 1 = connected
        for i in range(SWARM_SIZE):
            self.neighbors.append(0)
        self.in_cds = False  # Start as non-CDS node
        self.degree = 0      # Track number of neighbors

        self.destination_x = random.randint(100, 1280-100)
        self.destination_y = random.randint(100, 720-100)

        self.swarm_state = []
        for i in range(SWARM_SIZE):
            self.swarm_state.append(
                RobotState(gps_location=(0, 0), last_message_id=-1, status="ready", battery=1.0)
            )

    def update_cds_status(self):
        # Count active neighbors
        self.degree = sum(1 for n in self.neighbors if n > 0)
        
        # Rule 1: If a node has no neighbors, it must be in CDS
        if self.degree == 0:
            self.in_cds = True
            print("IN CDS")
            return
            
        # Rule 2: If a node has only one neighbor, it must be in CDS
        if self.degree == 1:
            self.in_cds = True
            print("IN CDS")
            return
            
        # Rule 3: If a node has two neighbors that are not connected to each other,
        # it must be in CDS
        for i in range(SWARM_SIZE):
            if self.neighbors[i] > 0:
                for j in range(i + 1, SWARM_SIZE):
                    if self.neighbors[j] > 0:
                        if all_robots[i].neighbors[j] == 0:
                            self.in_cds = True
                            print("IN CDS")
                            return
        
        print("NOT IN CDS")
        # If none of the rules apply, node is not in CDS
        self.in_cds = False

    def broadcast_cds(self):
        self.msg_count += 1
        self.swarm_state[self.id].last_message_id = self.msg_count

        # Update neighbor relationships - reduce decay rate
        for i in range(SWARM_SIZE):
            if self.neighbors[i] > 0:
                self.neighbors[i] -= 0.1  # Slower decay

        new_bc = CDSBroadcast(self.x, self.y, self.id, self.msg_count, self.id, self.neighbors)
        Broadcast.all_broadcasts.update({new_bc.id: new_bc})

    def relay_cds(self, robot_id, msg_id, last_robot_id):
        # Include our current neighbor information in the relay
        return CDSBroadcast(self.x, self.y, robot_id, msg_id, last_robot_id, self.neighbors)

    def tick(self):
        dist = distance(self, (self.destination_x, self.destination_y))
        if dist > 2.5:
            self.x += (self.destination_x - self.x) / dist * 2
            self.y += (self.destination_y - self.y) / dist * 2

    def broadcast_gps(self) -> None:
        global all_robots
        location = (self.x + random.randint(-10, 10), self.y + random.randint(-10, 10))

        # Update internal state
        self.msg_count += 1
        self.swarm_state[self.id].gps_location = location
        self.swarm_state[self.id].last_message_id = self.msg_count

        new_bc = GPSBroadcast(self.x, self.y, self.id, self.msg_count, self.id, location)
        Broadcast.all_broadcasts.update({new_bc.id: new_bc})

    def relay_gps(self, robot_id, msg_id, location) -> GPSBroadcast:
        global relay_counter
        if self.id == 0:
            print("RELAYING:", relay_counter)
            relay_counter += 1
        return GPSBroadcast(self.x, self.y, robot_id, msg_id, self.id, location)

    def broadcast_greedy(self):
        self.msg_count += 1
        self.swarm_state[self.id].last_message_id = self.msg_count

        new_bc = GreedyBroadcast(self.x, self.y, self.id, self.msg_count, self.id)
        Broadcast.all_broadcasts.update({new_bc.id: new_bc})
      
    def relay_greedy(self, robot_id, msg_id, last_robot_id):
        return GreedyBroadcast(self.x, self.y, robot_id, msg_id, last_robot_id)

    def receive_message(self, message: Broadcast):
        # Ignore message conditions (either robot sent this message, or it has already been received)
        if message.robot_id == self.id:
            return

        if self.swarm_state[message.robot_id].last_message_id >= message.msg_id:
            return

        # Update CDS status when receiving CDS messages
        if isinstance(message, CDSBroadcast):
            # Update our neighbor information
            self.neighbors[message.robot_id] = 3
            # Also update neighbors of neighbors
            for i in range(SWARM_SIZE):
                if message.neighbors[i] > 0:
                    self.neighbors[i] = max(self.neighbors[i], 2)  # Secondary connection
            self.update_cds_status()
            return

        # Only relay messages if in CDS
        if not self.in_cds:
            return

        self.swarm_state[message.robot_id].last_message_id = message.msg_id

        # GPS message
        if isinstance(message, GPSBroadcast):        
            self.swarm_state[message.robot_id].gps_location = message.location
            output = self.relay_gps(message.robot_id, message.msg_id, message.location)
            return output

        # Greedy algorithm
        if isinstance(message, GreedyBroadcast):
            last_robot = all_robots[message.last_robot_id]
            if distance(last_robot, (OPERATOR_X, OPERATOR_Y)) < distance(self, (OPERATOR_X, OPERATOR_Y)):
                return
            output = self.relay_greedy(message.robot_id, message.msg_id, self.id)            
            return output

        # CDS broadcast
        if isinstance(message, CDSBroadcast):
            output = self.relay_cds(message.robot_id, message.msg_id, self.id)
            return output

def distance(p1, p2) -> float:
    if isinstance(p1, tuple) or isinstance(p1, list):
        x1 = p1[0]
        y1 = p1[1]
    else:
        x1 = p1.x
        y1 = p1.y

    if isinstance(p2, tuple) or isinstance(p2, list):
        x2 = p2[0]
        y2 = p2[1]
    else:
        x2 = p2.x
        y2 = p2.y

    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def bridges(this: Robot, other: Robot, source: Robot):
    # If other is close enough to source, don't bother
    if distance(other, source) < BROADCAST_RANGE * 0.8:     # Multiplied by 1.2 for padding factor
        return False
    
    # If other is too far away, don't bother
    if distance(this, other) > BROADCAST_RANGE * 1.2:
        return False
    
    return True

def is_bridge(this: Robot, source: Robot):
    # TEMPORARY: minimum distance check
    if distance(this, source) < 50:
        return False

    for robot in all_robots:
        if robot.id != this.id:
            if bridges(this, robot, source):
                return True
            
    return False