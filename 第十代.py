import pygame
import sys
import random
import socket
import threading
import pickle
import struct
import time
import traceback
import select
import queue

# 游戏配置
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# 服务器配置
SERVER_IP = 'cn-bj-1.govfrp.com'
SERVER_PORT = 64702

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
CONNECTION_COLORS = [(100, 255, 100), (255, 255, 0), (255, 100, 100)]
UI_BUTTON_COLOR = (80, 80, 120, 180)
UI_BUTTON_HOVER = (100, 100, 150, 200)
UI_BUTTON_ACTIVE = (120, 120, 180, 220)

class Player:
    def __init__(self, x, y, player_id=None, is_local=False, name=None):
        self.rect = pygame.Rect(x, y, 40, 60)
        self.color = PLAYER_COLOR if is_local else OTHER_PLAYER_COLOR
        self.speed = 5
        self.jump_power = -18
        self.velocity_y = 0
        self.on_ground = False
        self.lives = 3
        self.player_id = str(player_id) if player_id else None
        self.is_local = is_local
        self.skills = {
            'high_jump': {'cooldown': 0, 'max_cooldown': 60, 'active': False}
        }
        self.jump_buffer = 0
        self.coyote_time = 0
        self.last_update = time.time()
        self.name = name if name else f"玩家{random.randint(1, 99)}"
        self.last_position = (x, y)
    
    def update(self, keys, ground, walls, left_pressed=False, right_pressed=False):
        if not self.is_local:
            return
            
        # 保存当前位置用于插值
        self.last_position = (self.rect.x, self.rect.y)
        
        # 处理跳跃缓冲
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
        
        # 处理边缘跳跃时间
        if self.on_ground:
            self.coyote_time = 10
        elif self.coyote_time > 0:
            self.coyote_time -= 1
        
        # 水平移动 - 支持键盘和UI按钮
        if keys[pygame.K_LEFT] or left_pressed:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or right_pressed:
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
            
            id_text = font.render(f"ID:{self.player_id[:8]}", True, WHITE)
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

class UIButton:
    """用于屏幕控制按钮的类（左、右、跳跃）"""
    def __init__(self, x, y, width, height, button_type):
        self.rect = pygame.Rect(x, y, width, height)
        self.button_type = button_type  # 'left', 'right', 'jump'
        self.pressed = False
        self.radius = min(width, height) // 2
    
    def draw(self, screen):
        # 创建半透明表面
        button_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # 根据按钮状态选择颜色
        if self.pressed:
            color = UI_BUTTON_ACTIVE
        else:
            color = UI_BUTTON_COLOR
        
        # 绘制圆形按钮
        pygame.draw.circle(button_surface, color, (self.radius, self.radius), self.radius)
        
        # 绘制按钮图标
        if self.button_type == 'left':
            # 左箭头
            pygame.draw.polygon(button_surface, WHITE, [
                (self.radius + 10, self.radius - 8),
                (self.radius - 10, self.radius),
                (self.radius + 10, self.radius + 8)
            ])
        elif self.button_type == 'right':
            # 右箭头
            pygame.draw.polygon(button_surface, WHITE, [
                (self.radius - 10, self.radius - 8),
                (self.radius + 10, self.radius),
                (self.radius - 10, self.radius + 8)
            ])
        elif self.button_type == 'jump':
            # 跳跃图标（向上的箭头）
            pygame.draw.polygon(button_surface, WHITE, [
                (self.radius, self.radius - 10),
                (self.radius - 8, self.radius + 5),
                (self.radius + 8, self.radius + 5)
            ])
        
        screen.blit(button_surface, self.rect)

class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.client_socket = None
        self.server_connected = False
        self.receive_thread = None
        self.heartbeat_thread = None
        self.last_receive_time = 0
        self.message_queue = queue.Queue()
        self.ping = 0
        self.ping_samples = []
        self.last_ping_time = 0
        self.send_interval = 0.1  # 100ms发送间隔
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 3  # 重连延迟（秒）
    
    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(3.0)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.server_connected = True
            self.last_receive_time = time.time()
            self.reconnect_attempts = 0
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self.receive_server_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 启动心跳线程
            self.heartbeat_thread = threading.Thread(target=self.send_heartbeats)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            print("已连接到服务器")
            return True
        except socket.timeout:
            print("连接服务器超时")
            return False
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False
    
    def reconnect(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        self.reconnect_attempts += 1
        if self.reconnect_attempts > self.max_reconnect_attempts:
            print(f"已达到最大重连次数({self.max_reconnect_attempts})，停止尝试")
            return False
        
        print(f"尝试重新连接({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
        time.sleep(self.reconnect_delay)
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(3.0)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            self.server_connected = True
            self.last_receive_time = time.time()
            
            # 重启接收线程
            self.receive_thread = threading.Thread(target=self.receive_server_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 重启心跳线程
            self.heartbeat_thread = threading.Thread(target=self.send_heartbeats)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            print("重新连接成功")
            self.reconnect_attempts = 0
            return True
        except Exception as e:
            print(f"重连失败: {e}")
            self.server_connected = False
            return False
    
    def receive_server_data(self):
        while self.game.running and self.server_connected:
            try:
                # 使用select检查socket状态
                readable, _, _ = select.select([self.client_socket], [], [], 1.0)  # 增加超时时间
                
                if readable:
                    # 接收数据长度
                    header = self.recvall(4)
                    if not header:
                        print("服务器断开连接，尝试重新连接...")
                        self.server_connected = self.reconnect()
                        if not self.server_connected:
                            break
                        continue
                    
                    length = struct.unpack('!I', header)[0]
                    data = self.recvall(length)
                    
                    if not data:
                        print("服务器断开连接，尝试重新连接...")
                        self.server_connected = self.reconnect()
                        if not self.server_connected:
                            break
                        continue
                    
                    # 记录接收时间
                    receive_time = time.time()
                    self.last_receive_time = receive_time
                    
                    try:
                        message = pickle.loads(data)
                    except Exception as e:
                        print(f"反序列化错误: {e}")
                        continue
                    
                    # 计算ping
                    if message.get('type') == 'pong':
                        self.ping = int((receive_time - message['timestamp']) * 1000)
                        self.ping_samples.append(self.ping)
                        if len(self.ping_samples) > 10:
                            self.ping_samples.pop(0)
                        continue
                    
                    # 将消息放入队列
                    self.message_queue.put(message)
                
                else:
                    # 检查连接超时 - 增加到25秒
                    if time.time() - self.last_receive_time > 25:
                        print("25秒内未收到服务器消息，尝试重新连接...")
                        self.server_connected = self.reconnect()
                        if not self.server_connected:
                            break
                        continue
                    
            except (ConnectionResetError, BrokenPipeError):
                print("连接被服务器重置，尝试重新连接...")
                self.server_connected = self.reconnect()
                if not self.server_connected:
                    break
                continue
            except socket.timeout:
                # 检查连接超时
                if time.time() - self.last_receive_time > 25:
                    print("25秒内未收到服务器消息，尝试重新连接...")
                    self.server_connected = self.reconnect()
                    if not self.server_connected:
                        break
                    continue
            except Exception as e:
                print(f"接收服务器数据错误: {e}")
                # 检查连接超时
                if time.time() - self.last_receive_time > 25:
                    print("25秒内未收到服务器消息，尝试重新连接...")
                    self.server_connected = self.reconnect()
                    if not self.server_connected:
                        break
                    continue
                time.sleep(0.1)
        
        print("接收线程结束")
        self.server_connected = False
    
    def recvall(self, length):
        data = bytearray()
        start_time = time.time()
        timeout = 5.0  # 设置5秒总超时
        
        while len(data) < length:
            try:
                # 设置每次接收超时
                self.client_socket.settimeout(2.0)
                packet = self.client_socket.recv(length - len(data))
                if not packet:
                    return None
                data.extend(packet)
                
                # 重置超时计时器
                start_time = time.time()
            except socket.timeout:
                # 检查总超时
                if time.time() - start_time > timeout:
                    print("接收数据包总超时")
                    return None
                continue
            except (ConnectionResetError, BrokenPipeError):
                return None
            except Exception as e:
                print(f"接收数据包时出错: {e}")
                return None
        
        return bytes(data)
    
    def send_data(self, data):
        if not self.server_connected:
            return False
        
        try:
            # 添加时间戳用于计算ping
            if data.get('type') == 'ping':
                data['timestamp'] = time.time()
            
            payload = pickle.dumps(data)
            self.client_socket.sendall(struct.pack('!I', len(payload)) + payload)
            return True
        except (ConnectionResetError, BrokenPipeError):
            print("连接中断，尝试重新连接...")
            self.server_connected = self.reconnect()
            return False
        except socket.timeout:
            print("发送数据超时")
            return False
        except Exception as e:
            print(f"发送数据失败: {e}")
            return False
    
    def send_heartbeats(self):
        while self.game.running and self.server_connected:
            try:
                # 发送ping请求
                if time.time() - self.last_ping_time > 2:
                    if self.send_data({'type': 'ping'}):
                        self.last_ping_time = time.time()
                
                time.sleep(0.5)
            except Exception as e:
                print(f"发送心跳失败: {e}")
                self.server_connected = self.reconnect()
    
    def process_messages(self):
        if not self.server_connected:
            return
        
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                msg_type = message.get('type')
                
                if msg_type == 'init':
                    self.handle_init_message(message)
                elif msg_type == 'player_update':
                    self.handle_player_update(message)
                elif msg_type == 'player_joined':
                    self.handle_player_joined(message)
                elif msg_type == 'player_left':
                    self.handle_player_left(message)
                elif msg_type == 'level':
                    self.handle_level_message(message)
                
            except queue.Empty:
                break
            except Exception as e:
                print(f"处理消息错误: {e}")
    
    def handle_init_message(self, message):
        # 服务器初始化数据
        self.game.player_id = str(message.get('id'))
        self.game.level = message.get('level', 1)
        
        # 初始化其他玩家
        players = message.get('players', {})
        for pid, pdata in players.items():
            pid = str(pid)
            if pid != self.game.player_id:
                self.game.other_players[pid] = Player(
                    pdata['x'], 
                    pdata['y'], 
                    pid, 
                    False, 
                    pdata.get('name')
                )
                self.game.other_players[pid].lives = pdata.get('lives', 3)
        
        # 更新关卡地图
        walls_data = message.get('walls', [])
        self.game.walls = []
        for wall in walls_data:
            self.game.walls.append(Wall(wall[0], wall[1], wall[2], wall[3]))
        
        # 更新怪物位置
        monster_pos = message.get('monster_pos', (400, 400))
        self.game.monster.rect.x = monster_pos[0]
        self.game.monster.rect.y = monster_pos[1]
    
    def handle_player_update(self, message):
        player_id = str(message['id'])
        if player_id != self.game.player_id:
            if player_id in self.game.other_players:
                # 更新现有玩家
                player = self.game.other_players[player_id]
                player.rect.x = message.get('x', player.rect.x)
                player.rect.y = message.get('y', player.rect.y)
                player.lives = message.get('lives', player.lives)
            else:
                # 添加新玩家
                print(f"新玩家加入: {player_id}")
                self.game.other_players[player_id] = Player(
                    message.get('x', 100),
                    message.get('y', 350),
                    player_id,
                    False,
                    message.get('name')
                )
    
    def handle_player_joined(self, message):
        player_id = str(message['id'])
        if player_id != self.game.player_id and player_id not in self.game.other_players:
            print(f"新玩家加入: {player_id}")
            self.game.other_players[player_id] = Player(
                message.get('x', 100),
                message.get('y', 350),
                player_id,
                False,
                message.get('name')
            )
    
    def handle_player_left(self, message):
        player_id = str(message['id'])
        if player_id in self.game.other_players:
            print(f"玩家离开: {player_id}")
            del self.game.other_players[player_id]
    
    def handle_level_message(self, message):
        # 服务器通知关卡更新
        new_level = message.get('level', 1)
        print(f"服务器通知: 进入第 {new_level} 关")
        self.game.level = new_level
        
        # 更新关卡地图
        walls_data = message.get('walls', [])
        self.game.walls = []
        for wall in walls_data:
            self.game.walls.append(Wall(wall[0], wall[1], wall[2], wall[3]))
        
        # 更新怪物位置
        monster_pos = message.get('monster_pos', (400, 400))
        self.game.monster.rect.x = monster_pos[0]
        self.game.monster.rect.y = monster_pos[1]
        
        # 重置玩家位置
        self.game.player.rect.x = 100
        self.game.player.rect.y = 350
        self.game.player.velocity_y = 0
        self.game.player.on_ground = True
        
        # 重置其他玩家位置
        for player in self.game.other_players.values():
            player.rect.x = 100
            player.rect.y = 350
        
        # 只有在多人游戏时才显示过关界面
        if self.game.is_multiplayer and self.server_connected:
            self.game.game_state = "next_level"
    
    def send_player_update(self):
        if not self.server_connected:
            return False
        
        player_data = {
            'type': 'player_update',
            'x': self.game.player.rect.x,
            'y': self.game.player.rect.y,
            'lives': self.game.player.lives,
            'name': self.game.player.name
        }
        return self.send_data(player_data)
    
    def send_level_update(self):
        if not self.server_connected:
            return False
        
        level_data = {
            'type': 'level',
            'level': self.game.level + 1
        }
        print(f"通知服务器: 请求进入第 {self.game.level + 1} 关")
        return self.send_data(level_data)
    
    def close(self):
        self.server_connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("多人平台游戏 - 可靠按钮控制版")
        
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
        self.game_state = "mode_selection"
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
        self.player_id = None
        self.other_players = {}
        self.network = NetworkManager(self)
        self.last_send_time = 0
        self.connection_lost = False
        
        # UI控制按钮
        self.ui_buttons = []
        self.left_pressed = False
        self.right_pressed = False
        self.jump_triggered = False
        
        # 按钮状态跟踪
        self.button_states = {
            'left': False,
            'right': False,
            'jump': False
        }
        
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
        
        # 重新连接按钮
        self.reconnect_button = Button(SCREEN_WIDTH//2 - 100, 300, 200, 50, "重新连接", self.reconnect_to_server)
        
        # UI控制按钮（左、右、跳跃）
        button_size = 70
        button_margin = 20
        button_y = SCREEN_HEIGHT - button_size - button_margin
        
        self.left_button = UIButton(button_margin, button_y, button_size, button_size, 'left')
        self.right_button = UIButton(button_margin + button_size + 20, button_y, button_size, button_size, 'right')
        self.jump_button = UIButton(SCREEN_WIDTH - button_size - button_margin, button_y, button_size, button_size, 'jump')
        
        self.ui_buttons = [self.left_button, self.right_button, self.jump_button]
    
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
        if not self.network.connect():
            # 连接失败时切换到单人模式
            self.is_multiplayer = False
            self.game_state = "playing"
            self.connection_lost = True
    
    def reconnect_to_server(self):
        if self.network.reconnect():
            self.connection_lost = False
            print("重新连接成功")
        else:
            print("重新连接失败")
    
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
        if not self.is_multiplayer or not self.network.server_connected:
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
        self.network.close()
        self.other_players = {}
        self.connection_lost = False
    
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
            
            # 连接丢失状态
            elif self.connection_lost:
                self.reconnect_button.check_hover(mouse_pos)
                if self.reconnect_button.handle_event(event):
                    return
            
            # 游戏内事件
            elif self.game_state == "playing":
                # 鼠标按下事件
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.left_button.rect.collidepoint(event.pos):
                        self.button_states['left'] = True
                    elif self.right_button.rect.collidepoint(event.pos):
                        self.button_states['right'] = True
                    elif self.jump_button.rect.collidepoint(event.pos):
                        self.button_states['jump'] = True
                        self.jump_triggered = True
                
                # 鼠标释放事件
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.button_states = {
                        'left': False,
                        'right': False,
                        'jump': False
                    }
                
                # 键盘事件
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1 and self.player.skills['high_jump']['cooldown'] == 0:
                        self.player.skills['high_jump']['active'] = True
                        self.player.skills['high_jump']['cooldown'] = self.player.skills['high_jump']['max_cooldown']
                    
                    # 跳跃缓冲
                    if event.key in [pygame.K_SPACE, pygame.K_UP]:
                        self.player.jump_buffer = 5
                    
                    # 手动重连快捷键
                    if event.key == pygame.K_r and not self.network.server_connected:
                        self.reconnect_to_server()
                
                if event.type == pygame.KEYUP:
                    # 短按跳跃 - 实现可变高度跳跃
                    if event.key in [pygame.K_SPACE, pygame.K_UP] and self.player.velocity_y < -5:
                        self.player.velocity_y = -5
    
    def update_button_states(self):
        """每帧更新按钮状态，支持同时按下多个按钮"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        # 如果鼠标左键按下，检查按钮状态
        if mouse_pressed[0]:
            # 左按钮状态
            if self.left_button.rect.collidepoint(mouse_pos):
                self.button_states['left'] = True
            else:
                self.button_states['left'] = False
                
            # 右按钮状态
            if self.right_button.rect.collidepoint(mouse_pos):
                self.button_states['right'] = True
            else:
                self.button_states['right'] = False
                
            # 跳跃按钮状态
            if self.jump_button.rect.collidepoint(mouse_pos):
                self.button_states['jump'] = True
            else:
                self.button_states['jump'] = False
        else:
            # 鼠标左键没有按下时，所有按钮都释放
            self.button_states = {
                'left': False,
                'right': False,
                'jump': False
            }
    
    def update(self):
        if self.game_state != "playing":
            return
        
        # 更新按钮状态
        self.update_button_states()
        
        # 设置移动状态
        self.left_pressed = self.button_states['left']
        self.right_pressed = self.button_states['right']
        
        # 更新按钮的pressed状态用于绘制
        self.left_button.pressed = self.left_pressed
        self.right_button.pressed = self.right_pressed
        self.jump_button.pressed = self.button_states['jump']
        
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.ground, self.walls, self.left_pressed, self.right_pressed)
        self.monster.update()
        
        # 处理跳跃触发
        if self.button_states['jump'] or self.jump_triggered:
            if self.player.on_ground or self.player.coyote_time > 0 or self.player.jump_buffer > 0:
                if self.player.skills['high_jump']['active']:
                    self.player.velocity_y = self.player.jump_power * 1.8
                    self.player.skills['high_jump']['active'] = False
                else:
                    self.player.velocity_y = self.player.jump_power
                self.player.on_ground = False
                self.player.coyote_time = 0
                self.player.jump_buffer = 0
            self.jump_triggered = False
        
        # 处理网络消息
        if self.is_multiplayer:
            self.network.process_messages()
            
            # 检查连接状态
            if not self.network.server_connected:
                self.connection_lost = True
        
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
            if not self.is_multiplayer or not self.network.server_connected:
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
                    self.network.send_level_update()
        
        # 定期发送玩家更新
        current_time = time.time()
        if self.is_multiplayer and self.network.server_connected and current_time - self.last_send_time > self.network.send_interval:
            if self.network.send_player_update():
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
            
            if not self.network.server_connected:
                status_text = self.small_font.render("服务器连接已断开", True, (255, 100, 100))
                self.screen.blit(status_text, (20, 380))
                
                # 显示重连提示
                reconnect_text = self.small_font.render("按R键尝试重新连接", True, (255, 200, 100))
                self.screen.blit(reconnect_text, (20, 410))
            else:
                # 显示网络状态
                ping = self.network.ping
                if self.network.ping_samples:
                    avg_ping = sum(self.network.ping_samples) // len(self.network.ping_samples)
                else:
                    avg_ping = ping
                
                # 根据延迟选择颜色
                if avg_ping < 100:
                    color_idx = 0
                elif avg_ping < 300:
                    color_idx = 1
                else:
                    color_idx = 2
                
                latency_text = self.small_font.render(f"延迟: {avg_ping}ms", True, CONNECTION_COLORS[color_idx])
                self.screen.blit(latency_text, (20, 410))
                
                # 连接质量
                if avg_ping < 100:
                    quality = "极佳"
                elif avg_ping < 200:
                    quality = "良好"
                elif avg_ping < 400:
                    quality = "一般"
                else:
                    quality = "较差"
                
                quality_text = self.small_font.render(f"网络质量: {quality}", True, CONNECTION_COLORS[color_idx])
                self.screen.blit(quality_text, (20, 440))
        
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
        
        # 绘制控制按钮（在游戏进行时显示）
        if self.game_state == "playing":
            for button in self.ui_buttons:
                button.draw(self.screen)
        
        # 绘制连接丢失界面
        if self.connection_lost:
            self.draw_connection_lost()
        
        # 绘制游戏状态界面
        if self.game_state == "mode_selection":
            self.draw_mode_selection()
        elif self.game_state == "game_over":
            self.draw_game_over()
        elif self.game_state == "next_level":
            self.draw_next_level()
    
    def draw_connection_lost(self):
        # 半透明覆盖层
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # 连接丢失文本
        title = self.font.render("连接已丢失", True, (255, 100, 100))
        reason = self.small_font.render("无法连接到服务器或连接中断", True, TEXT_COLOR)
        hint = self.small_font.render("请检查网络连接或稍后再试", True, (200, 200, 255))
        
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))
        self.screen.blit(reason, (SCREEN_WIDTH//2 - reason.get_width()//2, 200))
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 240))
        
        # 绘制重新连接按钮
        self.reconnect_button.draw(self.screen, self.font)
        
        # 返回菜单按钮
        back_button = Button(SCREEN_WIDTH//2 - 100, 370, 200, 50, "返回菜单", self.return_to_menu)
        back_button.draw(self.screen, self.font)
    
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
        self.network.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    client = Game()
    client.run()