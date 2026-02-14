# ui/optimize_result_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录优化结果对话框UI类
"""
import customtkinter as ctk


class OptimizeResultDialog(ctk.CTkToplevel):
    """
    章节目录优化结果对话框的UI类
    显示优化结果统计和操作选项
    """

    def __init__(self, master, optimization_results, on_apply_callback=None, on_cancel_callback=None):
        """
        初始化对话框

        参数:
            master: 父窗口
            optimization_results: 优化结果字典，包含各类型问题的处理统计
            on_apply_callback: 应用修改回调函数
            on_cancel_callback: 取消回调函数
        """
        super().__init__(master)

        self.master = master
        self.optimization_results = optimization_results
        self.on_apply_callback = on_apply_callback
        self.on_cancel_callback = on_cancel_callback

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("优化结果")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 600) // 2
        y = (screen_height - 500) // 2

        # 设置窗口位置和大小
        self.geometry(f'600x500+{x}+{y}')

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
        self.minsize(500, 400)

        # 设置窗口为模态
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 结果概要区
        self._create_summary_area()

        # 修复统计区
        self._create_stats_area()

        # 按钮区
        self._create_button_area()

    def _create_summary_area(self):
        """创建结果概要区"""
        summary_frame = ctk.CTkFrame(self.main_container)
        summary_frame.pack(fill="x", pady=(0, 10))

        # 计算总处理数
        total_processed = sum(
            result.get("processed", 0) 
            for result in self.optimization_results.values()
        )
        total_issues = sum(
            result.get("total", 0) 
            for result in self.optimization_results.values()
        )

        # 显示结果概要
        ctk.CTkLabel(
            summary_frame,
            text=f"✓ 优化完成！共处理{total_processed}/{total_issues}个问题",
            font=("Microsoft YaHei", 12, "bold")
        ).pack(padx=10, pady=10)

    def _create_stats_area(self):
        """创建修复统计区"""
        stats_frame = ctk.CTkFrame(self.main_container)
        stats_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            stats_frame,
            text="修复统计：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # 创建滚动区域
        scroll_frame = ctk.CTkScrollableFrame(stats_frame, height=200)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 显示各类型问题的统计
        type_names = {
            "cultivation": "修为变化问题",
            "spatial": "场景变化问题",
            "chapter_info": "章节信息问题",
            "character": "角色一致性问题",
            "plot": "剧情连贯性问题"
        }

        for issue_type, result in self.optimization_results.items():
            type_name = type_names.get(issue_type, issue_type)
            processed = result.get("processed", 0)
            total = result.get("total", 0)
            percentage = int((processed / total * 100)) if total > 0 else 0

            ctk.CTkLabel(
                scroll_frame,
                text=f"• {type_name}：{processed}/{total} ({percentage}%)",
                font=("Microsoft YaHei", 10)
            ).pack(anchor="w", pady=2)

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0), ipady=10)

        # 左侧按钮容器
        left_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_button_frame.pack(side="left", padx=10, pady=10)

        # 查看优化详情按钮
        self.btn_details = ctk.CTkButton(
            left_button_frame,
            text="查看优化详情",
            command=self._on_view_details,
            font=("Microsoft YaHei", 10),
            width=140,
            height=35
        )
        self.btn_details.pack(side="left", padx=5)

        # 查看对比按钮
        self.btn_comparison = ctk.CTkButton(
            left_button_frame,
            text="查看对比",
            command=self._on_view_comparison,
            font=("Microsoft YaHei", 10),
            width=120,
            height=35
        )
        self.btn_comparison.pack(side="left", padx=5)

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

    def _on_view_details(self):
        """查看优化详情按钮点击事件"""
        # 这里可以打开优化详情对话框
        pass

    def _on_view_comparison(self):
        """查看对比按钮点击事件"""
        # 这里可以打开优化对比对话框
        pass

    def _on_apply(self):
        """应用修改按钮点击事件"""
        if self.on_apply_callback:
            self.on_apply_callback(self.optimization_results)
        self.destroy()

    def _on_cancel(self):
        """取消按钮点击事件"""
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.destroy()
