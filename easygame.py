import pygame
import moviepy as mp
import os
import requests
from io import BytesIO

class GameEngine:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.background = None
        self.characters = []
        self.buttons = []
        self.music = None
        self.video = None
        self.video_playing = False
        self.running = True
        self.pygame = pygame  # 添加这行暴露pygame模块

    def BG(self, image_path):
        """设置背景图片"""
        self.background = pygame.image.load(image_path)
        self.background = pygame.transform.scale(self.background, (self.width, self.height))

    def Acont(self, image_path, x, y):
        """添加角色"""
        image = pygame.image.load(image_path)
        rect = image.get_rect()
        rect.x = x
        rect.y = y
        self.characters.append({'image': image, 'rect': rect})

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

    def play_video(self, video_path):
        """播放视频"""
        self.video = mp.VideoFileClip(video_path)
        self.video.preview()
        self.video_playing = True

    def check_collision(self, char1_index, char2_index):
        """检测两个角色是否碰撞"""
        rect1 = self.characters[char1_index]['rect']
        rect2 = self.characters[char2_index]['rect']
        return rect1.colliderect(rect2)

    def add_button(self, x, y, text, action=None, padding=20):
        """添加按钮，按钮大小根据文字自适应"""
        # 使用中文字体获取文字尺寸
        font = pygame.font.Font("simhei.ttf", 36)
        text_surf = font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect()
        
        # 计算按钮宽度和高度，加上内边距
        button_width = text_rect.width + 2 * padding
        button_height = text_rect.height + 2 * padding
        
        button = {
            'rect': pygame.Rect(x, y, button_width, button_height),
            'text': text,
            'action': action
        }
        self.buttons.append(button)

    def update(self):
        """更新游戏状态"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for button in self.buttons:
                    if button['rect'].collidepoint(mouse_pos) and button['action']:
                        button['action']()

        # 更新角色位置（如果有需要）
        keys = pygame.key.get_pressed()
        for char in self.characters:
                if keys[pygame.K_LEFT]:
                    char['rect'].x -= 5
                if keys[pygame.K_RIGHT]:
                    char['rect'].x += 5
                if keys[pygame.K_UP]:
                    char['rect'].y -= 5
                if keys[pygame.K_DOWN]:
                    char['rect'].y += 5

        # 绘制背景
        if self.background:
            self.screen.blit(self.background, (0, 0))

        # 绘制角色
        for char in self.characters:
            self.screen.blit(char['image'], char['rect'])

        # 绘制按钮
        for button in self.buttons:
            pygame.draw.rect(self.screen, (70, 70, 70), button['rect'])
            pygame.draw.rect(self.screen, (50, 50, 50), button['rect'], 2)
            
            # 使用中文字体
            font = pygame.font.Font("simhei.ttf", 36)
            text_surf = font.render(button['text'], True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)

        pygame.display.flip()
        self.clock.tick(60)

    def run(self):
        """运行游戏主循环"""
        while self.running:
            self.update()

        pygame.quit()

# 示例用法
"""
if __name__ == "__main__":
    # 初始化游戏引擎
    game = GameEngine(800, 600)

    # 设置背景
    game.BG("tuku/background.jpg")

    # 添加角色
    game.Acont("tuku/character1.png", 100, 100)
    game.Acont("tuku/character2.png", 300, 300)
    # 播放音乐

    
    # 添加按钮
    def on_button_click():
            music_url = "http://root/tuku/background_music.mp3"
            game.play_web_music(music_url)

    game.add_button(300, 200, "播放背景音乐", on_button_click)

    # 运行游戏
"""