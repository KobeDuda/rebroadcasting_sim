import pygame
from robot import all_robots, Robot, RobotState, BROADCAST_RANGE, BROADCAST_LIFETIME, Broadcast, SWARM_SIZE, OPERATOR_X, OPERATOR_Y
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

# Robot setup
for i in range(SWARM_SIZE):
    all_robots.append(Robot(i, 100, 360))

tick = 0

while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # fill the screen with a color to wipe away anything from last frame
    screen.fill((50, 200, 130))

    # RENDER YOUR GAME HERE
    for robot in all_robots:
        # Draw broadcast radius
        draw_circle_alpha(screen, pygame.Color(130, 100, 200, 20), (robot.x, robot.y), BROADCAST_RANGE)
        robot.tick()

    for robot in all_robots:
        # Draw body
        if robot.in_cds:
            # CDS robots are shown in blue
            pygame.draw.rect(screen, (100, 100, 255), pygame.Rect(robot.x - 10, robot.y - 10, 20, 20))
        else:
            # Non-CDS robots are shown in white
            pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(robot.x - 10, robot.y - 10, 20, 20))

        # Move towards destination

    pygame.draw.circle(screen, (200, 200, 200), (OPERATOR_X, OPERATOR_Y), 30)

    # TEST: Randomly spawn new broadcasts
    # Periodic GPS update
    if tick % 200 == 0:
        # Send CDS broadcasts to update the CDS
        for robot in all_robots:
            robot.broadcast_cds()

    if tick % 200 == 10:
        for robot in all_robots:
            robot.broadcast_gps()

    if tick % 240 == 0:
        robot = all_robots[random.randint(0, SWARM_SIZE - 1)]
        robot.broadcast_greedy()   

    tick += 1

    # Tick broadcasts
    keys_to_remove = []
    new_broadcasts = []
    for broadcast in Broadcast.all_broadcasts.values():
        to_add = broadcast.tick()
        for bc in to_add:
            new_broadcasts.append(bc)

        draw_circle_alpha(screen, broadcast.color, (broadcast.x, broadcast.y), BROADCAST_RANGE * broadcast.age / BROADCAST_LIFETIME)
        if broadcast.age == BROADCAST_LIFETIME:
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