# ui/optimize_comparison_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录优化对比对话框UI类
"""
import customtkinter as ctk


class OptimizeComparisonDialog(ctk.CTkToplevel):
    """
    章节目录优化对比对话框的UI类
    显示优化前后的章节内容对比
    """

    def __init__(self, master, original_content, optimized_content, chapter_number, on_apply_callback=None, on_cancel_callback=None):
        """
        初始化对话框

        参数:
            master: 父窗口
            original_content: 原始章节内容
            optimized_content: 优化后的章节内容
            chapter_number: 章节编号
            on_apply_callback: 应用修改回调函数
            on_cancel_callback: 取消回调函数
        """
        super().__init__(master)

        self.master = master
        self.original_content = original_content
        self.optimized_content = optimized_content
        self.chapter_number = chapter_number
        self.on_apply_callback = on_apply_callback
        self.on_cancel_callback = on_cancel_callback

        # 当前显示的章节编号
        self.current_chapter = chapter_number

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("优化前后对比")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 1200) // 2
        y = (screen_height - 800) // 2

        # 设置窗口位置和大小
        self.geometry(f'1200x800+{x}+{y}')

        # 设置窗口图标（如果存在）
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # 如果图标加载失败，继续执行

        # 允许调整大小
        self.resizable(True, True)

        # 设置最小尺寸
        self.minsize(1000, 700)

        # 设置窗口为模态
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 章节导航区
        self._create_navigation_area()

        # 对比内容区
        self._create_comparison_area()

        # 按钮区
        self._create_button_area()

    def _create_navigation_area(self):
        """创建章节导航区"""
        nav_frame = ctk.CTkFrame(self.main_container)
        nav_frame.pack(fill="x", pady=(0, 10))

        # 当前章节标签
        ctk.CTkLabel(
            nav_frame,
            text=f"当前章节：第{self.chapter_number}章",
            font=("Microsoft YaHei", 12, "bold")
        ).pack(side="left", padx=10, pady=10)

        # 上一个章节按钮
        self.btn_previous = ctk.CTkButton(
            nav_frame,
            text="上一个章节",
            command=self._on_previous_chapter,
            font=("Microsoft YaHei", 10),
            width=100
        )
        self.btn_previous.pack(side="right", padx=5, pady=10)

        # 下一个章节按钮
        self.btn_next = ctk.CTkButton(
            nav_frame,
            text="下一个章节",
            command=self._on_next_chapter,
            font=("Microsoft YaHei", 10),
            width=100
        )
        self.btn_next.pack(side="right", padx=5, pady=10)

    def _create_comparison_area(self):
        """创建对比内容区"""
        comparison_frame = ctk.CTkFrame(self.main_container)
        comparison_frame.pack(fill="both", expand=True, pady=(0, 10))

        # 创建左右分栏
        left_frame = ctk.CTkFrame(comparison_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_frame = ctk.CTkFrame(comparison_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # 左侧：优化前
        ctk.CTkLabel(
            left_frame,
            text="优化前",
            font=("Microsoft YaHei", 11, "bold")
        ).pack(pady=(10, 5))

        self.original_text = ctk.CTkTextbox(
            left_frame,
            font=("Microsoft YaHei", 10)
        )
        self.original_text.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.original_text.insert("end", self.original_content)
        self.original_text.configure(state="disabled")

        # 右侧：优化后
        ctk.CTkLabel(
            right_frame,
            text="优化后",
            font=("Microsoft YaHei", 11, "bold")
        ).pack(pady=(10, 5))

        self.optimized_text = ctk.CTkTextbox(
            right_frame,
            font=("Microsoft YaHei", 10)
        )
        self.optimized_text.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.optimized_text.insert("end", self.optimized_content)
        self.optimized_text.configure(state="disabled")

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0), ipady=10)

        # 右侧按钮容器
        right_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_button_frame.pack(side="right", padx=10, pady=10)

        # 取消按钮
        if self.on_cancel_callback:
            self.btn_cancel = ctk.CTkButton(
                right_button_frame,
                text="取消",
                command=self._on_cancel,
                font=("Microsoft YaHei", 10),
                width=120,
                height=35
            )
            self.btn_cancel.pack(side="right", padx=5)

        # 应用修改按钮
        if self.on_apply_callback:
            self.btn_apply = ctk.CTkButton(
                right_button_frame,
                text="应用修改",
                command=self._on_apply,
                font=("Microsoft YaHei", 10),
                fg_color=("#28a745", "#28a745"),
                hover_color=("#218838", "#218838"),
                text_color_disabled="gray",
                width=140,
                height=35
            )
            self.btn_apply.pack(side="right", padx=5)

    def _on_previous_chapter(self):
        """上一个章节按钮点击事件"""
        # 这里可以导航到上一个章节的对比
        pass

    def _on_next_chapter(self):
        """下一个章节按钮点击事件"""
        # 这里可以导航到下一个章节的对比
        pass

    def _on_apply(self):
        """应用修改按钮点击事件"""
        if self.on_apply_callback:
            self.on_apply_callback(self.chapter_number, self.optimized_content)
        self.destroy()

    def _on_cancel(self):
        """取消按钮点击事件"""
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.destroy()
