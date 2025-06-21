# 第十代.py
import pygame
import sys
import random
import socket
import threading
import pickle
import struct
import time
import traceback

# 游戏配置
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# 服务器配置
SERVER_IP = '127.0.0.1'  # 更改为您的服务器IP
SERVER_PORT = 5555

# 颜色定义
BACKGROUND = (25, 25, 40)
WHITE = (255, 255, 255)
BLUE = (65, 105, 225)
PLAYER_COLOR = (30, 144, 255)
OTHER_PLAYER_COLOR = (50, 205, 50)
GREEN = (34, 139, 34)
RED = (220, 20, 60)
WALL_COLOR = (139, 69, 19)
GROUND_COLOR = (46, 139, 87)
MONSTER_COLOR = (178, 34, 34)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 149, 237)
TEXT_COLOR = (240, 248, 255)
BLACK = (0, 0, 0)
LEVEL_COLORS = [(65, 105, 225), (50, 205, 50), (220, 20, 60)]

class Player:
    def __init__(self, x, y, player_id=None, is_local=False, name=None):
        self.rect = pygame.Rect(x, y, 40, 60)
        self.color = PLAYER_COLOR if is_local else OTHER_PLAYER_COLOR
        self.speed = 5
        self.jump_power = -18
        self.velocity_y = 0
        self.on_ground = False
        self.lives = 3
        self.player_id = str(player_id) if player_id else None  # 确保ID是字符串
        self.is_local = is_local
        self.skills = {
            'high_jump': {'cooldown': 0, 'max_cooldown': 60, 'active': False}
        }
        self.jump_buffer = 0
        self.coyote_time = 0
        self.last_update = time.time()
        self.name = name if name else f"玩家{random.randint(1, 99)}"
    
    def update(self, keys, ground, walls):
        if not self.is_local:
            return
            
        # 处理跳跃缓冲
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
        
        # 处理边缘跳跃时间
        if self.on_ground:
            self.coyote_time = 10
        elif self.coyote_time > 0:
            self.coyote_time -= 1
        
        # 水平移动
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        
        # 应用重力
        self.velocity_y += 0.8
        self.rect.y += self.velocity_y
        
        # 重置地面状态
        self.on_ground = False
        
        # 地面碰撞检测
        if self.rect.bottom >= ground.rect.top:
            self.rect.bottom = ground.rect.top
            self.velocity_y = 0
            self.on_ground = True
        
        # 墙壁碰撞检测
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                # 从上方碰撞
                if self.velocity_y > 0 and abs(self.rect.bottom - wall.rect.top) < 20:
                    self.rect.bottom = wall.rect.top
                    self.velocity_y = 0
                    self.on_ground = True
                # 从下方碰撞
                elif self.velocity_y < 0 and abs(self.rect.top - wall.rect.bottom) < 10:
                    self.rect.top = wall.rect.bottom
                    self.velocity_y = 0
                # 从左侧碰撞
                elif self.rect.right > wall.rect.left and self.rect.centerx < wall.rect.centerx:
                    self.rect.right = wall.rect.left
                # 从右侧碰撞
                elif self.rect.left < wall.rect.right and self.rect.centerx > wall.rect.centerx:
                    self.rect.left = wall.rect.right
        
        # 边界检查
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        
        # 跳跃检测
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and (self.on_ground or self.coyote_time > 0 or self.jump_buffer > 0):
            if self.skills['high_jump']['active']:
                self.velocity_y = self.jump_power * 1.8
                self.skills['high_jump']['active'] = False
            else:
                self.velocity_y = self.jump_power
            self.on_ground = False
            self.coyote_time = 0
            self.jump_buffer = 0
    
    def draw(self, screen, font):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=8)
        
        # 绘制玩家信息
        if self.player_id:
            name_text = font.render(f"{self.name}", True, WHITE)
            screen.blit(name_text, (self.rect.centerx - name_text.get_width()//2, self.rect.top - 45))
            
            id_text = font.render(f"ID:{self.player_id[:8]}", True, WHITE)  # 只显示部分ID
            screen.blit(id_text, (self.rect.centerx - id_text.get_width()//2, self.rect.top - 25))

class Ground:
    def __init__(self, y, width, height):
        self.rect = pygame.Rect(0, y, width, height)
        self.color = GROUND_COLOR
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # 添加草地纹理
        for i in range(0, SCREEN_WIDTH, 20):
            pygame.draw.line(screen, (34, 177, 76), 
                            (i, self.rect.top), 
                            (i+10, self.rect.top - 10), 3)

class Wall:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = WALL_COLOR
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # 添加木纹效果
        pygame.draw.rect(screen, (101, 67, 33), self.rect, 2)
        for i in range(0, self.rect.height, 10):
            pygame.draw.line(screen, (101, 67, 33), 
                            (self.rect.left, self.rect.top + i),
                            (self.rect.right, self.rect.top + i), 1)

class Monster:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.color = MONSTER_COLOR
        self.speed = 2
        self.direction = 1
        self.move_area = {'left': 300, 'right': 500}
    
    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.move_area['left'] or self.rect.right >= self.move_area['right']:
            self.direction *= -1
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (139, 0, 0), self.rect, 2, border_radius=10)
        
        # 绘制眼睛
        eye_x = self.rect.left + 10 if self.direction == 1 else self.rect.right - 15
        pygame.draw.circle(screen, WHITE, (eye_x, self.rect.top + 15), 6)
        pygame.draw.circle(screen, BLACK, (eye_x, self.rect.top + 15), 3)

class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = BUTTON_COLOR
        self.text = text
        self.action = action
        self.hovered = False
    
    def draw(self, screen, font):
        color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (30, 70, 120), self.rect, 2, border_radius=10)
        
        text_surf = font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered and self.action:
                self.action()
                return True
        return False

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("多人平台游戏")
        
        self.clock = pygame.time.Clock()
        
        # 解决字体问题
        try:
            self.font = pygame.font.Font("simhei.ttf", 36)
            self.small_font = pygame.font.Font("simhei.ttf", 24)
        except:
            print("无法加载自定义字体，使用系统默认字体")
            self.font = pygame.font.SysFont(None, 36)
            self.small_font = pygame.font.SysFont(None, 24)
        
        # 游戏状态
        self.running = True
        self.game_state = "mode_selection"  # mode_selection, playing, next_level, game_over
        self.level = 1
        self.is_multiplayer = False
        self.score = 0
        
        # 游戏对象
        self.player = None
        self.ground = None
        self.walls = []
        self.monster = None
        self.buttons = []
        
        # 多人游戏
        self.client_socket = None
        self.player_id = None
        self.other_players = {}  # 存储其他玩家实体
        self.receive_thread = None
        self.heartbeat_thread = None
        self.last_send_time = 0
        self.server_connected = False
        
        # 初始化游戏对象
        self.init_game_objects()
        
        # 创建UI按钮
        self.create_buttons()
    
    def init_game_objects(self):
        # 创建地面
        self.ground = Ground(500, SCREEN_WIDTH, 100)
        
        # 创建玩家
        self.player = Player(100, 350, self.player_id, True)
        
        # 初始化墙壁和怪物
        self.walls = [
            Wall(300, 350, 100, 150),
            Wall(600, 220, 100, 280),
            Wall(135, 410, 100, 90),
            Wall(450, 300, 100, 20)
        ]
        
        # 创建怪物
        self.monster = Monster(400, 400)
    
    def create_buttons(self):
        # 模式选择按钮
        self.mode_buttons = [
            Button(SCREEN_WIDTH//2 - 100, 250, 200, 50, "单人游戏", self.start_single_player),
            Button(SCREEN_WIDTH//2 - 100, 320, 200, 50, "多人游戏", self.start_multiplayer)
        ]
        
        # 游戏结束按钮
        self.game_over_buttons = [
            Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "重新开始", self.reset_game),
            Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "返回菜单", self.return_to_menu)
        ]
        
        # 下一关按钮
        self.next_level_buttons = [
            Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "下一关", self.next_game_level),
            Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "返回菜单", self.return_to_menu)
        ]
    
    def start_single_player(self):
        self.is_multiplayer = False
        self.player = Player(100, 350, None, True)
        self.game_state = "playing"
        print("开始单人游戏")
    
    def start_multiplayer(self):
        self.is_multiplayer = True
        self.game_state = "playing"
        print(f"开始多人游戏")
        
        # 连接到服务器
        self.connect_to_server()
    
    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # 设置连接超时
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.server_connected = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self.receive_server_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 启动心跳线程
            self.heartbeat_thread = threading.Thread(target=self.send_heartbeats)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            print("已连接到服务器")
        except Exception as e:
            print(f"连接服务器失败: {e}")
            self.server_connected = False
            self.is_multiplayer = False
    
    def receive_server_data(self):
        while self.running and self.server_connected:
            try:
                data = self.recv_data(self.client_socket)
                if not data:
                    print("服务器断开连接")
                    self.server_connected = False
                    break
                    
                try:
                    message = pickle.loads(data)
                except Exception as e:
                    print(f"反序列化错误: {e}")
                    continue
                    
                msg_type = message.get('type')
                
                if msg_type == 'init':
                    # 服务器初始化数据
                    self.player_id = str(message.get('id'))  # 确保ID是字符串
                    self.level = message.get('level', 1)
                    
                    # 初始化其他玩家
                    players = message.get('players', {})
                    for pid, pdata in players.items():
                        pid = str(pid)  # 确保ID是字符串
                        if pid != self.player_id:
                            self.other_players[pid] = Player(
                                pdata['x'], 
                                pdata['y'], 
                                pid, 
                                False, 
                                pdata.get('name')
                            )
                            self.other_players[pid].lives = pdata.get('lives', 3)
                    
                    # 更新关卡地图
                    walls_data = message.get('walls', [])
                    self.walls = []
                    for wall in walls_data:
                        self.walls.append(Wall(wall[0], wall[1], wall[2], wall[3]))
                    
                    # 更新怪物位置
                    monster_pos = message.get('monster_pos', (400, 400))
                    self.monster.rect.x = monster_pos[0]
                    self.monster.rect.y = monster_pos[1]
                
                elif msg_type == 'player_update':
                    player_id = str(message['id'])  # 确保ID是字符串
                    if player_id != self.player_id:
                        if player_id in self.other_players:
                            # 更新现有玩家
                            player = self.other_players[player_id]
                            player.rect.x = message.get('x', player.rect.x)
                            player.rect.y = message.get('y', player.rect.y)
                            player.lives = message.get('lives', player.lives)
                        else:
                            # 添加新玩家
                            print(f"新玩家加入: {player_id}")
                            self.other_players[player_id] = Player(
                                message.get('x', 100),
                                message.get('y', 350),
                                player_id,
                                False,
                                message.get('name')
                            )
                
                elif msg_type == 'player_joined':
                    player_id = str(message['id'])  # 确保ID是字符串
                    if player_id != self.player_id and player_id not in self.other_players:
                        print(f"新玩家加入: {player_id}")
                        self.other_players[player_id] = Player(
                            message.get('x', 100),
                            message.get('y', 350),
                            player_id,
                            False,
                            message.get('name')
                        )
                
                elif msg_type == 'player_left':
                    player_id = str(message['id'])  # 确保ID是字符串
                    if player_id in self.other_players:
                        print(f"玩家离开: {player_id}")
                        del self.other_players[player_id]
                
                elif msg_type == 'level':
                    # 服务器通知关卡更新
                    new_level = message.get('level', 1)
                    print(f"服务器通知: 进入第 {new_level} 关")
                    self.level = new_level
                    
                    # 更新关卡地图
                    walls_data = message.get('walls', [])
                    self.walls = []
                    for wall in walls_data:
                        self.walls.append(Wall(wall[0], wall[1], wall[2], wall[3]))
                    
                    # 更新怪物位置
                    monster_pos = message.get('monster_pos', (400, 400))
                    self.monster.rect.x = monster_pos[0]
                    self.monster.rect.y = monster_pos[1]
                    
                    # 重置玩家位置
                    self.player.rect.x = 100
                    self.player.rect.y = 350
                    self.player.velocity_y = 0
                    self.player.on_ground = True
                    
                    # 重置其他玩家位置
                    for player in self.other_players.values():
                        player.rect.x = 100
                        player.rect.y = 350
                    
                    # 只有在多人游戏时才显示过关界面
                    if self.is_multiplayer and self.server_connected:
                        self.game_state = "next_level"
                
            except (ConnectionResetError, BrokenPipeError):
                print("连接被服务器重置")
                self.server_connected = False
                break
            except Exception as e:
                print(f"接收服务器数据错误: {e}")
                # 不要立即断开，尝试继续接收
                time.sleep(0.1)
    
    def send_player_update(self):
        if not self.server_connected or not self.is_multiplayer:
            return
        
        try:
            player_data = {
                'type': 'player_update',
                'x': self.player.rect.x,
                'y': self.player.rect.y,
                'lives': self.player.lives,
                'name': self.player.name
            }
            self.send_data(self.client_socket, player_data)
        except (ConnectionResetError, BrokenPipeError):
            print("连接中断，无法发送更新")
            self.server_connected = False
        except Exception as e:
            print(f"发送玩家更新失败: {e}")
    
    def send_heartbeats(self):
        while self.running and self.server_connected:
            try:
                heartbeat = {'type': 'heartbeat'}
                self.send_data(self.client_socket, heartbeat)
                time.sleep(5)  # 每5秒发送一次心跳
            except (ConnectionResetError, BrokenPipeError):
                print("连接中断，无法发送心跳")
                self.server_connected = False
                break
            except Exception as e:
                print(f"发送心跳失败: {e}")
                self.server_connected = False
                break
    
    def send_level_update(self):
        if not self.server_connected or not self.is_multiplayer:
            return
        
        try:
            level_data = {
                'type': 'level',
                'level': self.level + 1
            }
            self.send_data(self.client_socket, level_data)
            print(f"通知服务器: 请求进入第 {self.level + 1} 关")
        except (ConnectionResetError, BrokenPipeError):
            print("连接中断，无法发送关卡更新")
            self.server_connected = False
        except Exception as e:
            print(f"发送关卡更新失败: {e}")
    
    def send_data(self, sock, data):
        try:
            payload = pickle.dumps(data)
            sock.sendall(struct.pack('!I', len(payload)) + payload)
        except (ConnectionResetError, BrokenPipeError):
            raise
        except Exception as e:
            print(f"发送数据失败: {e}")
    
    def recv_data(self, sock):
        try:
            header = self.recvall(sock, 4)
            if not header:
                return None
            length = struct.unpack('!I', header)[0]
            return self.recvall(sock, length)
        except (ConnectionResetError, BrokenPipeError):
            return None
        except Exception as e:
            print(f"接收数据错误: {e}")
            return None
    
    def recvall(self, sock, length):
        data = bytearray()
        while len(data) < length:
            try:
                packet = sock.recv(length - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (ConnectionResetError, BrokenPipeError):
                return None
            except Exception as e:
                print(f"接收数据包时出错: {e}")
                return None
        return bytes(data)
    
    def reset_game(self):
        self.level = 1
        self.score = 0
        self.player = Player(100, 350, self.player_id, True)
        self.game_state = "playing"
        print("游戏重置")
        
        # 重置其他玩家
        self.other_players = {}
    
    def next_game_level(self):
        # 只在单人模式下增加关卡
        if not self.is_multiplayer or not self.server_connected:
            self.level += 1
        
        # 重置玩家位置
        self.player.rect.x = 100
        self.player.rect.y = 350
        self.player.velocity_y = 0
        self.player.on_ground = True
        
        # 设置游戏状态
        self.game_state = "playing"
        print(f"进入第 {self.level} 关")
    
    def return_to_menu(self):
        self.level = 1
        self.score = 0
        self.player = Player(100, 350, self.player_id, True)
        self.game_state = "mode_selection"
        print("返回主菜单")
        
        # 断开服务器连接
        if self.server_connected:
            try:
                self.client_socket.close()
            except:
                pass
            self.server_connected = False
            self.other_players = {}
    
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # 按钮事件处理
            if self.game_state == "mode_selection":
                for button in self.mode_buttons:
                    button.check_hover(mouse_pos)
                    if button.handle_event(event):
                        return
            
            elif self.game_state == "game_over":
                for button in self.game_over_buttons:
                    button.check_hover(mouse_pos)
                    if button.handle_event(event):
                        return
            
            elif self.game_state == "next_level":
                for button in self.next_level_buttons:
                    button.check_hover(mouse_pos)
                    if button.handle_event(event):
                        return
            
            # 游戏内事件
            elif self.game_state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 and self.player.skills['high_jump']['cooldown'] == 0:
                        self.player.skills['high_jump']['active'] = True
                        self.player.skills['high_jump']['cooldown'] = self.player.skills['high_jump']['max_cooldown']
                    
                    # 跳跃缓冲
                    if event.key in [pygame.K_SPACE, pygame.K_UP]:
                        self.player.jump_buffer = 5
                
                if event.type == pygame.KEYUP:
                    # 短按跳跃 - 实现可变高度跳跃
                    if event.key in [pygame.K_SPACE, pygame.K_UP] and self.player.velocity_y < -5:
                        self.player.velocity_y = -5
    
    def update(self):
        if self.game_state != "playing":
            return
        
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.ground, self.walls)
        self.monster.update()
        
        # 技能冷却
        if self.player.skills['high_jump']['cooldown'] > 0:
            self.player.skills['high_jump']['cooldown'] -= 1
        
        # 怪物碰撞检测
        if self.player.rect.colliderect(self.monster.rect):
            self.player.lives -= 1
            self.player.rect.x = 100
            self.player.rect.y = 300
            self.player.velocity_y = 0
            self.player.on_ground = True
            
            if self.player.lives <= 0:
                self.game_state = "game_over"
        
        # 过关检测
        if self.player.rect.x >= SCREEN_WIDTH - 50:
            self.score += 10
            
            # 单人模式直接进入下一关
            if not self.is_multiplayer or not self.server_connected:
                self.level += 1
                self.player.rect.x = 100
                self.player.rect.y = 350
                self.player.velocity_y = 0
                self.player.on_ground = True
                print(f"进入第 {self.level} 关")
            else:
                # 多人游戏只发送一次关卡更新请求
                if self.game_state != "next_level":
                    self.game_state = "next_level"
                    self.send_level_update()
        
        # 定期发送玩家更新
        current_time = time.time()
        if self.is_multiplayer and self.server_connected and current_time - self.last_send_time > 0.05:
            self.send_player_update()
            self.last_send_time = current_time
    
    def draw(self):
        self.screen.fill(BACKGROUND)
        
        # 绘制背景装饰
        for i in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, (50, 50, 70), (i, 0), (i, SCREEN_HEIGHT), 1)
        for i in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, (50, 50, 70), (0, i), (SCREEN_WIDTH, i), 1)
        
        # 绘制云朵
        for i, pos in enumerate([(100, 80), (400, 120), (650, 60)]):
            pygame.draw.ellipse(self.screen, (200, 220, 240), 
                               (pos[0], pos[1], 80, 40))
            pygame.draw.ellipse(self.screen, (200, 220, 240), 
                               (pos[0]+20, pos[1]-20, 70, 40))
            pygame.draw.ellipse(self.screen, (200, 220, 240), 
                               (pos[0]+40, pos[1]+10, 60, 30))
        
        # 绘制游戏对象
        self.ground.draw(self.screen)
        for wall in self.walls:
            wall.draw(self.screen)
        self.monster.draw(self.screen)
        
        # 绘制其他玩家实体
        for player in self.other_players.values():
            player.draw(self.screen, self.small_font)
        
        self.player.draw(self.screen, self.small_font)
        
        # 绘制UI信息
        lives_text = self.font.render(f"生命: {self.player.lives}", True, TEXT_COLOR)
        level_text = self.font.render(f"关卡: {self.level}", True, LEVEL_COLORS[(self.level-1) % len(LEVEL_COLORS)])
        score_text = self.font.render(f"分数: {self.score}", True, TEXT_COLOR)
        
        self.screen.blit(lives_text, (20, 20))
        self.screen.blit(level_text, (20, 60))
        self.screen.blit(score_text, (20, 100))
        
        # 多人游戏状态
        if self.is_multiplayer:
            players_count = len(self.other_players) + 1
            players_text = self.small_font.render(f"在线玩家: {players_count}", True, (100, 255, 100))
            self.screen.blit(players_text, (20, 350))
            
            if not self.server_connected:
                status_text = self.small_font.render("服务器连接已断开", True, (255, 100, 100))
                self.screen.blit(status_text, (20, 380))
        
        # 技能状态
        if self.player.skills['high_jump']['cooldown'] > 0:
            cooldown_text = self.small_font.render(f"高跳冷却: {self.player.skills['high_jump']['cooldown']//10}", True, (255, 200, 0))
            self.screen.blit(cooldown_text, (20, 140))
        else:
            skill_text = self.small_font.render("按1键激活高跳技能", True, (100, 255, 100))
            self.screen.blit(skill_text, (20, 140))
        
        # 跳跃提示
        jump_tip = self.small_font.render("按空格键或↑键跳跃", True, (200, 200, 100))
        self.screen.blit(jump_tip, (20, 320))
        
        # 终点旗帜
        pygame.draw.rect(self.screen, (220, 20, 60), (SCREEN_WIDTH - 60, 300, 10, 200))
        pygame.draw.polygon(self.screen, (30, 200, 30), [
            (SCREEN_WIDTH - 60, 300),
            (SCREEN_WIDTH - 60, 340),
            (SCREEN_WIDTH - 20, 320)
        ])
        
        # 绘制游戏状态界面
        if self.game_state == "mode_selection":
            self.draw_mode_selection()
        elif self.game_state == "game_over":
            self.draw_game_over()
        elif self.game_state == "next_level":
            self.draw_next_level()
    
    def draw_mode_selection(self):
        # 半透明覆盖层
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # 标题
        title = self.font.render("多人平台游戏", True, TEXT_COLOR)
        subtitle = self.small_font.render("选择游戏模式", True, (200, 200, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 200))
        
        # 服务器状态
        server_info = self.small_font.render(f"服务器: {SERVER_IP}:{SERVER_PORT}", True, (150, 200, 255))
        self.screen.blit(server_info, (SCREEN_WIDTH//2 - server_info.get_width()//2, 400))
        
        # 绘制按钮
        for button in self.mode_buttons:
            button.draw(self.screen, self.font)
    
    def draw_game_over(self):
        # 半透明覆盖层
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # 游戏结束文本
        title = self.font.render("游戏结束", True, (255, 100, 100))
        score_text = self.font.render(f"最终分数: {self.score}", True, TEXT_COLOR)
        level_text = self.font.render(f"到达关卡: {self.level}", True, TEXT_COLOR)
        
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 200))
        self.screen.blit(level_text, (SCREEN_WIDTH//2 - level_text.get_width()//2, 240))
        
        # 绘制按钮
        for button in self.game_over_buttons:
            button.draw(self.screen, self.font)
    
    def draw_next_level(self):
        # 半透明覆盖层
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # 过关文本
        title = self.font.render(f"第 {self.level} 关完成!", True, (100, 255, 100))
        score_text = self.font.render(f"获得分数: +10", True, TEXT_COLOR)
        next_text = self.font.render(f"即将进入第 {self.level+1} 关", True, TEXT_COLOR)
        
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, 200))
        self.screen.blit(next_text, (SCREEN_WIDTH//2 - next_text.get_width()//2, 240))
        
        # 玩家列表
        players_text = self.font.render("玩家列表:", True, (200, 200, 255))
        self.screen.blit(players_text, (SCREEN_WIDTH//2 - players_text.get_width()//2, 280))
        
        y_offset = 320
        # 绘制本地玩家
        player_info = self.small_font.render(f"{self.player.name} (你)", True, (200, 255, 200))
        self.screen.blit(player_info, (SCREEN_WIDTH//2 - player_info.get_width()//2, y_offset))
        y_offset += 30
        
        # 绘制其他玩家
        for player in self.other_players.values():
            player_info = self.small_font.render(f"{player.name} (ID:{player.player_id[:8]})", True, (200, 255, 200))
            self.screen.blit(player_info, (SCREEN_WIDTH//2 - player_info.get_width()//2, y_offset))
            y_offset += 30
        
        # 绘制按钮
        for button in self.next_level_buttons:
            button.draw(self.screen, self.font)
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # 清理资源
        if self.server_connected:
            try:
                self.client_socket.close()
            except:
                pass
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    client = Game()
    client.run()