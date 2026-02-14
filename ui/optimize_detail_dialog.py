# ui/optimize_detail_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录优化详情对话框UI类
"""
import customtkinter as ctk


class OptimizeDetailDialog(ctk.CTkToplevel):
    """
    章节目录优化详情对话框的UI类
    显示单个问题的详细信息和优化方案
    """

    def __init__(self, master, issue, solutions, on_apply_solution_callback=None):
        """
        初始化对话框

        参数:
            master: 父窗口
            issue: 问题字典
            solutions: 优化方案列表
            on_apply_solution_callback: 应用方案回调函数
        """
        super().__init__(master)

        self.master = master
        self.issue = issue
        self.solutions = solutions
        self.on_apply_solution_callback = on_apply_solution_callback

        # 当前选中的方案索引
        self.selected_solution_index = ctk.IntVar(value=0)

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("优化详情")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 700) // 2
        y = (screen_height - 600) // 2

        # 设置窗口位置和大小
        self.geometry(f'700x600+{x}+{y}')

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
        self.minsize(600, 500)

        # 设置窗口为模态
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 问题信息区
        self._create_issue_info_area()

        # 优化方案区
        self._create_solutions_area()

        # 按钮区
        self._create_button_area()

    def _create_issue_info_area(self):
        """创建问题信息区"""
        info_frame = ctk.CTkFrame(self.main_container)
        info_frame.pack(fill="x", pady=(0, 10))

        # 问题类型
        type_label = ctk.CTkLabel(
            info_frame,
            text=f"问题类型：{self.issue.get('type', '未知')}",
            font=("Microsoft YaHei", 11)
        )
        type_label.pack(anchor="w", padx=10, pady=(10, 5))

        # 严重程度
        severity = self.issue.get('severity', '提示')
        severity_colors = {
            "错误": ("red", "red"),
            "警告": ("orange", "orange"),
            "提示": ("blue", "blue")
        }
        severity_color = severity_colors.get(severity, ("black", "white"))

        severity_label = ctk.CTkLabel(
            info_frame,
            text=f"严重程度：{severity}",
            font=("Microsoft YaHei", 11),
            text_color=severity_color[0]
        )
        severity_label.pack(anchor="w", padx=10, pady=5)

        # 影响章节
        chapter_label = ctk.CTkLabel(
            info_frame,
            text=f"影响章节：第{self.issue.get('chapter', 0)}章",
            font=("Microsoft YaHei", 11)
        )
        chapter_label.pack(anchor="w", padx=10, pady=5)

        # 问题描述
        ctk.CTkLabel(
            info_frame,
            text="问题描述：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        description_text = ctk.CTkTextbox(
            info_frame,
            height=80,
            font=("Microsoft YaHei", 10)
        )
        description_text.pack(fill="x", padx=10, pady=(0, 10))
        description_text.insert("end", self.issue.get('description', ''))
        description_text.configure(state="disabled")

    def _create_solutions_area(self):
        """创建优化方案区"""
        solutions_frame = ctk.CTkFrame(self.main_container)
        solutions_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            solutions_frame,
            text="优化方案：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 创建滚动区域
        scroll_frame = ctk.CTkScrollableFrame(solutions_frame, height=150)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 显示每个方案
        for i, solution in enumerate(self.solutions):
            # 创建单选按钮
            radio_btn = ctk.CTkRadioButton(
                scroll_frame,
                text=f"方案{i+1}：{solution.get('title', '')}",
                variable=self.selected_solution_index,
                value=i,
                font=("Microsoft YaHei", 10)
            )
            radio_btn.pack(anchor="w", pady=5)

            # 创建方案描述
            desc_text = ctk.CTkTextbox(
                scroll_frame,
                height=60,
                font=("Microsoft YaHei", 9)
            )
            desc_text.pack(fill="x", padx=20, pady=(0, 10))
            desc_text.insert("end", solution.get('description', ''))
            desc_text.configure(state="disabled")

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0), ipady=10)

        # 左侧按钮容器
        left_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_button_frame.pack(side="left", padx=10, pady=10)

        # 上一个问题按钮
        self.btn_previous = ctk.CTkButton(
            left_button_frame,
            text="上一个",
            command=self._on_previous,
            font=("Microsoft YaHei", 10),
            width=120,
            height=35
        )
        self.btn_previous.pack(side="left", padx=5)

        # 下一个问题按钮
        self.btn_next = ctk.CTkButton(
            left_button_frame,
            text="下一个",
            command=self._on_next,
            font=("Microsoft YaHei", 10),
            width=120,
            height=35
        )
        self.btn_next.pack(side="left", padx=5)

        # 右侧按钮容器
        right_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_button_frame.pack(side="right", padx=10, pady=10)

        # 关闭按钮
        self.btn_close = ctk.CTkButton(
            right_button_frame,
            text="关闭",
            command=self._on_close,
            font=("Microsoft YaHei", 10),
            width=120,
            height=35
        )
        self.btn_close.pack(side="right", padx=5)

        # 应用方案按钮
        if self.on_apply_solution_callback:
            self.btn_apply = ctk.CTkButton(
                right_button_frame,
                text="应用方案",
                command=self._on_apply_solution,
                font=("Microsoft YaHei", 10),
                fg_color=("#28a745", "#28a745"),
                hover_color=("#218838", "#218838"),
                text_color_disabled="gray",
                width=140,
                height=35
            )
            self.btn_apply.pack(side="right", padx=5)

    def _on_previous(self):
        """上一个按钮点击事件"""
        # 这里可以导航到上一个问题
        pass

    def _on_next(self):
        """下一个按钮点击事件"""
        # 这里可以导航到下一个问题
        pass

    def _on_apply_solution(self):
        """应用方案按钮点击事件"""
        if self.on_apply_solution_callback:
            index = self.selected_solution_index.get()
            if 0 <= index < len(self.solutions):
                self.on_apply_solution_callback(self.issue, self.solutions[index])
        self.destroy()

    def _on_close(self):
        """关闭按钮点击事件"""
        self.destroy()
