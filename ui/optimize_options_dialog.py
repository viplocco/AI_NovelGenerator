# ui/optimize_options_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录优化选项对话框UI类
"""
import customtkinter as ctk
from tkinter import messagebox


class OptimizeOptionsDialog(ctk.CTkToplevel):
    """
    章节目录优化选项对话框的UI类
    提供优化模式、优化范围和高级选项的设置界面
    """

    def __init__(self, master, issues, on_optimize_callback):
        """
        初始化对话框

        参数:
            master: 父窗口
            issues: 检测到的问题列表
            on_optimize_callback: 优化回调函数，接收优化参数
        """
        super().__init__(master)

        self.master = master
        self.issues = issues
        self.on_optimize_callback = on_optimize_callback

        # 优化模式
        self.optimize_mode = ctk.StringVar(value="smart")  # smart(智能), interactive(交互), manual(手动)

        # 优化范围选项
        self.optimize_ranges = {
            "cultivation": ctk.BooleanVar(value=True),
            "spatial": ctk.BooleanVar(value=True),
            "chapter_info": ctk.BooleanVar(value=True),
            "character": ctk.BooleanVar(value=True),
            "plot": ctk.BooleanVar(value=True)
        }

        # 高级选项
        self.advanced_options = {
            "backup": ctk.BooleanVar(value=True),
            "show_comparison": ctk.BooleanVar(value=True),
            "generate_log": ctk.BooleanVar(value=True)
        }

        # 统计各类型问题数量
        self.issue_counts = self._count_issues_by_type()

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("章节目录优化选项")

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

        # 优化模式区
        self._create_optimize_mode_area()

        # 优化范围区
        self._create_optimize_range_area()

        # 高级选项区
        self._create_advanced_options_area()

        # 按钮区
        self._create_button_area()

    def _create_optimize_mode_area(self):
        """创建优化模式区"""
        mode_frame = ctk.CTkFrame(self.main_container)
        mode_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            mode_frame,
            text="优化模式：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 智能优化
        ctk.CTkRadioButton(
            mode_frame,
            text="智能优化（推荐）- 使用AI自动修复所有问题",
            variable=self.optimize_mode,
            value="smart",
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 交互优化
        ctk.CTkRadioButton(
            mode_frame,
            text="交互优化 - 逐个确认每个问题的修复方案",
            variable=self.optimize_mode,
            value="interactive",
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 手动优化
        ctk.CTkRadioButton(
            mode_frame,
            text="手动优化 - 仅提供修复建议，由用户手动修改",
            variable=self.optimize_mode,
            value="manual",
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

    def _create_optimize_range_area(self):
        """创建优化范围区"""
        range_frame = ctk.CTkFrame(self.main_container)
        range_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            range_frame,
            text="优化范围：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 修为变化问题
        ctk.CTkCheckBox(
            range_frame,
            text=f"修为变化问题 ({self.issue_counts.get('cultivation', 0)}个)",
            variable=self.optimize_ranges["cultivation"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 场景变化问题
        ctk.CTkCheckBox(
            range_frame,
            text=f"场景变化问题 ({self.issue_counts.get('spatial', 0)}个)",
            variable=self.optimize_ranges["spatial"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 章节信息问题
        ctk.CTkCheckBox(
            range_frame,
            text=f"章节信息问题 ({self.issue_counts.get('chapter_info', 0)}个)",
            variable=self.optimize_ranges["chapter_info"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 角色一致性问题
        ctk.CTkCheckBox(
            range_frame,
            text=f"角色一致性问题 ({self.issue_counts.get('character', 0)}个)",
            variable=self.optimize_ranges["character"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 剧情连贯性问题
        ctk.CTkCheckBox(
            range_frame,
            text=f"剧情连贯性问题 ({self.issue_counts.get('plot', 0)}个)",
            variable=self.optimize_ranges["plot"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

    def _create_advanced_options_area(self):
        """创建高级选项区"""
        adv_frame = ctk.CTkFrame(self.main_container)
        adv_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            adv_frame,
            text="高级选项：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 优化前自动备份原始目录
        ctk.CTkCheckBox(
            adv_frame,
            text="优化前自动备份原始目录",
            variable=self.advanced_options["backup"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 显示优化前后对比
        ctk.CTkCheckBox(
            adv_frame,
            text="显示优化前后对比",
            variable=self.advanced_options["show_comparison"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

        # 生成优化日志
        ctk.CTkCheckBox(
            adv_frame,
            text="生成优化日志",
            variable=self.advanced_options["generate_log"],
            font=("Microsoft YaHei", 10)
        ).pack(anchor="w", padx=20, pady=2)

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0), ipady=10)

        # 左侧按钮容器
        left_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_button_frame.pack(side="left", padx=10, pady=10)

        # 全选按钮
        ctk.CTkButton(
            left_button_frame,
            text="全选",
            command=self._on_select_all,
            font=("Microsoft YaHei", 10),
            width=100,
            height=35
        ).pack(side="left", padx=5)

        # 全不选按钮
        ctk.CTkButton(
            left_button_frame,
            text="全不选",
            command=self._on_deselect_all,
            font=("Microsoft YaHei", 10),
            width=100,
            height=35
        ).pack(side="left", padx=5)

        # 右侧按钮容器
        right_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_button_frame.pack(side="right", padx=10, pady=10)

        # 取消按钮
        ctk.CTkButton(
            right_button_frame,
            text="取消",
            command=self._on_cancel,
            font=("Microsoft YaHei", 10),
            width=100,
            height=35
        ).pack(side="right", padx=5)

        # 开始优化按钮
        self.btn_optimize = ctk.CTkButton(
            right_button_frame,
            text="开始优化",
            command=self._on_start_optimize,
            font=("Microsoft YaHei", 10),
            fg_color=("#28a745", "#28a745"),
            hover_color=("#218838", "#218838"),
            text_color_disabled="gray",
            width=120,
            height=35
        ).pack(side="right", padx=5)

    def _count_issues_by_type(self):
        """统计各类型问题的数量"""
        counts = {
            "cultivation": 0,
            "spatial": 0,
            "chapter_info": 0,
            "character": 0,
            "plot": 0
        }

        for issue in self.issues:
            issue_type = issue.get("type", "")
            if issue_type in counts:
                counts[issue_type] += 1

        return counts

    def _on_select_all(self):
        """全选按钮点击事件"""
        for var in self.optimize_ranges.values():
            var.set(True)

    def _on_deselect_all(self):
        """全不选按钮点击事件"""
        for var in self.optimize_ranges.values():
            var.set(False)

    def _on_start_optimize(self):
        """开始优化按钮点击事件"""
        # 检查是否至少选择了一个优化范围
        if not any(var.get() for var in self.optimize_ranges.values()):
            messagebox.showwarning("提示", "请至少选择一个优化范围")
            return

        # 收集优化参数
        optimize_params = {
            "mode": self.optimize_mode.get(),
            "ranges": {
                "cultivation": self.optimize_ranges["cultivation"].get(),
                "spatial": self.optimize_ranges["spatial"].get(),
                "chapter_info": self.optimize_ranges["chapter_info"].get(),
                "character": self.optimize_ranges["character"].get(),
                "plot": self.optimize_ranges["plot"].get()
            },
            "advanced": {
                "backup": self.advanced_options["backup"].get(),
                "show_comparison": self.advanced_options["show_comparison"].get(),
                "generate_log": self.advanced_options["generate_log"].get()
            }
        }

        # 调用优化回调
        if self.on_optimize_callback:
            self.on_optimize_callback(optimize_params)

        # 关闭对话框
        self.destroy()

    def _on_cancel(self):
        """取消按钮点击事件"""
        self.destroy()
