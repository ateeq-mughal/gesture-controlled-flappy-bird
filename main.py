import cv2
import mediapipe as mp
import pygame
import random
import numpy as np

# ---------------- PYGAME SETUP ----------------
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Hand Flappy Bird")

clock = pygame.time.Clock()

# Load assets
bg = pygame.image.load("assets/images/bg.png").convert()
bird_img = pygame.image.load("assets/images/bird.png").convert_alpha()
pipe_img = pygame.image.load("assets/images/pipe.png").convert_alpha()
green_pipe_img = pygame.image.load("assets/images/greenpipe.png").convert_alpha()

bg_sound = pygame.mixer.Sound("assets/sounds/bg.mp3")
bg_sound.play(-1)  # Loop background music
flap_sound = pygame.mixer.Sound("assets/sounds/flap.wav")
score_sound = pygame.mixer.Sound("assets/sounds/score.wav")
gameover_sound = pygame.mixer.Sound("assets/sounds/gameover.wav")
turbo_sound = pygame.mixer.Sound("assets/sounds/turbo.wav")

turbo_sound_played = False
gameover_sound_played = False

# Scale
bird_img = pygame.transform.scale(bird_img, (40, 30))
pipe_img = pygame.transform.scale(pipe_img, (70, 400))
green_pipe_img = pygame.transform.scale(green_pipe_img, (70, 400))

font = pygame.font.SysFont("Arial", 32)

# Bird
bird_x = 100
bird_y = HEIGHT // 2
velocity = 0
gravity = 0.5

# Pipes
pipe_gap = 180
normal_pipe_speed = 5
turbo_pipe_speed = 10  # faster in turbo
pipes = []

score = 0
game_over = False
turbo_mode = False

# ---------------- MEDIAPIPE ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
cap = cv2.VideoCapture(0)

mp_draw = mp.solutions.drawing_utils


# Smooth control variables
smoothed_y = HEIGHT // 2
alpha = 0.15  # smoothing factor

# ---------------- FUNCTIONS ----------------
def spawn_pipe():
    height = random.randint(150, 400)
    pipes.append([WIDTH, height, False])  # third element = scored

def reset_game():
    global bird_y, velocity, pipes, score, game_over
    bird_y = HEIGHT // 2
    velocity = 0
    pipes.clear()
    spawn_pipe()
    score = 0
    game_over = False


def detect_turbo_gesture(frame_results):
    global turbo_mode
    global turbo_sound_played

    if frame_results and frame_results.multi_hand_landmarks:
        hand = frame_results.multi_hand_landmarks[0]

        fingers = [8,12,16,20]
        pips = [6,10,14,18]

        up = 0
        for f,p in zip(fingers,pips):
            if hand.landmark[f].y < hand.landmark[p].y:
                up += 1

        # TWO fingers → turbo
        if up == 2:
            turbo_mode = True
            if not turbo_sound_played:
                turbo_sound.play()
                turbo_sound_played = True
        else:
            turbo_mode = False
            turbo_sound_played = False



def detect_hand_control():
    global smoothed_y

    ret, frame = cap.read()
    if not ret:
        return None

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    detect_turbo_gesture(results)


    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]

        # Draw landmarks
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        palm_y = hand.landmark[9].y
        target_y = int(palm_y * HEIGHT)

        smoothed_y = int(alpha * target_y + (1 - alpha) * smoothed_y)

    # SHOW CAMERA WINDOW
    cv2.imshow("AI Hand Control", frame)
    cv2.waitKey(1)

    return smoothed_y


def detect_restart():
    global gameover_sound_played

    ret, frame = cap.read()
    if not ret:
        return False

    frame = cv2.flip(frame,1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        fingers = [8,12,16,20]
        pips = [6,10,14,18]

        up = 0
        for f,p in zip(fingers,pips):
            if hand.landmark[f].y < hand.landmark[p].y:
                up += 1

        if up >= 4:
            cv2.imshow("AI Hand Control", frame)
            cv2.waitKey(1)

            gameover_sound_played = False  # reset game over sound for next time
            return True

    return False

# ---------------- START ----------------

spawn_pipe()

running = True
while running:
    screen.blit(bg, (0,0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not game_over:
        hand_y = detect_hand_control()

        if hand_y:
            if turbo_mode:
                velocity = (hand_y - bird_y) * 0.26
            else:
                velocity = (hand_y - bird_y) * 0.08


        velocity += gravity
        bird_y += velocity

    # Draw bird
    screen.blit(bird_img, (bird_x, bird_y))

    # Pipes
    for pipe in pipes:
        if turbo_mode:
            pipe[0] -= turbo_pipe_speed
        else:
            pipe[0] -= normal_pipe_speed

        screen.blit(green_pipe_img, (pipe[0], pipe[1] - green_pipe_img.get_height()))
        screen.blit(pipe_img, (pipe[0], pipe[1] + pipe_gap))

        # Check if bird passed the pipe (and not scored yet)
        if not pipe[2] and bird_x > pipe[0] + 70:  # bird passed pipe
            score += 1
            pipe[2] = True
            score_sound.play()

        # Collision
        if bird_x + 40 > pipe[0] and bird_x < pipe[0] + 70:
            if bird_y < pipe[1] or bird_y > pipe[1] + pipe_gap:
                game_over = True
                pipes.clear()
                bird_y = HEIGHT // 2
                bird_x = 10
                if not gameover_sound_played:
                    gameover_sound.play()
                    gameover_sound_played = True


    pipes = [p for p in pipes if p[0] > -70]

    if len(pipes) == 0 or pipes[-1][0] < WIDTH - 250:
        if not game_over:
            spawn_pipe()

    # Ground / ceiling
    if bird_y < 0 or bird_y > HEIGHT:
        game_over = True
        gameover_sound.play()

    # Score
    score_text = font.render(str(score), True, (255,255,255))
    screen.blit(score_text, (WIDTH//2, 30))

    if turbo_mode:
        turbo_text = font.render("**TURBO**", True, (255,255,0))
        screen.blit(turbo_text, (WIDTH-150, 30))


    # Game Over
    if game_over:
        over = font.render("***GAME OVER***", True, (255,0,0))
        restart = font.render("Open Palm to Restart", True, (255,255,255))
        screen.blit(font.render(f"Score: {score}", True, (255,0,0)), (WIDTH//2 - 170, HEIGHT//2 - 80))
        screen.blit(font.render("Intelligent Cosumer Technologies", True, (255,0,0)), (WIDTH//2 - 170, HEIGHT//2 + 40))
        screen.blit(font.render("Ateeq Ur Rehman - 913901", True, (0,0,0)), (WIDTH//2 - 170, HEIGHT//2 + 80))
        screen.blit(font.render("Abdul Hadi - 920846", True, (0,0,0)), (WIDTH//2 - 170, HEIGHT//2 + 120))
        screen.blit(over, (WIDTH//2 - 170, HEIGHT//2 - 40))
        screen.blit(restart, (WIDTH//2 - 170, HEIGHT//2))

        if detect_restart():
            reset_game()

    pygame.display.update()
    clock.tick(30)

cap.release()
cv2.destroyAllWindows()
pygame.quit()
