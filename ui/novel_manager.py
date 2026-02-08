# ui/novel_manager.py
# -*- coding: utf-8 -*-
"""
小说管理模块 - 用于管理创建的小说
提供小说的增删改查、分页、翻页等功能
"""
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk


class Novel:
    """小说数据模型"""
    def __init__(self, novel_id: str, title: str, description: str, 
                 cover_image: str = "", created_at: str = "", updated_at: str = "",
                 chapter_count: int = 0, generated_chapters: int = 0,
                 word_count: int = 0, tags: List[str] = None, status: str = "草稿",
                 save_path: str = "", topic: str = "", genre: str = "玄幻",
                 num_chapters: int = 10, word_number: int = 3000, chapter_num: int = 1,
                 user_guidance: str = "", characters_involved: str = "", key_items: str = "",
                 scene_location: str = "", time_constraint: str = ""):
        self.novel_id = novel_id
        self.title = title
        self.description = description
        self.cover_image = cover_image
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.chapter_count = chapter_count
        self.generated_chapters = generated_chapters
        self.word_count = word_count
        self.tags = tags or []
        self.status = status
        self.save_path = save_path
        # 小说参数
        self.topic = topic
        self.genre = genre
        self.num_chapters = num_chapters
        self.word_number = word_number
        self.chapter_num = chapter_num
        self.user_guidance = user_guidance
        self.characters_involved = characters_involved
        self.key_items = key_items
        self.scene_location = scene_location
        self.time_constraint = time_constraint

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "novel_id": self.novel_id,
            "title": self.title,
            "description": self.description,
            "cover_image": self.cover_image,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "chapter_count": self.chapter_count,
            "generated_chapters": self.generated_chapters,
            "word_count": self.word_count,
            "tags": self.tags,
            "status": self.status,
            "save_path": self.save_path,
            "topic": self.topic,
            "genre": self.genre,
            "num_chapters": self.num_chapters,
            "word_number": self.word_number,
            "chapter_num": self.chapter_num,
            "user_guidance": self.user_guidance,
            "characters_involved": self.characters_involved,
            "key_items": self.key_items,
            "scene_location": self.scene_location,
            "time_constraint": self.time_constraint
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Novel':
        """从字典创建Novel对象"""
        return cls(
            novel_id=data.get("novel_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            cover_image=data.get("cover_image", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            chapter_count=data.get("chapter_count", 0),
            generated_chapters=data.get("generated_chapters", 0),
            word_count=data.get("word_count", 0),
            tags=data.get("tags", []),
            status=data.get("status", "草稿"),
            save_path=data.get("save_path", ""),
            topic=data.get("topic", ""),
            genre=data.get("genre", "玄幻"),
            num_chapters=data.get("num_chapters", 10),
            word_number=data.get("word_number", 3000),
            chapter_num=data.get("chapter_num", 1),
            user_guidance=data.get("user_guidance", ""),
            characters_involved=data.get("characters_involved", ""),
            key_items=data.get("key_items", ""),
            scene_location=data.get("scene_location", ""),
            time_constraint=data.get("time_constraint", "")
        )

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NovelManager:
    """小说管理器 - 负责小说的增删改查和数据持久化"""
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.novels_dir = os.path.join(data_dir, "novels")
        self._ensure_directories()
        self._novels: Dict[str, Novel] = {}
        self._load_novels()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.novels_dir):
            os.makedirs(self.novels_dir)

    def _load_novels(self):
        """加载所有小说"""
        if not os.path.exists(self.novels_dir):
            return

        for novel_id in os.listdir(self.novels_dir):
            novel_path = os.path.join(self.novels_dir, novel_id)
            if os.path.isdir(novel_path):
                info_file = os.path.join(novel_path, "novel_info.json")
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self._novels[novel_id] = Novel.from_dict(data)
                    except Exception as e:
                        print(f"加载小说 {novel_id} 失败: {e}")

    def _save_novel(self, novel: Novel):
        """保存单个小说"""
        novel_path = os.path.join(self.novels_dir, novel.novel_id)
        if not os.path.exists(novel_path):
            os.makedirs(novel_path)

        info_file = os.path.join(novel_path, "novel_info.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(novel.to_dict(), f, ensure_ascii=False, indent=2)

    def create_novel(self, title: str, topic: str, genre: str, 
                    cover_image: str = "", save_path: str = "") -> Novel:
        """创建新小说"""
        novel_id = f"novel_{uuid.uuid4().hex[:8]}"
        # 创建小说目录
        novel_path = os.path.join(self.novels_dir, novel_id)
        if not os.path.exists(novel_path):
            os.makedirs(novel_path)
        # 如果没有提供save_path，使用默认的小说目录
        if not save_path:
            save_path = novel_path
        # 创建chapters目录
        chapters_dir = os.path.join(novel_path, "chapters")
        if not os.path.exists(chapters_dir):
            os.makedirs(chapters_dir)
        novel = Novel(
            novel_id=novel_id,
            title=title,
            description=topic,  # description字段存储topic内容
            topic=topic,
            genre=genre,
            cover_image=cover_image,
            save_path=save_path
        )
        self._novels[novel_id] = novel
        self._save_novel(novel)
        return novel

    def update_novel(self, novel_id: str, **kwargs) -> bool:
        """更新小说信息"""
        if novel_id not in self._novels:
            return False

        novel = self._novels[novel_id]
        for key, value in kwargs.items():
            if hasattr(novel, key):
                setattr(novel, key, value)

        # 如果更新了description，同时更新topic
        if 'description' in kwargs:
            novel.topic = kwargs['description']
        # 如果更新了topic，同时更新description
        if 'topic' in kwargs:
            novel.description = kwargs['topic']

        novel.update_timestamp()
        self._save_novel(novel)
        return True

    def delete_novel(self, novel_id: str) -> bool:
        """删除小说"""
        if novel_id not in self._novels:
            return False

        novel_path = os.path.join(self.novels_dir, novel_id)
        try:
            # 删除小说目录及其所有内容
            import shutil
            shutil.rmtree(novel_path)
            del self._novels[novel_id]
            return True
        except Exception as e:
            print(f"删除小说 {novel_id} 失败: {e}")
            return False

    def get_novel(self, novel_id: str) -> Optional[Novel]:
        """获取单个小说"""
        return self._novels.get(novel_id)

    def get_all_novels(self) -> List[Novel]:
        """获取所有小说"""
        return list(self._novels.values())

    def search_novels(self, keyword: str) -> List[Novel]:
        """搜索小说"""
        keyword = keyword.lower()
        results = []
        for novel in self._novels.values():
            if (keyword in novel.title.lower() or 
                keyword in novel.description.lower() or
                keyword in novel.genre.lower()):
                results.append(novel)
        return results

    def update_novel_stats(self, novel_id: str, chapter_count: int = None,
                          generated_chapters: int = None, word_count: int = None) -> bool:
        """更新小说统计数据"""
        if novel_id not in self._novels:
            return False

        novel = self._novels[novel_id]
        if chapter_count is not None:
            novel.chapter_count = chapter_count
        if generated_chapters is not None:
            novel.generated_chapters = generated_chapters
        if word_count is not None:
            novel.word_count = word_count

        novel.update_timestamp()
        self._save_novel(novel)
        return True


class NovelCard(ctk.CTkFrame):
    """小说卡片组件"""
    def __init__(self, master, novel: Novel, on_edit=None, on_delete=None, on_open=None, on_selection_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.novel = novel
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_open = on_open
        self.on_selection_change = on_selection_change
        self.selected = False
        self.context_menu = None
        self.is_hovered = False
        self.cover_border = None  # 封面边框Frame
        self.shadow_frame = None  # 阴影Frame
        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        """构建卡片UI"""
        # 设置卡片样式（透明背景，固定尺寸160x220）
        self.configure(fg_color="transparent", corner_radius=0, width=160, height=220)

        # 阴影Frame（用于显示阴影效果）
        self.shadow_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            width=160,
            height=220
        )
        self.shadow_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # 封面边框Frame（用于显示交互效果，固定大小160x220）
        self.cover_border = ctk.CTkFrame(
            self.shadow_frame,
            fg_color="transparent",
            border_width=0,
            width=160,
            height=220
        )
        self.cover_border.place(x=0, y=0, relwidth=1, relheight=1)
        
        # 封面区域（固定大小160x220，完全透明）
        cover_frame = ctk.CTkFrame(self.cover_border, fg_color="transparent", width=160, height=220)
        cover_frame.place(x=0, y=0, relwidth=1, relheight=1)
        # 为cover_frame绑定鼠标事件
        cover_frame.bind("<Enter>", self._on_enter)
        cover_frame.bind("<Leave>", self._on_leave)
        cover_frame.bind("<Button-1>", self._on_clicked)

        if self.novel.cover_image and os.path.exists(self.novel.cover_image):
            try:
                img = Image.open(self.novel.cover_image)
                img = img.resize((152, 212), Image.Resampling.LANCZOS)
                cover_photo = ctk.CTkImage(img, size=(152, 212))
                cover_label = ctk.CTkLabel(cover_frame, image=cover_photo, text="", width=152, height=212)
                cover_label.image = cover_photo  # 保持引用
                cover_label.place(relx=0.5, rely=0.5, anchor="center")
                # 绑定双击事件到封面Label
                cover_label.bind("<Double-Button-1>", lambda event: self._on_open_clicked())
                # 绑定右键菜单事件到封面Label
                cover_label.bind("<Button-3>", self._show_context_menu)
                # 绑定鼠标悬停和点击事件
                cover_label.bind("<Enter>", self._on_enter)
                cover_label.bind("<Leave>", self._on_leave)
                cover_label.bind("<Button-1>", self._on_clicked)
            except Exception as e:
                print(f"加载封面失败: {e}")
                # 显示加载失败的提示
                cover_label = ctk.CTkLabel(
                    cover_frame,
                    text="封面加载失败",
                    width=160,
                    height=220,
                    fg_color=("gray90", "gray25"),
                    text_color=("#cc0000", "#ff6b6b")
                )
                cover_label.pack()
                # 绑定双击事件
                cover_label.bind("<Double-Button-1>", lambda event: self._on_open_clicked())
                # 绑定右键菜单事件
                cover_label.bind("<Button-3>", self._show_context_menu)
                # 绑定鼠标悬停和点击事件
                cover_label.bind("<Enter>", self._on_enter)
                cover_label.bind("<Leave>", self._on_leave)
                cover_label.bind("<Button-1>", self._on_clicked)
        else:
            self._create_default_cover(cover_frame)

        # 标题
        # title_frame = ctk.CTkFrame(
        #     self.cover_border,
        #     fg_color="transparent",
        #     width=144,
        #     height=40
        # )
        # title_frame.place(relx=0.5, rely=0.9, anchor="center", relwidth=0.9)
        
        # 标题
        self.title_label = ctk.CTkLabel(
            self.cover_border, 
            text=self._truncate_title(self.novel.title),
            font=("Microsoft YaHei", 12, "bold"),
            text_color=("black", "white"),
            fg_color="transparent",
            anchor="center",
            justify="center",
            wraplength=136
        )
        self.title_label.place(relx=0.5, rely=0.9, anchor="center", relwidth=0.9)
        # 绑定右键菜单事件到标题Label
        self.title_label.bind("<Button-3>", self._show_context_menu)
        # 绑定鼠标悬停和点击事件
        self.title_label.bind("<Enter>", self._on_enter)
        self.title_label.bind("<Leave>", self._on_leave)
        self.title_label.bind("<Button-1>", self._on_clicked)

    def _bind_events(self):
        """绑定事件"""
        # 绑定双击事件
        self.bind("<Double-Button-1>", lambda event: self._on_open_clicked())
        # 绑定右键菜单事件
        self.bind("<Button-3>", self._show_context_menu)
        # 绑定鼠标悬停事件
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        # 绑定点击事件
        self.bind("<Button-1>", self._on_clicked)

    def _on_enter(self, event=None):
        """鼠标进入事件"""
        if not self.is_hovered:
            self.is_hovered = True
            self._update_card_style()

    def _on_leave(self, event=None):
        """鼠标离开事件"""
        if self.is_hovered:
            self.is_hovered = False
            self._update_card_style()

    def _on_clicked(self, event):
        """点击事件"""
        # 切换选中状态
        self.selected = not self.selected
        self._update_card_style()
        # 通知选中状态变化
        if self.on_selection_change:
            self.on_selection_change(self)

    def _update_card_style(self):
        """更新卡片样式"""
        if self.shadow_frame and self.cover_border:
            if self.selected:
                # 选中状态 - 蓝色边框+阴影效果
                self.shadow_frame.configure(
                    fg_color=("#99ccff", "#003366")
                )
                self.cover_border.configure(
                    fg_color=("#cce6ff", "#004080"),
                    border_color=("#0066cc", "#0099ff"),
                    border_width=5
                )

            elif self.is_hovered:
                # 悬停状态 - 浅紫色边框+阴影效果
                self.shadow_frame.configure(
                    fg_color=("#d0c0ff", "#3a3050")
                )
                self.cover_border.configure(
                    fg_color=("#e0d5ff", "#4a4060"),
                    border_color=("#9966cc", "#aa88dd"),
                    border_width=4
                )

            else:
                # 普通状态
                self.shadow_frame.configure(
                    fg_color="transparent"
                )
                self.cover_border.configure(
                    fg_color="transparent",
                    border_width=0
                )


    def _show_context_menu(self, event):
        """显示右键菜单"""
        # 先隐藏所有已存在的右键菜单
        self._hide_all_context_menus()
        
        if self.context_menu is None:
            # 将菜单的父窗口设置为主窗口，确保可以正确显示
            self.context_menu = ctk.CTkFrame(
                self.winfo_toplevel(),
                fg_color=("white", "#1a1a1a"),
                border_width=0,
                corner_radius=12
            )
            
            # 打开按钮
            if self.on_open:
                open_btn = ctk.CTkButton(
                    self.context_menu,
                    text="打开",
                    width=120,
                    height=36,
                    font=("Microsoft YaHei", 13, "bold"),
                    fg_color="transparent",
                    hover_color=("gray90", "gray30"),
                    text_color=("#1a1a1a", "#ffffff"),
                    anchor="w",
                    corner_radius=8,
                    command=lambda: self._on_menu_action("open")
                )
                open_btn.pack(fill="x", padx=2, pady=2)
            
            # 编辑按钮
            if self.on_edit:
                edit_btn = ctk.CTkButton(
                    self.context_menu,
                    text="编辑",
                    width=120,
                    height=36,
                    font=("Microsoft YaHei", 13, "bold"),
                    fg_color="transparent",
                    hover_color=("gray90", "gray30"),
                    text_color=("#1a1a1a", "#ffffff"),
                    anchor="w",
                    corner_radius=8,
                    command=lambda: self._on_menu_action("edit"),
                )
                edit_btn.pack(fill="x", padx=2, pady=2)
            
            # 删除按钮
            if self.on_delete:
                delete_btn = ctk.CTkButton(
                    self.context_menu,
                    text="删除",
                    width=120,
                    height=36,
                    font=("Microsoft YaHei", 13, "bold"),
                    fg_color="transparent",
                    hover_color=("gray90", "gray30"),
                    text_color=("#cc0000", "#ff6b6b"),
                    anchor="w",
                    corner_radius=8,
                    command=lambda: self._on_menu_action("delete"),
                )
                delete_btn.pack(fill="x", padx=2, pady=2)
        
        # 在鼠标位置显示菜单，确保不超出屏幕边界
        x = event.x_root
        y = event.y_root
        
        # 获取菜单尺寸
        self.context_menu.update_idletasks()
        menu_width = self.context_menu.winfo_reqwidth()
        menu_height = self.context_menu.winfo_reqheight()
        
        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 调整位置，确保菜单在屏幕内
        if x + menu_width > screen_width:
            x = screen_width - menu_width - 10
        if y + menu_height > screen_height:
            y = screen_height - menu_height - 10
        
        # 将屏幕坐标转换为相对于主窗口的坐标
        root_x = x - self.winfo_toplevel().winfo_rootx()
        root_y = y - self.winfo_toplevel().winfo_rooty()
        
        # 确保菜单在主窗口内
        root_width = self.winfo_toplevel().winfo_width()
        root_height = self.winfo_toplevel().winfo_height()
        if root_x + menu_width > root_width:
            root_x = root_width - menu_width - 10
        if root_y + menu_height > root_height:
            root_y = root_height - menu_height - 10
        if root_x < 0:
            root_x = 10
        if root_y < 0:
            root_y = 10

        # 使用place在主窗口中显示菜单
        self.context_menu.place(x=root_x, y=root_y)
        
        # 点击其他地方隐藏菜单 - 绑定到主窗口
        self._hide_binding = self.winfo_toplevel().bind("<Button-1>", self._hide_context_menu, add="+")
    
    def _hide_all_context_menus(self):
        """隐藏所有右键菜单"""
        # 获取主窗口
        toplevel = self.winfo_toplevel()
        
        # 遍历所有卡片，隐藏它们的菜单
        try:
            # 尝试从scroll_frame获取所有卡片
            scroll_frame = toplevel.nametowidget(toplevel.winfo_children()[0]).novel_manager_ui.scroll_frame
            for widget in scroll_frame.winfo_children():
                if isinstance(widget, NovelCard) and hasattr(widget, "context_menu") and widget.context_menu:
                    widget.context_menu.place_forget()
        except:
            pass

    def _hide_context_menu(self, event=None):
        """隐藏右键菜单"""
        try:
            if self.context_menu:
                self.context_menu.place_forget()
        except:
            pass
        # 解绑主窗口的点击事件
        try:
            if hasattr(self, "_hide_binding"):
                self.winfo_toplevel().unbind("<Button-1>", self._hide_binding)
        except:
            pass







    def _truncate_title(self, title, max_lines=2, wrap_length=136):
        """截断标题文本，最多显示指定行数，超出后显示省略号"""
        lines = []
        current_line = ""
        current_width = 0
        for char in title:
            # 估算字符宽度（中文字符按2个英文字符计算）
            char_width = 2 if ord(char) > 127 else 1
            
            # 如果当前行还未达到最大行数，且添加字符后不超过宽度限制
            if len(lines) < max_lines and current_width + char_width <= wrap_length:
                current_line += char
                current_width += char_width
            # 如果当前行已满，且还有空间添加新行
            elif len(lines) < max_lines:
                lines.append(current_line)
                current_line = char
                current_width = char_width
            # 如果已经达到最大行数，停止处理
            else:
                break
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        # 如果超出最大行数，最后一行添加省略号
        if len(lines) >= max_lines and (current_line or len(title) > sum(len(line) for line in lines)):
            lines[-1] = lines[-1][:-3] + "..." if len(lines[-1]) > 3 else "..."
        
        # 直接返回原始标题，让CTkLabel的wraplength参数来处理换行和截断
        return title

    def _create_default_cover(self, parent):
        """创建默认封面"""
        cover_label = ctk.CTkLabel(
            parent,
            text="无封面",
            width=152,
            height=212,
            fg_color=("gray90", "gray25"),
            text_color=("gray40", "gray70")
        )
        cover_label.place(relx=0.5, rely=0.5, anchor="center")
        # 绑定双击事件到默认封面Label
        cover_label.bind("<Double-Button-1>", lambda event: self._on_open_clicked())
        # 绑定右键菜单事件到默认封面Label
        cover_label.bind("<Button-3>", self._show_context_menu)
        # 绑定鼠标悬停和点击事件
        cover_label.bind("<Enter>", self._on_enter)
        cover_label.bind("<Leave>", self._on_leave)
        cover_label.bind("<Button-1>", self._on_clicked)

    def _on_menu_action(self, action):
        """菜单操作处理，先隐藏菜单再执行操作"""
        # 先隐藏菜单
        self._hide_context_menu()
        # 执行对应的操作
        if action == "open":
            self._on_open_clicked()
        elif action == "edit":
            self._on_edit_clicked()
        elif action == "delete":
            self._on_delete_clicked()

    def _on_edit_clicked(self):
        """编辑按钮点击事件"""
        if self.on_edit:
            self.on_edit(self.novel)

    def _on_delete_clicked(self):
        """删除按钮点击事件"""
        if self.on_delete:
            self.on_delete(self.novel)

    def _on_select_changed(self):
        """选择状态改变事件"""
        self.selected = self.select_check.get()
        if self.on_selection_change:
            self.on_selection_change(self)

    def _on_open_clicked(self):
        """打开按钮点击事件"""
        if self.on_open:
            self.on_open(self.novel)


class NovelManagerUI(ctk.CTkFrame):
    """小说管理UI组件"""
    def __init__(self, master, on_novel_opened=None, manager=None, **kwargs):
        super().__init__(master, **kwargs)
        # 如果没有提供manager实例，则创建一个新的
        self.manager = manager if manager else NovelManager()
        self.on_novel_opened = on_novel_opened
        self.current_page = 1
        self.page_size = 15  # 每页显示15本小说
        self.current_novels: List[Novel] = []
        self.search_keyword = ""
        self._search_timer = None  # 搜索防抖定时器
        self._resize_timer = None  # 窗口大小改变防抖定时器
        self._notification_label = None  # 通知标签
        self._notification_timer = None  # 通知定时器
        self._build_ui()
        # 延迟加载小说列表，确保界面完全渲染后再计算列数
        self.after(100, self._load_novels)

    def _build_ui(self):
        """构建UI"""
        # 通知标签（初始隐藏）
        self._notification_label = ctk.CTkLabel(
            self,
            text="",
            fg_color="#2CC985",
            text_color="white",
            font=("Microsoft YaHei", 12),
            corner_radius=8,
            padx=20,
            pady=8
        )

        # 标题栏
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        # 标题
        title_label = ctk.CTkLabel(
            header_frame,
            text="小说管理",
            font=("Microsoft YaHei", 24, "bold")
        )
        title_label.pack(side="left")

        # 搜索框
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 搜索小说标题、主题或类型...",
            height=35,
            border_width=2,
            corner_radius=8,
            width=300
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search_key_release)

        # 新建小说按钮
        new_btn = ctk.CTkButton(
            search_frame,
            text="+ 新建小说",
            width=100,
            height=35,
            command=lambda: self._show_novel_dialog()
        )
        new_btn.pack(side="left", padx=(0, 10))

        # 批量操作按钮
        self.batch_delete_btn = ctk.CTkButton(
            search_frame,
            text="批量删除",
            width=100,
            height=35,
            state="disabled",
            command=self._on_batch_delete
        )
        self.batch_delete_btn.pack(side="left", padx=(0, 10))

        # 排序下拉菜单
        self.sort_var = ctk.StringVar(value="更新时间")
        self.sort_menu = ctk.CTkOptionMenu(
            search_frame,
            values=["更新时间", "创建时间", "标题", "章节数", "字数"],
            variable=self.sort_var,
            width=120,
            height=35,
            command=self._on_sort_changed
        )
        self.sort_menu.pack(side="left")

        # 小说列表区域（可滚动）
        self.scroll_container = ctk.CTkFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        # 绑定scroll_container和self的Configure事件
        self.scroll_container.bind("<Configure>", self._on_window_resize)
        self.bind("<Configure>", self._on_window_resize)
        
        # 创建可滚动区域
        self.scroll_frame = ctk.CTkScrollableFrame(self.scroll_container, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True)
        # 隐藏滚动条
        self.scroll_frame._scrollbar.grid_remove()

        # 分页控件
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.pack(fill="x", padx=10, pady=(0, 10))

        # 上一页按钮
        prev_btn = ctk.CTkButton(
            self.pagination_frame,
            text="◀ 上一页",
            width=100,
            height=32,
            corner_radius=6,
            command=self._on_prev_page
        )
        prev_btn.pack(side="left", padx=(0, 10))

        # 页码输入框
        self.page_entry = ctk.CTkEntry(
            self.pagination_frame,
            width=60,
            height=32,
            justify="center"
        )
        self.page_entry.pack(side="left", padx=(0, 5))
        self.page_entry.bind("<Return>", self._on_page_jump)

        # 总页数显示
        self.total_page_label = ctk.CTkLabel(
            self.pagination_frame,
            text="/ 1",
            font=("Microsoft YaHei", 12)
        )
        self.total_page_label.pack(side="left", padx=(0, 10))

        # 下一页按钮
        next_btn = ctk.CTkButton(
            self.pagination_frame,
            text="下一页 ▶",
            width=100,
            height=32,
            corner_radius=6,
            command=self._on_next_page
        )
        next_btn.pack(side="left", padx=(0, 20))

        self.size_var = ctk.StringVar(value="15")
        
        # 绑定窗口大小改变事件
        self.bind("<Configure>", self._on_window_resize)

    def _load_novels(self):
        """加载小说列表"""
        if self.search_keyword:
            self.current_novels = self.manager.search_novels(self.search_keyword)
        else:
            self.current_novels = self.manager.get_all_novels()

        # 按选定的排序方式排序
        self._sort_novels()
        self._refresh_novel_list()

    def _sort_novels(self):
        """根据选择的排序方式排序小说"""
        sort_type = self.sort_var.get()
        if sort_type == "更新时间":
            self.current_novels.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_type == "创建时间":
            self.current_novels.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_type == "标题":
            self.current_novels.sort(key=lambda x: x.title)
        elif sort_type == "章节数":
            self.current_novels.sort(key=lambda x: x.chapter_count, reverse=True)
        elif sort_type == "字数":
            self.current_novels.sort(key=lambda x: x.word_count, reverse=True)

    def _on_sort_changed(self, value):
        """排序方式改变事件"""
        self._sort_novels()
        self._refresh_novel_list()

    def _refresh_novel_list(self):
        """刷新小说列表显示"""
        # 清空现有列表
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # 计算分页
        total = len(self.current_novels)
        total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1

        # 确保当前页码有效
        if self.current_page > total_pages:
            self.current_page = total_pages
        elif self.current_page < 1:
            self.current_page = 1

        # 更新页码显示
        self.page_entry.delete(0, "end")
        self.page_entry.insert(0, str(self.current_page))
        self.total_page_label.configure(text=f"/ {total_pages}")
        
        # 根据页数控制分页控件的显示
        if total_pages <= 1:
            self.pagination_frame.pack_forget()
        else:
            self.pagination_frame.pack(fill="x", padx=10, pady=(0, 10))

        # 计算当前页的小说范围
        start = (self.current_page - 1) * self.page_size
        end = min(start + self.page_size, total)
        page_novels = self.current_novels[start:end]

        # 创建卡片网格（自适应布局）
        if page_novels:
            # 根据窗口宽度动态计算列数
            frame_width = self.scroll_container.winfo_width()
            # 如果窗口宽度小于等于1，使用默认宽度800
            if frame_width <= 1:
                frame_width = 800
            card_width = 160  # 卡片宽度
            card_spacing = 16  # 卡片间距（padx=8 * 2）
            # 计算可用的总宽度（减去padding）
            available_width = frame_width - 20  # padx=10 * 2
            # 计算每列需要的总宽度（卡片宽度+间距）
            column_width = card_width + card_spacing
            # 计算最大列数
            columns = max(1, int(available_width / column_width))
            # 根据当前页面书籍数量动态调整最大列数
            columns = min(columns, len(page_novels))  # 最多显示当前页书籍数量
            
            # 配置网格布局
            # 先重置所有列的配置
            for i in range(len(page_novels)):  # 最多重置当前页书籍数量的列
                self.scroll_frame.grid_columnconfigure(i, weight=0, minsize=0)
            # 再配置新的列
            for i in range(columns):
                self.scroll_frame.grid_columnconfigure(i, weight=0, minsize=card_width + card_spacing)

            # 创建卡片
            for idx, novel in enumerate(page_novels):
                row = idx // columns
                col = idx % columns
                card = NovelCard(
                    self.scroll_frame,
                    novel,
                    on_edit=self._on_edit_novel,
                    on_delete=self._on_delete_novel,
                    on_open=self._on_open_novel,
                    on_selection_change=self._on_card_selection_change
                )
                card.grid(row=row, column=col, padx=8, pady=8, sticky="ew")
        else:
            # 空状态提示
            # 创建一个容器frame来实现居中效果
            empty_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty_container.pack(fill="both", expand=True)
            empty_label = ctk.CTkLabel(
                empty_container,
                text='📚 暂无小说\n点击"新建小说"开始创作',
                font=("Microsoft YaHei", 16),
                text_color=("gray50", "gray70")
            )
            empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def _show_novel_dialog(self, novel: Novel = None):
        """显示新建/编辑小说对话框
        
        Args:
            novel: 如果提供，则为编辑模式；否则为新建模式
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑小说" if novel else "新建小说")
        dialog.geometry("600x500")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        # 居中显示对话框
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # 主容器
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 标题输入
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 8))

        title_label = ctk.CTkLabel(title_frame, text="小说标题:", width=70, anchor="w",
                                  font=("Microsoft YaHei", 11, "bold"))
        title_label.pack(side="left")

        # 标题占位符
        title_placeholder = "请输入小说标题，如：修仙之路"

        def set_title_placeholder():
            if not title_var.get():
                title_entry.delete(0, "end")
                title_entry.insert(0, title_placeholder)
                title_entry.configure(text_color=("gray70", "gray50"))

        def clear_title_placeholder(event=None):
            if title_entry.get() == title_placeholder:
                title_entry.delete(0, "end")
                title_entry.configure(text_color=("black", "white"))

        def check_title_placeholder(event=None):
            if not title_var.get():
                set_title_placeholder()

        title_var = ctk.StringVar(value=novel.title if novel else "")
        title_entry = ctk.CTkEntry(title_frame, textvariable=title_var, height=32)
        title_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # 初始化占位符
        if novel and novel.title:
            title_entry.configure(text_color=("black", "white"))
        else:
            set_title_placeholder()

        # 绑定事件
        title_entry.bind("<FocusIn>", clear_title_placeholder)
        title_entry.bind("<FocusOut>", check_title_placeholder)
        
        # 添加标题长度限制
        def validate_title(*args):
            current_text = title_var.get()
            if len(current_text) > 20:
                title_var.set(current_text[:20])
        title_var.trace("w", validate_title)

        # 主题输入
        topic_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        topic_frame.pack(fill="both", expand=True, pady=(0, 8))

        topic_label = ctk.CTkLabel(topic_frame, text="主题:", width=70, anchor="w",
                                font=("Microsoft YaHei", 11, "bold"))
        topic_label.pack(side="left")

        topic_text = ctk.CTkTextbox(topic_frame, height=160)
        topic_text.pack(side="top", fill="both", expand=True, padx=(8, 0), pady=(3, 0))

        # 主题占位符
        topic_placeholder = "请输入小说主题，描述故事背景、主要情节和核心冲突..."

        def set_topic_placeholder():
            if not topic_text.get("0.0", "end").strip():
                topic_text.delete("0.0", "end")
                topic_text.insert("0.0", topic_placeholder)
                topic_text.configure(text_color=("gray70", "gray50"))

        def clear_topic_placeholder(event=None):
            if topic_text.get("0.0", "end").strip() == topic_placeholder:
                topic_text.delete("0.0", "end")
                topic_text.configure(text_color=("black", "white"))

        def check_topic_placeholder(event=None):
            content = topic_text.get("0.0", "end").strip()
            if not content:
                set_topic_placeholder()

        # 初始化占位符
        if novel and novel.topic:
            topic_text.insert("0.0", novel.topic)
            topic_text.configure(text_color=("black", "white"))
        else:
            set_topic_placeholder()

        # 绑定事件
        topic_text.bind("<FocusIn>", clear_topic_placeholder)
        topic_text.bind("<FocusOut>", check_topic_placeholder)

        # 封面选择
        cover_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        cover_frame.pack(fill="x", pady=(0, 8))

        # 新建模式：默认加载SVG封面图片路径
        # 编辑模式：显示当前封面图片路径
        default_cover = os.path.abspath(os.path.join("data", "default_cover.png"))
        cover_var = ctk.StringVar(value=novel.cover_image if novel else default_cover)
        cover_label = ctk.CTkLabel(cover_frame, text="封面图片:", width=70, anchor="w",
                                  font=("Microsoft YaHei", 11, "bold"))
        cover_label.pack(side="left")

        # 封面图片路径占位符
        cover_placeholder = "选择或输入封面图片路径"

        def set_cover_placeholder():
            if not cover_var.get():
                cover_entry.delete(0, "end")
                cover_entry.insert(0, cover_placeholder)
                cover_entry.configure(text_color=("gray70", "gray50"))

        def clear_cover_placeholder(event=None):
            if cover_entry.get() == cover_placeholder:
                cover_entry.delete(0, "end")
                cover_entry.configure(text_color=("black", "white"))

        def check_cover_placeholder(event=None):
            if not cover_var.get():
                set_cover_placeholder()

        cover_entry = ctk.CTkEntry(cover_frame, textvariable=cover_var, height=32)
        cover_entry.pack(side="left", fill="x", expand=True, padx=(8, 5))

        # 初始化占位符
        if novel and novel.cover_image:
            cover_entry.configure(text_color=("black", "white"))
        else:
            set_cover_placeholder()

        # 绑定事件
        cover_entry.bind("<FocusIn>", clear_cover_placeholder)
        cover_entry.bind("<FocusOut>", check_cover_placeholder)

        def browse_cover():
            file_path = filedialog.askopenfilename(
                title="选择封面图片",
                filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp")]
            )
            if file_path:
                cover_var.set(file_path)
                cover_entry.configure(text_color=("black", "white"))

        browse_btn = ctk.CTkButton(cover_frame, text="浏览...", width=70, height=32,
                                  command=browse_cover)
        browse_btn.pack(side="right")

        # 类型输入
        genre_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        genre_frame.pack(fill="x", pady=(0, 8))

        genre_label = ctk.CTkLabel(genre_frame, text="类型:", width=70, anchor="w",
                                font=("Microsoft YaHei", 11, "bold"))
        genre_label.pack(side="left")

        # 类型占位符
        genre_placeholder = "允许填写：玄幻、都市、科幻等"

        def set_genre_placeholder():
            if not genre_var.get():
                genre_entry.delete(0, "end")
                genre_entry.insert(0, genre_placeholder)
                genre_entry.configure(text_color=("gray70", "gray50"))

        def clear_genre_placeholder(event=None):
            if genre_entry.get() == genre_placeholder:
                genre_entry.delete(0, "end")
                genre_entry.configure(text_color=("black", "white"))

        def check_genre_placeholder(event=None):
            if not genre_var.get():
                set_genre_placeholder()

        # 使用novel.genre作为默认值，如果没有则使用空字符串
        genre_var = ctk.StringVar(value=novel.genre if novel else "")
        genre_entry = ctk.CTkEntry(genre_frame, textvariable=genre_var, height=32)
        genre_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # 初始化占位符
        if novel and novel.genre:
            genre_entry.configure(text_color=("black", "white"))
        else:
            set_genre_placeholder()

        # 绑定事件
        genre_entry.bind("<FocusIn>", clear_genre_placeholder)
        genre_entry.bind("<FocusOut>", check_genre_placeholder)

        # 保存路径输入
        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=(0, 8))

        path_label = ctk.CTkLabel(path_frame, text="保存路径:", width=70, anchor="w",
                                 font=("Microsoft YaHei", 11, "bold"))
        path_label.pack(side="left")

        # 获取默认保存路径
        # 新建模式：显示小说的父目录
        # 编辑模式：显示小说的具体目录
        if novel and hasattr(novel, "save_path") and novel.save_path:
            default_path = novel.save_path
        else:
            default_path = os.path.abspath(os.path.join("data", "novels"))
        path_var = ctk.StringVar(value=default_path)
        # 保存路径占位符
        path_placeholder = "选择或输入小说保存路径"

        def set_path_placeholder():
            if not path_var.get():
                path_entry.delete(0, "end")
                path_entry.insert(0, path_placeholder)
                path_entry.configure(text_color=("gray70", "gray50"))

        def clear_path_placeholder(event=None):
            if path_entry.get() == path_placeholder:
                path_entry.delete(0, "end")
                path_entry.configure(text_color=("black", "white"))

        def check_path_placeholder(event=None):
            if not path_var.get():
                set_path_placeholder()

        path_entry = ctk.CTkEntry(path_frame, textvariable=path_var, height=32)
        path_entry.pack(side="left", fill="x", expand=True, padx=(8, 5))

        # 初始化占位符
        if novel and hasattr(novel, "save_path") and novel.save_path:
            path_entry.configure(text_color=("black", "white"))
        else:
            set_path_placeholder()

        # 绑定事件
        path_entry.bind("<FocusIn>", clear_path_placeholder)
        path_entry.bind("<FocusOut>", check_path_placeholder)

        def browse_path():
            from tkinter import filedialog as tk_filedialog
            selected_path = tk_filedialog.askdirectory(
                title="选择保存路径",
                initialdir=path_var.get()
            )
            if selected_path:
                path_var.set(selected_path)
                path_entry.configure(text_color=("black", "white"))

        browse_path_btn = ctk.CTkButton(path_frame, text="浏览...", width=70, height=32,
                                       command=browse_path)
        browse_path_btn.pack(side="right")

        # 状态选择（仅编辑模式显示）
        status_var = None
        if novel:
            status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            status_frame.pack(fill="x", pady=(0, 8))

            status_label = ctk.CTkLabel(status_frame, text="状态:", width=70, anchor="w",
                                      font=("Microsoft YaHei", 11, "bold"))
            status_label.pack(side="left")

            status_var = ctk.StringVar(value=novel.status)
            status_menu = ctk.CTkOptionMenu(
                status_frame,
                values=["草稿", "进行中", "已完成"],
                variable=status_var,
                width=140,
                height=32
            )
            status_menu.pack(side="left", padx=(8, 0))

        # 按钮区域
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        def on_save():
            title = title_var.get().strip()
            topic = topic_text.get("0.0", "end").strip()
            genre = genre_var.get().strip()
            cover = cover_var.get().strip()
            save_path = path_var.get().strip()

            # 检查并排除占位符文本
            if title == title_placeholder:
                title = ""
            if topic == topic_placeholder:
                topic = ""
            if genre == genre_placeholder:
                genre = ""
            if cover == cover_placeholder:
                cover = ""
            if save_path == path_placeholder:
                save_path = ""

            if not title:
                messagebox.showwarning("警告", "请输入小说标题")
                return

            if len(title) > 20:
                messagebox.showwarning("警告", "小说标题不能超过20个字")
                return

            if not topic:
                messagebox.showwarning("警告", "请输入主题")
                return

            if not genre:
                messagebox.showwarning("警告", "请输入类型")
                return

            if not save_path:
                messagebox.showwarning("警告", "请选择或输入保存路径")
                return

            try:
                if novel:
                    # 编辑模式
                    self.manager.update_novel(
                        novel.novel_id,
                        title=title,
                        topic=topic,
                        description=topic,  # 同时更新description字段
                        genre=genre,
                        cover_image=cover,
                        status=status_var.get() if status_var else novel.status,
                        save_path=save_path
                    )
                    # 如果当前打开的小说是被编辑的小说，同步更新"小说参数"模块中的字段
                    if self.on_novel_opened and hasattr(self.master, 'current_novel_id') and self.master.current_novel_id == novel.novel_id:
                        if hasattr(self.master, 'title_var'):
                            self.master.title_var.set(title)
                        if hasattr(self.master, 'topic_var'):
                            self.master.topic_var.set(topic)
                        if hasattr(self.master, 'genre_var'):
                            self.master.genre_var.set(genre)
                    messagebox.showinfo("成功", "小说更新成功！")
                    # 刷新小说列表，以显示最新的小说名称
                    self._load_novels()
                else:
                    # 新建模式
                    new_novel = self.manager.create_novel(title, topic, genre, cover, save_path)
                    messagebox.showinfo("成功", "小说创建成功！")
                    # 直接将新创建的小说添加到列表中，避免重新加载导致topic和genre被重置
                    self.current_novels.insert(0, new_novel)
                    self._refresh_novel_list()
                
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"操作失败: {str(e)}")

        save_btn = ctk.CTkButton(btn_frame, text="保存" if novel else "创建", 
                              command=on_save, width=90, height=32)
        save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = ctk.CTkButton(btn_frame, text="取消", command=dialog.destroy, 
                                 width=90, height=32)
        cancel_btn.pack(side="right")

    def _on_edit_novel(self, novel: Novel):
        """编辑小说"""
        self._show_novel_dialog(novel=novel)

    def _on_delete_novel(self, novel: Novel):
        """删除小说"""
        if messagebox.askyesno("确认删除", f"确定要删除小说《{novel.title}》吗？\n此操作不可恢复！"):
            try:
                if self.manager.delete_novel(novel.novel_id):
                    self._load_novels()
                else:
                    messagebox.showerror("错误", "删除小说失败！")
            except Exception as e:
                messagebox.showerror("错误", f"删除小说失败: {str(e)}")

    def _on_card_selection_change(self, card):
        """卡片选择状态改变事件"""
        selected_count = sum(1 for widget in self.scroll_frame.winfo_children() 
                           if hasattr(widget, "selected") and widget.selected)
        self.batch_delete_btn.configure(
            state="normal" if selected_count > 0 else "disabled",
            text=f"批量删除 ({selected_count})"
        )

    def _show_notification(self, message, duration=1000):
        """显示顶部通知"""
        # 如果已有通知在显示，先取消定时器
        if self._notification_timer:
            self.after_cancel(self._notification_timer)

        # 设置通知内容
        self._notification_label.configure(text=message)
        # 显示通知
        self._notification_label.place(relx=0.5, rely=0.1, anchor="center")

        # 设置定时器，在指定时间后隐藏通知
        self._notification_timer = self.after(duration, self._hide_notification)

    def _hide_notification(self):
        """隐藏顶部通知"""
        self._notification_label.place_forget()
        self._notification_timer = None

    def _on_batch_delete(self):
        """批量删除选中的小说"""
        selected = [card.novel for card in self.scroll_frame.winfo_children() if hasattr(card, "selected") and card.selected]
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的小说")
            return
        
        titles = "\n".join([f"- {novel.title}" for novel in selected])
        if messagebox.askyesno("确认批量删除", f"确定要删除以下 {len(selected)} 本小说吗？\n{titles}\n\n此操作不可恢复！"):
            try:
                success_count = 0
                for novel in selected:
                    if self.manager.delete_novel(novel.novel_id):
                        success_count += 1
                self._load_novels()
            except Exception as e:
                messagebox.showerror("错误", f"批量删除失败: {str(e)}")

    def _on_open_novel(self, novel: Novel):
        """打开小说"""
        if self.on_novel_opened:
            self.on_novel_opened(novel)

    def _on_search_key_release(self, event):
        """搜索框键盘释放事件（带防抖）"""
        # 取消之前的定时器
        if self._search_timer:
            self.after_cancel(self._search_timer)
        
        # 设置新的定时器，延迟300ms执行搜索
        self._search_timer = self.after(300, self._perform_search)

    def _perform_search(self):
        """执行搜索"""
        # 获取搜索框内容
        search_widget = self.search_entry
        if search_widget:
            self.search_keyword = search_widget.get().strip()
            self.current_page = 1
            self._load_novels()

    def _on_search_clicked(self):
        """搜索按钮点击事件"""
        # 取消防抖定时器
        if self._search_timer:
            self.after_cancel(self._search_timer)
            self._search_timer = None
        # 立即执行搜索
        self._perform_search()

    def _on_prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_novel_list()

    def _on_page_jump(self, event):
        """页码跳转"""
        try:
            page_num = int(self.page_entry.get())
            total = len(self.current_novels)
            total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1
            if 1 <= page_num <= total_pages:
                self.current_page = page_num
                self._refresh_novel_list()
            else:
                self.page_entry.delete(0, "end")
                self.page_entry.insert(0, str(self.current_page))
        except ValueError:
            self.page_entry.delete(0, "end")
            self.page_entry.insert(0, str(self.current_page))

    def _on_next_page(self):
        """下一页"""
        total = len(self.current_novels)
        total_pages = (total + self.page_size - 1) // self.page_size if total > 0 else 1
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh_novel_list()

    def _on_window_resize(self, event):
        """窗口大小改变事件处理（带防抖）"""
        # 处理所有Configure事件
        

        
        # 取消之前的定时器
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        
        # 设置新的定时器，延迟200ms执行重新布局
        self._resize_timer = self.after(200, self._refresh_novel_list)

    def refresh_novels(self):
        """刷新小说列表"""
        self._load_novels()
        self._refresh_novel_list()
