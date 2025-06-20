import pygame
import sys
import random
import socket
import threading
import pickle
import struct
import time
import json
import os
from easygame import GameEngine
import requests
from io import BytesIO
"""第九代
  成功解决关卡问题"""


url = "http://localhost/vegest.json"
ves = 1.5
mp3 ="http://localhost/tuku/background_music.mp3"
ip = 'cn-bj-1.govfrp.com'
port = 64702



print("正在获取云端最新版本..")
try:
                # 发送 GET 请求
                response = requests.get(url)
                
                # 检查请求是否成功
                response.raise_for_status()  # 如果状态码不是 200，会抛出异常
                
                # 解析 JSON 数据
                data = response.json()
                
except requests.exceptions.RequestException as e:
                print(f"请求失败: {e}")
except ValueError as e:
                print(f"解析 JSON 失败: {e}")

ve = data["vecer"]
print(f"最新版本为'{ve}'")
print(f"你的版本为'{ves}'")
if ve == ves:
                print("版本正确")
                # 初始化 Pygame
                pygame.init()
                pygame.mixer.init()
                # 设置屏幕尺寸
                screen_width = 800
                screen_height = 600
                screen = pygame.display.set_mode((screen_width, screen_height))
                pygame.display.set_caption("2D 平台游戏")

                # 定义颜色
                WHITE = (255, 255, 255)
                BLUE = (0, 0, 255)
                GREEN = (0, 255, 0)
                RED = (255, 0, 0)
                BLACK = (0, 0, 0)

                # 创建玩家角色
                player = {
                    'rect': pygame.Rect(100, 350, 40, 60),
                    'color': BLUE,
                    'speed': 5,
                    'jump_power': -15,
                    'velocity_y': 0,
                    'on_ground': True,
                    'lives': 3,
                    'skills': {
                        'high_jump': {'cooldown': 0, 'max_cooldown': 60, 'active': False}
                    }
                }

                # 创建地面
                ground = {
                    'rect': pygame.Rect(0, 500, 800, 100),
                    'color': GREEN
                }

                # 创建墙壁
                walls = [
                    {'rect': pygame.Rect(300, 350, 100, 150), 'color': (150, 75, 0)},
                    {'rect': pygame.Rect(600, 220, 100, 280), 'color': (150, 75, 0)},
                    {'rect': pygame.Rect(135, 410, 100, 90), 'color': (150, 75, 0)},
                    {'rect': pygame.Rect(450, 300, 100, 20), 'color': (150, 75, 0)}
                ]

                # 创建怪物
                monster = {
                    'rect': pygame.Rect(400, 400, 40, 40),
                    'color': RED,
                    'speed': 3,
                    'direction': 1,
                    'move_area': {'left': 300, 'right': 500}
                }

                # 游戏主循环
                clock = pygame.time.Clock()
                running = True
                game_over = False
                next_level = False
                level = 1
                is_multiplayer = False
                player_id = None
                other_players = {}

                # 积分系统
                score = 99
                font_path = "simhei.ttf"
                score_font = pygame.font.Font(font_path, 36)

                # 联机模式变量
                client_socket = None
                # 添加按钮
                def play_web_music(self, music_url):
                    """从网络加载并播放音乐"""
                    try:
                        # 从网络获取音频数据
                        response = requests.get(music_url)
                        response.raise_for_status()  # 检查请求是否成功

                        # 将音频数据加载到内存中
                        audio_data = BytesIO(response.content)

                        # 使用 pygame 播放音频
                        pygame.mixer.music.load(audio_data)
                        pygame.mixer.music.play(-1)  # 循环播放

                        print(f"音乐已开始播放: {music_url}")
                    except requests.exceptions.RequestException as e:
                        print(f"网络请求失败: {e}")
                    except pygame.error as e:
                        print(f"pygame 播放失败: {e}")
                    except Exception as e:
                        print(f"播放音乐时出错: {e}")

                def draw_button(text, x, y, width, height, action=None):
                    mouse = pygame.mouse.get_pos()
                    click = pygame.mouse.get_pressed()
                    color = (100, 100, 100) if x < mouse[0] < x + width and y < mouse[1] < y + height else (70, 70, 70)
                    pygame.draw.rect(screen, color, (x, y, width, height))
                    if click[0] == 1 and action is not None:
                        action()
                    font = pygame.font.Font(font_path, 36)
                    text_surf = font.render(text, True, WHITE)
                    text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
                    screen.blit(text_surf, text_rect)

                # 重置游戏
                def reset_game():
                    global game_over, next_level, level, walls, monster, score, player, other_players, is_multiplayer
                    player['rect'].x = 100
                    player['rect'].y = 300
                    player['velocity_y'] = 0
                    player['on_ground'] = True
                    player['lives'] = 3
                    player['skills']['high_jump']['cooldown'] = 0
                    player['skills']['high_jump']['active'] = False
                    game_over = False
                    next_level = False
                    level = 1
                    score = 0
                    other_players = {}
                    is_multiplayer = False
                    walls = [
                        {'rect': pygame.Rect(300, 350, 100, 150), 'color': (150, 75, 0)},
                        {'rect': pygame.Rect(600, 220, 100, 280), 'color': (150, 75, 0)},
                        {'rect': pygame.Rect(135, 410, 100, 90), 'color': (150, 75, 0)},
                        {'rect': pygame.Rect(450, 300, 100, 20), 'color': (150, 75, 0)}
                    ]
                    monster['rect'].x = 400
                    monster['rect'].y = 400

                # 进入下一关
                def next_game_level():
                    global game_over, next_level, level, walls, monster
                    player['rect'].x = 100
                    player['rect'].y = 300
                    player['velocity_y'] = 0
                    player['on_ground'] = True
                    player['lives'] = 3
                    game_over = False
                    next_level = False  # 重置下一关标志

                    # 根据关卡设置不同的墙壁和怪物位置
                    if level == 2:
                        # 第2关
                        walls = [
                            {'rect': pygame.Rect(300, 350, 100, 150), 'color': (150, 75, 0)},  # 棕色墙壁，第一个
                            {'rect': pygame.Rect(600, 220, 100, 280), 'color': (150, 75, 0)},#第二个
                            {'rect': pygame.Rect(0, 340, 300, 20),'color': (150, 75, 0)},#第二个
                            {'rect': pygame.Rect(450, 300, 100, 20), 'color': (150, 75, 0)}#第四个
                        ]
                        monster['rect'].x = 400
                        monster['rect'].y = 400
                    elif level == 3:
                        # 第3关
                        walls = [
                            {'rect': pygame.Rect(200, 300, 100, 200), 'color': (150, 75, 0)},  # 新墙壁1
                            {'rect': pygame.Rect(500, 200, 100, 300), 'color': (150, 75, 0)},  # 新墙壁2
                            {'rect': pygame.Rect(100, 400, 100, 100), 'color': (150, 75, 0)},  # 新墙壁3
                        ]
                        monster['rect'].x = 300
                        monster['rect'].y = 400
                    elif level == 4:
                        # 第4关
                        walls = [
                            {'rect': pygame.Rect(150, 250, 100, 250), 'color': (150, 75, 0)},  # 新墙壁1
                            {'rect': pygame.Rect(400, 150, 100, 350), 'color': (150, 75, 0)},  # 新墙壁2
                            {'rect': pygame.Rect(650, 200, 100, 300), 'color': (150, 75, 0)},  # 新墙壁3
                        ]
                        monster['rect'].x = 200
                        monster['rect'].y = 400

                    # 确保玩家在地面或平台的下方
                    player['rect'].y = ground['rect'].y - player['rect'].height
                    player['on_ground'] = True

                # 定义技能函数
                def activate_high_jump():
                    player['skills']['high_jump']['active'] = True

                # 接收服务器数据
                def receive_server_data():
                    global client_socket, running, other_players, level, player_id
                    while running:
                        data = recv_data(client_socket)
                        if not data:
                            break
                        try:
                            received = pickle.loads(data)
                            if isinstance(received, dict) and 'type' in received:
                                if received['type'] == 'init':
                                    player_id = received['id']
                                    level = received.get('level', 1)
                                    print(f"收到初始化消息，客户端ID: {player_id}")
                                elif received.get('type') == 'level':
                                    level = received.get('level')
                                    next_game_level()
                                else:
                                    other_players[received.get('id', 'unknown')] = received
                        except Exception as e:
                            print(f"Error parsing data: {e}")

                # 发送玩家状态到服务器
                def send_player_state():
                    global client_socket, player, player_id, level
                    if client_socket:
                        player_data = {
                            'type': 'position',
                            'id': player_id,  # 使用自定义的 player_id
                            'rect': player['rect'],
                            'lives': player['lives'],
                            'score': score,
                            'level': level
                        }
                        send_data(client_socket, player_data)

                # 发送心跳包
                def send_heartbeat():
                    global client_socket, player_id
                    if client_socket and player_id:
                        heartbeat_data = {
                            'type': 'heartbeat',
                            'id': player_id
                        }
                        send_data(client_socket, heartbeat_data)

                # 初始化客户端
                def start_client():
                    global client_socket, player_id
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        client_socket.connect((ip, port))
                        receive_thread = threading.Thread(target=receive_server_data)
                        receive_thread.daemon = True
                        receive_thread.start()
                        # 启动心跳线程
                        heartbeat_thread = threading.Thread(target=send_regular_heartbeats)
                        heartbeat_thread.daemon = True
                        heartbeat_thread.start()
                        print("客户端已连接到服务器")
                    except Exception as e:
                        print(f"Error connecting to server: {e}")
                        client_socket.close()
                        client_socket = None

                def send_data(sock, data):
                    payload = pickle.dumps(data)
                    sock.sendall(struct.pack('!I', len(payload)) + payload)

                def recv_data(sock):
                    try:
                        header = recvall(sock, 4)
                        if not header:
                            return None
                        length = struct.unpack('!I', header)[0]
                        return recvall(sock, length)
                    except Exception:
                        return None

                def recvall(sock, length):
                    data = bytearray()
                    while len(data) < length:
                        packet = sock.recv(length - len(data))
                        if not packet:
                            return None
                        data.extend(packet)
                    return bytes(data)

                # 定期发送心跳包
                def send_regular_heartbeats():
                    while running:
                        send_heartbeat()
                        time.sleep(5)  # 每5秒发送一次心跳包

                # 启动游戏时选择单机或多人模式
                def start_single_player():
                    global is_multiplayer, client_socket
                    is_multiplayer = False
                    if client_socket:
                        client_socket.close()
                        client_socket = None

                
                def start_multiplayer():
                    global is_multiplayer, player_id
                    is_multiplayer = True
                    
                    # 提示玩家输入自定义 ID
                    player_id = 111

                    start_client()

                # 显示模式选择界面
                def show_mode_selection():
                    screen.fill(WHITE)
                    font = pygame.font.Font(font_path, 36)
                    title = font.render("选择游戏模式", True, BLACK)
                    screen.blit(title, (screen_width // 2 - title.get_width() // 2, 100))
                    draw_button("单机模式", 300, 200, 200, 50, start_single_player)
                    draw_button("多人模式", 300, 300, 200, 50, start_multiplayer)
                    pygame.display.flip()

                # 主循环
                def main_game_loop():
                    global running, game_over, next_level, level, walls, monster, score, player, other_players, is_multiplayer

                    show_mode_selection()

                    # 等待玩家选择模式
                    waiting_for_mode = True
                    while waiting_for_mode:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                running = False
                                return
                            elif event.type == pygame.MOUSEBUTTONDOWN:
                                mouse_pos = pygame.mouse.get_pos()
                                # 检查单机模式按钮
                                if 300 <= mouse_pos[0] <= 500 and 200 <= mouse_pos[1] <= 250:
                                    start_single_player()
                                    waiting_for_mode = False
                                # 检查多人模式按钮
                                elif 300 <= mouse_pos[0] <= 500 and 300 <= mouse_pos[1] <= 350:
                                    start_multiplayer()
                                    waiting_for_mode = False

                    while running:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                running = False
                            elif event.type == pygame.KEYDOWN:
                                if event.key == pygame.K_1 and player['skills']['high_jump']['cooldown'] == 0 and score >= 1:
                                    activate_high_jump()
                                    player['skills']['high_jump']['cooldown'] = player['skills']['high_jump']['max_cooldown']
                                    score -= 1

                        if not game_over and not next_level:
                            keys = pygame.key.get_pressed()
                            if keys[pygame.K_LEFT]:
                                player['rect'].x -= player['speed']
                            if keys[pygame.K_RIGHT]:
                                player['rect'].x += player['speed']
                            if keys[pygame.K_SPACE] and player['on_ground']:
                                if player['skills']['high_jump']['active']:
                                    player['velocity_y'] = player['jump_power'] * 1.5
                                    player['skills']['high_jump']['active'] = False
                                else:
                                    player['velocity_y'] = player['jump_power']
                                player['on_ground'] = False

                            if player['skills']['high_jump']['cooldown'] > 0:
                                player['skills']['high_jump']['cooldown'] -= 1

                            player['velocity_y'] += 1
                            player['rect'].y += player['velocity_y']

                            if player['rect'].y >= ground['rect'].y - player['rect'].height:
                                player['rect'].y = ground['rect'].y - player['rect'].height
                                player['velocity_y'] = 0
                                player['on_ground'] = True

                            for wall in walls:
                                if player['rect'].colliderect(wall['rect']):
                                    if player['rect'].right > wall['rect'].left and player['rect'].x < wall['rect'].x:
                                        player['rect'].right = wall['rect'].left
                                    elif player['rect'].x < wall['rect'].right and player['rect'].right > wall['rect'].right:
                                        player['rect'].x = wall['rect'].right
                                    elif player['rect'].bottom >= wall['rect'].top and player['rect'].y < wall['rect'].top:
                                        player['rect'].bottom = wall['rect'].top
                                        player['velocity_y'] = 0
                                        player['on_ground'] = True
                                    elif level == 3:
                                        if player['rect'].right >= wall['rect'].left and player['rect'].x < wall['rect'].x:
                                            player['rect'].right = wall['rect'].left
                                            player['velocity_y'] = 0
                                            player['on_ground'] = True
                                        elif player['rect'].x <= wall['rect'].right and player['rect'].right > wall['rect'].right:
                                            player['rect'].x = wall['rect'].right
                                            player['velocity_y'] = 0
                                            player['on_ground'] = True

                            # 检测玩家与其他玩家的碰撞（仅在多人模式下）
                            if is_multiplayer:
                                for pid, pdata in other_players.items():
                                    if pid != player_id and player['rect'].colliderect(pdata['rect']):
                                        if player['rect'].bottom >= pdata['rect'].top and player['rect'].y < pdata['rect'].top:
                                            player['rect'].bottom = pdata['rect'].top
                                            player['velocity_y'] = 0
                                            player['on_ground'] = True

                            monster['rect'].x += monster['speed'] * monster['direction']
                            if monster['rect'].x <= monster['move_area']['left'] or monster['rect'].x >= monster['move_area']['right']:
                                monster['direction'] *= -1

                            if player['rect'].colliderect(monster['rect']):
                                player['lives'] -= 1
                                player['rect'].x = 100
                                player['rect'].y = 300
                                player['velocity_y'] = 0
                                player['on_ground'] = True
                                if player['lives'] <= 0:
                                    game_over = True  # 设置游戏结束标志
                                player['rect'].y = ground['rect'].y - player['rect'].height
                                player['on_ground'] = True

                            if player['rect'].x >= screen_width:
                                score += 1
                                level += 1
                                next_level = True

                            screen.fill(WHITE)
                            pygame.draw.rect(screen, ground['color'], ground['rect'])
                            for wall in walls:
                                pygame.draw.rect(screen, wall['color'], wall['rect'])
                            pygame.draw.rect(screen, monster['color'], monster['rect'])
                            for pid, pdata in other_players.items():
                                if pid != player_id:
                                    pygame.draw.rect(screen, BLUE, pdata['rect'])

                            pygame.draw.rect(screen, player['color'], player['rect'])

                            # 在玩家角色头上显示 player_id
                            font = pygame.font.Font(font_path, 24)
                            #id_text = font.render(player_id, True, BLACK)
                            #screen.blit(id_text, (player['rect'].x + player['rect'].width // 2 - id_text.get_width() // 2, player['rect'].y - 25))

                            # 在其他玩家头上显示他们的 ID
                            

                            lives_text = font.render(f"生命值: {player['lives']}", True, BLACK)
                            level_text = font.render(f"关卡: {level}", True, BLACK)
                            screen.blit(lives_text, (10, 10))
                            screen.blit(level_text, (10, 50))

                            score_text = score_font.render(f"积分: {score}", True, BLACK)
                            screen.blit(score_text, (10, 100))

                            if is_multiplayer:
                                send_player_state()

                        # 在主循环
                        # 在主循环中
                        elif next_level:
                            screen.fill(WHITE)
                            font = pygame.font.Font(font_path, 36)
                            next_level_text = font.render(f"进入第 {level} 关", True, BLACK)
                            screen.blit(next_level_text, (150, 100))
                            # 修改按钮回调函数，确保在按下继续后正确处理状态
                            draw_button("继续", 300, 200, 200, 50, next_game_level)
                            draw_button("退出", 300, 300, 200, 50, sys.exit)
                            # 在此处添加一个变量来控制是否继续游戏主循环
                            continue_game = True
                            while continue_game:
                                for event in pygame.event.get():
                                    if event.type == pygame.QUIT:
                                        running = False
                                        continue_game = False
                                    elif event.type == pygame.MOUSEBUTTONDOWN:
                                        mouse_pos = pygame.mouse.get_pos()
                                        # 检查继续按钮
                                        if 300 <= mouse_pos[0] <= 500 and 200 <= mouse_pos[1] <= 250:
                                            next_game_level()
                                            continue_game = False
                                        # 检查退出按钮
                                        elif 300 <= mouse_pos[0] <= 500 and 300 <= mouse_pos[1] <= 350:
                                            pygame.quit()
                                            sys.exit()
                                pygame.display.flip()
                            # 重置 next_level 标志，继续游戏主循环
                            next_level = False

                        elif game_over:
                            screen.fill(WHITE)
                            font = pygame.font.Font(font_path, 36)
                            game_over_text = font.render("游戏结束", True, BLACK)
                            screen.blit(game_over_text, (250, 100))
                            draw_button("重新开始", 300, 200, 200, 50, reset_game)
                            draw_button("退出", 300, 300, 200, 50, sys.exit)
                            pygame.display.flip()
                            clock.tick(60)
                            continue  # 跳过主循环的其他部分

                        pygame.display.flip()
                        clock.tick(60)

                    pygame.quit()
                    sys.exit()

                if __name__ == "__main__":
                    music_url = mp3
                    game = GameEngine(800, 600)
                    game.play_web_music(music_url)
                    main_game_loop()
else:
                print("版本不正确，请去下载最新版本")
    