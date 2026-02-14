# ui/optimize_progress_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录优化进度对话框UI类
"""
import customtkinter as ctk


class OptimizeProgressDialog(ctk.CTkToplevel):
    """
    章节目录优化进度对话框的UI类
    显示优化进度和当前处理的问题
    """

    def __init__(self, master, total_issues, on_cancel_callback=None):
        """
        初始化对话框

        参数:
            master: 父窗口
            total_issues: 总问题数
            on_cancel_callback: 取消回调函数
        """
        super().__init__(master)

        self.master = master
        self.total_issues = total_issues
        self.current_issue = 0
        self.on_cancel_callback = on_cancel_callback

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("正在优化章节目录")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 600) // 2
        y = (screen_height - 250) // 2

        # 设置窗口位置和大小
        self.geometry(f'600x250+{x}+{y}')

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
        self.minsize(500, 200)

        # 设置窗口为模态
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 进度条区
        self._create_progress_area()

        # 当前处理问题区
        self._create_current_issue_area()

        # 统计信息区
        self._create_stats_area()

        # 按钮区
        self._create_button_area()

    def _create_progress_area(self):
        """创建进度条区"""
        progress_frame = ctk.CTkFrame(self.main_container)
        progress_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            progress_frame,
            text="进度：",
            font=("Microsoft YaHei", 10)
        ).pack(side="left", padx=5)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=300
        )
        self.progress_bar.pack(side="left", padx=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="0%",
            font=("Microsoft YaHei", 10)
        )
        self.progress_label.pack(side="left", padx=5)

    def _create_current_issue_area(self):
        """创建当前处理问题区"""
        issue_frame = ctk.CTkFrame(self.main_container)
        issue_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            issue_frame,
            text="正在处理：",
            font=("Microsoft YaHei", 10)
        ).pack(side="left", padx=5)

        self.current_issue_label = ctk.CTkLabel(
            issue_frame,
            text="准备开始...",
            font=("Microsoft YaHei", 10)
        )
        self.current_issue_label.pack(side="left", padx=5)

    def _create_stats_area(self):
        """创建统计信息区"""
        stats_frame = ctk.CTkFrame(self.main_container)
        stats_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            stats_frame,
            text="已完成：",
            font=("Microsoft YaHei", 10)
        ).pack(side="left", padx=5)

        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text=f"0/{self.total_issues}个问题",
            font=("Microsoft YaHei", 10)
        )
        self.stats_label.pack(side="left", padx=5)

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0), ipady=10)

        # 左侧按钮容器
        left_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_button_frame.pack(side="left", padx=10, pady=10)

        # 显示详情按钮
        self.btn_details = ctk.CTkButton(
            left_button_frame,
            text="显示详情",
            command=self._on_show_details,
            font=("Microsoft YaHei", 10),
            width=120,
            height=35
        )
        self.btn_details.pack(side="left", padx=5)

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

    def update_progress(self, current, total, issue_description=""):
        """
        更新进度

        参数:
            current: 当前进度
            total: 总数
            issue_description: 当前处理的问题描述
        """
        # 更新进度条
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"{int(progress * 100)}%")

        # 更新当前问题
        if issue_description:
            self.current_issue_label.configure(text=issue_description)

        # 更新统计信息
        self.stats_label.configure(text=f"{current}/{self.total_issues}个问题")

    def _on_show_details(self):
        """显示详情按钮点击事件"""
        # 这里可以显示详细的优化日志
        pass

    def _on_cancel(self):
        """取消按钮点击事件"""
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.destroy()
