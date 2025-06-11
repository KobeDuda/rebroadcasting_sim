import pygame
from robot import all_robots, Robot, RobotState, BROADCAST_RANGE, BROADCAST_LIFETIME, Broadcast, SWARM_SIZE, OPERATOR_X, OPERATOR_Y, GPSBroadcast, GreedyBroadcast, distance
import random

def draw_circle_alpha(surface, color, center, radius):
    target_rect = pygame.Rect(center, (0, 0)).inflate((radius * 2, radius * 2))
    shape_surf = pygame.Surface(target_rect.size, pygame.SRCALPHA)
    pygame.draw.circle(shape_surf, color, (radius, radius), radius)
    surface.blit(shape_surf, target_rect)

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True

# Represent the operator as a robot
all_robots.append(Robot(0, OPERATOR_X, OPERATOR_Y))

# Robot setup
for i in range(1, SWARM_SIZE):
    all_robots.append(Robot(i, random.randint(100, 500), random.randint(360-200, 360+200)))


tick = 0

selected_robot = None

while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # fill the screen with a color to wipe away anything from last frame
    screen.fill((50, 200, 130))

    # Draw a rectangle representing the area of the swarm
    pygame.draw.rect(screen, (30, 150, 90), pygame.Rect(90, 350-200, 420, 420))

    # RENDER YOUR GAME HERE
    for robot in all_robots:
        # Draw broadcast radius
        # Make radius white if robot is selected
        if robot.selected:
            draw_circle_alpha(screen, pygame.Color(255, 255, 255, 50), (robot.x, robot.y), BROADCAST_RANGE)
        else:
            draw_circle_alpha(screen, pygame.Color(130, 100, 200, 20), (robot.x, robot.y), BROADCAST_RANGE)
        robot.tick()

    for robot in all_robots:
        # Draw body
        # If robot is rebroadcasting a message, change color to green
        # If robot is pinged, change color to red
        pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(robot.x - 10, robot.y - 10, 20, 20))

        if robot.suppress_ping_timer > 0:
            # Draw a red circle around the robot
            pygame.draw.circle(screen, (255, 0, 0), (robot.x, robot.y), 18, 4)
        elif robot.rebroadcast_ping_timer > 0:
            # Draw a green circle around the robot
            pygame.draw.circle(screen, (0, 255, 0), (robot.x, robot.y), 20, 4)
        elif robot.ping_timer > 0:
            # Draw a blue circle around the robot
            pygame.draw.circle(screen, (0, 100, 255), (robot.x, robot.y), 22, 4)

        # If robot is the operator, color the robot's body gold
        if robot.id == 0:
            pygame.draw.rect(screen, (255, 255, 0), pygame.Rect(robot.x - 10, robot.y - 10, 20, 20))

        # If robot's broadcast buffer contains a message from the selected robot, color the robot's body blue
        if robot.broadcast_buffer and selected_robot != None:
            for broadcast in robot.broadcast_buffer:
                if broadcast.robot_id == selected_robot.id:
                    pygame.draw.rect(screen, (0, 100, 255), pygame.Rect(robot.x - 10, robot.y - 10, 20, 20))
                    break

    # Allow user to click and drag the selected robot
    if selected_robot is not None:
        if pygame.mouse.get_pressed()[0]:
            selected_robot.x = pygame.mouse.get_pos()[0]
            selected_robot.y = pygame.mouse.get_pos()[1]
        else:
            selected_robot = None
        
    # Select the robot closest to the mouse
    for robot in all_robots:
        robot.selected = False
        if distance(robot, (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])) < 30:
            selected_robot = robot
            robot.selected = True
            break

    # Draw a line from the robot to every other robot stored in the robot's swarm_state
    if selected_robot is not None:
        for other_robot in selected_robot.swarm_state:
            pygame.draw.line(screen, (255, 255, 255), (selected_robot.x, selected_robot.y), (other_robot.gps_location[0], other_robot.gps_location[1]), 2)
        for robot in all_robots:
            pygame.draw.line(screen, (0, 150, 255), (robot.x, robot.y), (robot.swarm_state[selected_robot.id].gps_location[0], robot.swarm_state[selected_robot.id].gps_location[1]), 2)

        # Draw a line from selected robot to every robot the robot is holding a broadcast for
        for broadcast in selected_robot.broadcast_buffer:
            pygame.draw.line(screen, (0, 220, 0), (selected_robot.x, selected_robot.y), (all_robots[broadcast.robot_id].x, all_robots[broadcast.robot_id].y), 2)

    # Draw a yellow highlight around the selected robot
    if selected_robot is not None:
        pygame.draw.rect(screen, (240, 220, 0), pygame.Rect(selected_robot.x - 12, selected_robot.y - 12, 24, 24), 5)

    # Run on positive edge of spacebar press
    if pygame.key.get_pressed()[pygame.K_SPACE] and not space_pressed:
        space_pressed = True
        for robot in all_robots:
            robot.broadcast_gps()

    if not pygame.key.get_pressed()[pygame.K_SPACE]:
        space_pressed = False

    tick += 1

    # Tick broadcasts
    keys_to_remove = []
    new_broadcasts = []
    for broadcast in Broadcast.all_broadcasts.values():
        broadcast.tick()

        draw_circle_alpha(screen, broadcast.color, (broadcast.x, broadcast.y), BROADCAST_RANGE * broadcast.age / BROADCAST_LIFETIME)
        if broadcast.age >= BROADCAST_LIFETIME:
            keys_to_remove.append(broadcast.id)

    for key in keys_to_remove:
        del Broadcast.all_broadcasts[key]
            
    for broadcast in new_broadcasts:
        if (isinstance(broadcast, Broadcast)):
            Broadcast.all_broadcasts.update({broadcast.id: broadcast})

    # flip() the display to put your work on screen
    pygame.display.flip()

    clock.tick(60)  # limits FPS to 60

pygame.quit()