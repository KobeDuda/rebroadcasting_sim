import random
import math
import copy

BROADCAST_LIFETIME = 40
BROADCAST_RANGE = 500.0

OPERATOR_X = 1000
OPERATOR_Y = 360

SWARM_SIZE = 7

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
        self.delay = 0
        self.color = [255, 255, 255, 100]  # Default white color with alpha

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
        if hasattr(self, 'color'):
            # Clamp alpha between 0 and 100
            alpha = max(0, min(100, 100 - (100 * self.age / BROADCAST_LIFETIME)))
            self.color[3] = alpha

        return new_broadcasts

class GPSBroadcast (Broadcast):
    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int, location: tuple):
        super().__init__(x, y, robot_id, msg_id, last_robot_id)
        self.location = location
        self.color = [255, 190, 100, 100]

class GreedyBroadcast (Broadcast):
    def __init__(self, x: float, y: float, robot_id: int, msg_id: int, last_robot_id: int):
        super().__init__(x, y, robot_id, msg_id, last_robot_id)
        self.color = [150, 255, 50, 100]

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
        self.broadcast_buffer = []

        self.destination_x = random.randint(100, 500)
        self.destination_y = random.randint(100, 500)

        self.swarm_state = []
        for i in range(SWARM_SIZE):
            self.swarm_state.append(
                RobotState(gps_location=(0, 0), last_message_id=-1, status="ready", battery=1.0)
            )

    def tick(self):
        dist = distance(self, (self.destination_x, self.destination_y))
        if dist > 2.5:
            self.x += (self.destination_x - self.x) / dist * 2
            self.y += (self.destination_y - self.y) / dist * 2

        # If the robot is close enough to the destination, set a new destination
        if dist < 2.5:
            self.destination_x = random.randint(100, 500)
            self.destination_y = random.randint(100, 500)
        
        # Broadcast all messages in buffer after delay
        for bc in self.broadcast_buffer:
            if bc.delay > 0:
                bc.delay -= 1
            else:
                # Set position to the robot's position
                bc.x = self.x
                bc.y = self.y
                Broadcast.all_broadcasts.update({bc.id: bc})
                self.broadcast_buffer.remove(bc)

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
        
        new_bc = GPSBroadcast(self.x, self.y, robot_id, msg_id, self.id, location)
        self.broadcast_buffer.append(new_bc)
        # Make delay based on distance
        delay = 20 * (1 - distance(self, all_robots[robot_id]) / BROADCAST_RANGE)
        new_bc.delay = delay
        return new_bc

        # return GPSBroadcast(self.x, self.y, robot_id, msg_id, self.id, location)

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

        # Suppress message if it is in buffer
        indices_to_remove = []
        for i, bc in enumerate(self.broadcast_buffer):
            if bc.msg_id == message.msg_id:
                print("SUPPRESSING")
                indices_to_remove.append(i)
        
        for i in indices_to_remove:
            self.broadcast_buffer.pop(i)

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
    if distance(other, source) < BROADCAST_RANGE * 0.8:     # Multiplied by 0.8 for padding factor
        return False
    
    # If other is too far away, don't bother
    if distance(this, other) > BROADCAST_RANGE * 1.2:
        return False
    
    return True

def is_bridge(this: Robot, source: Robot):
    for robot in all_robots:
        if robot.id != this.id:
            if bridges(this, robot, source):
                return True
            
    return False