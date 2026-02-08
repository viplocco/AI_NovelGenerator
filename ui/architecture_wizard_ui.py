# ui/architecture_wizard_ui.py
# -*- coding: utf-8 -*-
"""
小说架构生成向导UI类
"""
import os
import threading
import customtkinter as ctk
from tkinter import messagebox
from novel_generator.architecture_wizard import (
    ArchitectureWizardLogic,
    STEP_USER_GUIDANCE,
    STEPS,
    STEP_NAMES
)

class ArchitectureWizardUI(ctk.CTkToplevel):
    """
    小说架构生成向导的UI类
    提供分步骤生成小说架构的界面
    """

    def __init__(
        self,
        master,
        interface_format: str,
        api_key: str,
        base_url: str,
        llm_model: str,
        topic: str,
        genre: str,
        number_of_chapters: int,
        word_number: int,
        filepath: str,
        global_guidance: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 600,
        on_complete: callable = None
    ):
        """
        初始化向导弹窗

        参数:
            master: 父窗口
            interface_format: LLM接口格式
            api_key: API密钥
            base_url: API基础URL
            llm_model: 模型名称
            topic: 小说主题
            genre: 小说类型
            number_of_chapters: 章节数
            word_number: 每章字数
            filepath: 保存路径
            global_guidance: 全局用户指导
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            on_complete: 完成回调函数
        """
        super().__init__(master)

        self.master = master
        self.on_complete = on_complete

        # 初始化逻辑类
        self.wizard_logic = ArchitectureWizardLogic(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            llm_model=llm_model,
            topic=topic,
            genre=genre,
            number_of_chapters=number_of_chapters,
            word_number=word_number,
            filepath=filepath,
            global_guidance=global_guidance,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            on_stream_callback=self._on_stream_output
        )

        # 当前步骤索引
        self.current_step_index = 0
        self.is_generating = False
        self.generation_thread = None

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

        # 加载第一步
        self._load_step(0)

    def _setup_window(self):
        """设置窗口属性"""
        self.title("小说架构生成向导")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 900) // 2
        y = (screen_height - 700) // 2

        # 一次性设置窗口位置和大小
        self.geometry(f'900x700+{x}+{y}')

        # 设置窗口图标（如果存在）
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # 如果图标加载失败，继续执行

        # 允许调整大小和最大化
        self.resizable(True, True)
        self.maxsize(screen_width, screen_height)

        # 设置最小尺寸
        self.minsize(600, 500)

        # 设置窗口为模态（但不使用transient，以保留标题栏按钮）
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 步骤导航区
        self._create_step_navigation()

        # 内容区
        self._create_content_area()

        # 按钮区
        self._create_button_area()

    def _create_step_navigation(self):
        """创建步骤导航区"""
        nav_frame = ctk.CTkFrame(self.main_container)
        nav_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            nav_frame,
            text="步骤导航：",
            font=("Microsoft YaHei", 12)
        ).pack(side="left", padx=(10, 5))

        # 创建步骤标签
        self.step_labels = []
        for i, step_key in enumerate(STEPS):
            step_name = STEP_NAMES.get(step_key, step_key)

            # 创建步骤标签
            label = ctk.CTkLabel(
                nav_frame,
                text=f"[{step_name}]",
                font=("Microsoft YaHei", 10),
                fg_color="gray",
                text_color="white",
                corner_radius=5
            )
            label.pack(side="left", padx=2)
            self.step_labels.append(label)

            # 添加箭头（最后一个步骤除外）
            if i < len(STEPS) - 1:
                arrow = ctk.CTkLabel(
                    nav_frame,
                    text="→",
                    font=("Microsoft YaHei", 12)
                )
                arrow.pack(side="left", padx=2)

    def _create_content_area(self):
        """创建内容区"""
        content_frame = ctk.CTkFrame(self.main_container)
        content_frame.pack(fill="both", expand=True)

        # 当前步骤标题
        self.step_title = ctk.CTkLabel(
            content_frame,
            text="",
            font=("Microsoft YaHei", 14, "bold")
        )
        self.step_title.pack(anchor="w", padx=10, pady=(10, 5))

        # 用户指导区
        guidance_frame = ctk.CTkFrame(content_frame)
        guidance_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            guidance_frame,
            text="用户指导（可编辑）",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=5, pady=(5, 2))

        self.guidance_text = ctk.CTkTextbox(
            guidance_frame,
            height=100,
            font=("Microsoft YaHei", 12)
        )
        self.guidance_text.pack(fill="x", padx=5, pady=(0, 5))

        # 绑定焦点事件，用于显示/隐藏占位符
        self.guidance_text.bind("<FocusIn>", self._on_guidance_focus_in)
        self.guidance_text.bind("<FocusOut>", self._on_guidance_focus_out)

        # 生成结果区
        result_frame = ctk.CTkFrame(content_frame)
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(
            result_frame,
            text="生成结果（可编辑）",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=5, pady=(5, 2))

        self.result_text = ctk.CTkTextbox(
            result_frame,
            font=("Microsoft YaHei", 13)
        )
        self.result_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # 进度指示器
        self.progress_frame = ctk.CTkFrame(content_frame)
        self.progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=("Microsoft YaHei", 10)
        )
        self.progress_label.pack(side="left", padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=200
        )
        self.progress_bar.pack(side="left", padx=5, pady=5)
        self.progress_bar.set(0)

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0))

        # 上一步按钮
        self.btn_prev = ctk.CTkButton(
            button_frame,
            text="上一步",
            command=self._on_prev_step,
            font=("Microsoft YaHei", 11),
            fg_color=("#1f6aa5", "#3c3c3c"),
            hover_color=("#164e7e", "#3c3c3c"),
            text_color_disabled="gray"
        )
        self.btn_prev.pack(side="left", padx=5, pady=10)

        # 开始生成/重新生成按钮
        self.btn_generate = ctk.CTkButton(
            button_frame,
            text="开始生成",
            command=self._on_generate,
            font=("Microsoft YaHei", 11),
            fg_color=("#1f6aa5", "#3c3c3c"),
            hover_color=("#164e7e", "#3c3c3c"),
            text_color_disabled="gray"
        )
        self.btn_generate.pack(side="left", padx=5, pady=10)

        # 下一步按钮
        self.btn_next = ctk.CTkButton(
            button_frame,
            text="下一步",
            command=self._on_next_step,
            font=("Microsoft YaHei", 11),
            fg_color=("#1f6aa5", "#3c3c3c"),
            hover_color=("#164e7e", "#3c3c3c"),
            text_color_disabled="gray"
        )
        self.btn_next.pack(side="left", padx=5, pady=10)

        # 完成按钮
        self.btn_complete = ctk.CTkButton(
            button_frame,
            text="完成",
            command=self._on_complete,
            font=("Microsoft YaHei", 11),
            fg_color=("#1f6aa5", "#3c3c3c"),
            hover_color=("#164e7e", "#3c3c3c"),
            text_color_disabled="gray"
        )
        self.btn_complete.pack(side="right", padx=5, pady=10)

        # 取消按钮
        self.btn_cancel = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self._on_cancel,
            font=("Microsoft YaHei", 11)
        )
        self.btn_cancel.pack(side="right", padx=5, pady=10)

    def _load_step(self, step_index: int):
        """
        加载指定步骤的内容

        参数:
            step_index: 步骤索引
        """
        # 更新当前步骤索引
        self.current_step_index = step_index
        step_key = STEPS[step_index]
        step_name = STEP_NAMES.get(step_key, step_key)

        # 更新步骤标题
        self.step_title.configure(
            text=f"当前步骤：第{step_index + 1}步/共{len(STEPS)}步 - {step_name}"
        )

        # 加载用户指导
        guidance = self.wizard_logic.get_step_guidance(step_key)
        format_hint = STEP_USER_GUIDANCE.get(step_key, "")
        self.guidance_text.delete("0.0", "end")

        if guidance.strip():
            # 如果有用户修改的指导，直接显示
            self.guidance_text.insert("0.0", guidance)
        else:
            # 如果没有用户修改，显示系统默认的用户内容要求（正常颜色，不是占位符）
            self.guidance_text.insert("0.0", format_hint)

        # 加载生成结果
        result = self.wizard_logic.get_step_result(step_key)
        self.result_text.delete("0.0", "end")

        # 如果结果为空，不显示任何内容
        if result.strip():
            self.result_text.insert("0.0", result)
        else:
            # 如果结果为空，且步骤已完成，说明是从保存的数据加载的
            # 保持结果框为空，等待重新生成
            pass

        # 更新步骤导航状态
        self._update_step_navigation()

        # 更新按钮状态（包括生成按钮的文本）
        self._update_button_state()

    def _update_step_navigation(self):
        """更新步骤导航状态"""
        for i, label in enumerate(self.step_labels):
            step_key = STEPS[i]
            status = self.wizard_logic.get_step_status(step_key)

            # 根据状态设置颜色
            if i == self.current_step_index:
                # 当前步骤
                label.configure(fg_color="#1f6aa5")  # 蓝色
            elif status == "completed":
                # 已完成
                label.configure(fg_color="#2CC985")  # 绿色
            elif status == "modified":
                # 已修改
                label.configure(fg_color="#FFA500")  # 橙色
            else:
                # 待执行
                label.configure(fg_color="gray")

    def _update_button_state(self):
        """更新按钮状态"""
        # 上一步按钮
        self.btn_prev.configure(
            state="normal" if self.current_step_index > 0 else "disabled"
        )

        # 开始生成/重新生成按钮
        step_key = STEPS[self.current_step_index]
        status = self.wizard_logic.get_step_status(step_key)

        # 根据当前步骤的状态更新按钮文本
        if status == "pending":
            self.btn_generate.configure(
                text="开始生成",
                state="normal" if not self.is_generating else "disabled"
            )
        else:
            self.btn_generate.configure(
                text="重新生成",
                state="normal" if not self.is_generating else "disabled"
            )

        # 下一步按钮
        is_last_step = self.current_step_index == len(STEPS) - 1
        self.btn_next.configure(
            state="normal" if not is_last_step and status != "pending" and not self.is_generating else "disabled"
        )

        # 完成按钮
        all_completed = all(
            self.wizard_logic.get_step_status(step) != "pending"
            for step in STEPS
        )
        self.btn_complete.configure(
            state="normal" if all_completed and not self.is_generating else "disabled"
        )

        # 取消按钮
        self.btn_cancel.configure(
            state="disabled" if self.is_generating else "normal"
        )

    def _on_generate(self):
        """处理开始生成/重新生成按钮点击"""
        if self.is_generating:
            return

        # 保存当前步骤的用户指导
        self._save_current_guidance()

        # 确认重新生成
        step_key = STEPS[self.current_step_index]
        status = self.wizard_logic.get_step_status(step_key)

        if status != "pending":
            if not messagebox.askyesno(
                "确认",
                "确定要重新生成当前步骤的内容吗？"
            ):
                return

        # 开始生成
        self._start_generation()

    def _on_prev_step(self):
        """处理上一步按钮点击"""
        if self.is_generating:
            return

        if self.current_step_index > 0:
            # 保存当前步骤的用户指导和结果
            self._save_current_guidance()
            self._save_current_result()

            # 加载上一步
            self._load_step(self.current_step_index - 1)

    def _on_next_step(self):
        """处理下一步按钮点击"""
        if self.is_generating:
            return

        # 保存当前步骤的用户指导和结果
        self._save_current_guidance()
        self._save_current_result()

        # 检查当前步骤是否完成
        step_key = STEPS[self.current_step_index]
        status = self.wizard_logic.get_step_status(step_key)

        if status == "pending":
            messagebox.showwarning(
                "提示",
                "请先生成当前步骤的内容"
            )
            return

        # 进入下一步
        next_index = self.current_step_index + 1
        if next_index < len(STEPS):
            self._load_step(next_index)

    def _on_complete(self):
        """处理完成按钮点击"""
        if self.is_generating:
            return

        # 保存当前步骤的用户指导
        self._save_current_guidance()

        # 保存所有步骤的用户指导
        self._save_all_guidance()

        # 确认完成
        if not messagebox.askyesno(
            "确认",
            "确定要完成并保存所有步骤的内容吗？"
        ):
            return

        # 保存最终结果
        self._save_final_result()

        # 调用完成回调（传递成功标志）
        if self.on_complete:
            self.on_complete(success=True)

        # 关闭弹窗
        self.destroy()

    def _on_cancel(self):
        """处理取消按钮点击"""
        if self.is_generating:
            return

        # 确认取消
        if not messagebox.askyesno(
            "确认",
            "确定要取消吗？已生成的内容将保存到partial_architecture.json"
        ):
            return

        # 保存部分数据
        self.wizard_logic._save_partial_data()

        # 调用完成回调来恢复按钮状态（传递失败标志）
        if self.on_complete:
            self.on_complete(success=False)

        # 关闭弹窗
        self.destroy()

    def _save_current_guidance(self):
        """保存当前步骤的用户指导"""
        step_key = STEPS[self.current_step_index]
        current_text = self.guidance_text.get("0.0", "end-1c")

        # 检查是否为占位符文本
        tags = self.guidance_text.tag_names("0.0")
        if "placeholder" in tags:
            # 如果是占位符，保存空字符串（表示用户没有修改）
            self.wizard_logic.set_step_guidance(step_key, "")
            return

        # 保存用户修改后的内容
        if current_text.strip():
            self.wizard_logic.set_step_guidance(step_key, current_text.strip())
        else:
            # 如果用户清空了内容，保存空字符串
            self.wizard_logic.set_step_guidance(step_key, "")

    def _save_all_guidance(self):
        """保存所有步骤的用户指导"""
        # 先保存当前步骤
        self._save_current_guidance()
        # 其他步骤的指导已经在逻辑类中管理，无需重复保存

    def _save_current_result(self):
        """保存当前步骤的生成结果"""
        step_key = STEPS[self.current_step_index]
        result = self.result_text.get("0.0", "end-1c").strip()
        self.wizard_logic.set_step_result(step_key, result)

    def _save_final_result(self):
        """保存最终结果到Novel_architecture.txt"""
        # 保存所有步骤的结果
        self._save_current_result()

        # 构建最终内容
        core_seed = self.wizard_logic.get_step_result("core_seed")
        character_design = self.wizard_logic.get_step_result("character_design")
        character_state = self.wizard_logic.get_step_result("character_state")
        world_building = self.wizard_logic.get_step_result("world_building")
        plot_arch = self.wizard_logic.get_step_result("plot_architecture")

        final_content = (
            "#=== 0) 小说设定 ===\n"
            f"主题：{self.wizard_logic.topic},类型：{self.wizard_logic.genre},"
            f"篇幅：约{self.wizard_logic.number_of_chapters}章（每章{self.wizard_logic.word_number}字）\n\n"
            "#=== 1) 核心种子 ===\n"
            f"{core_seed}\n\n"
            "#=== 2) 世界观 ===\n"
            f"{world_building}\n\n"
            "#=== 3) 角色动力学 ===\n"
            f"{character_design}\n\n"
            "#=== 3.1) 角色状态表 ===\n"
            f"{character_state}\n\n"
            "#=== 4) 三幕式情节架构 ===\n"
            f"{plot_arch}\n"
        )

        # 保存到文件
        arch_file = os.path.join(self.wizard_logic.filepath, "Novel_architecture.txt")
        from utils import clear_file_content, save_string_to_txt
        clear_file_content(arch_file)
        save_string_to_txt(final_content, arch_file)

        # 不删除partial_architecture.json，以便下次打开时可以回填数据

    def _start_generation(self):
        """开始生成当前步骤"""
        if self.is_generating:
            return

        # 检查步骤依赖
        step_key = STEPS[self.current_step_index]
        if not self.wizard_logic.check_step_dependencies(step_key):
            messagebox.showwarning(
                "提示",
                "前置步骤尚未完成，请先完成前置步骤"
            )
            return

        # 保存当前步骤的用户指导
        self._save_current_guidance()

        # 检查是否为占位符文本
        tags = self.guidance_text.tag_names("0.0")
        if "placeholder" in tags:
            # 如果是占位符，清除占位符文本
            self.guidance_text.delete("0.0", "end")
            self.guidance_text.tag_remove("placeholder", "0.0", "end")

        # 标记为生成中
        self.is_generating = True

        # 立即更新按钮状态，禁用所有按钮
        self._update_button_state()

        # 清空结果文本框
        self.result_text.delete("0.0", "end")

        # 添加初始提示信息
        self.result_text.insert("end", "正在连接LLM，请稍候...\n\n")

        # 更新进度标签
        self.progress_label.configure(text="正在连接LLM...")
        self.progress_bar.set(0)

        # 创建生成线程
        self.generation_thread = threading.Thread(
            target=self._generate_step,
            daemon=True
        )
        self.generation_thread.start()

    def _generate_step(self):
        """在后台线程中生成当前步骤"""
        step_key = STEPS[self.current_step_index]

        try:
            # 更新进度标签为"生成中"
            self.master.after(0, lambda: self.progress_label.configure(text="生成中..."))

            # 生成步骤
            success = self.wizard_logic.generate_step(
                step_key,
                stream_callback=self._on_stream_output
            )

            if success:
                # 更新进度
                self.master.after(0, lambda: self.progress_bar.set(1))
                self.master.after(0, lambda: self.progress_label.configure(text="生成完成"))
                # 保存生成结果
                self.master.after(0, self._save_current_result)
                # 更新步骤状态
                step_key = STEPS[self.current_step_index]
                def update_status():
                    self.wizard_logic.step_data[step_key]["status"] = "completed"
                self.master.after(0, update_status)
            else:
                self.master.after(0, lambda: self.progress_label.configure(text="生成失败"))
                self.master.after(0, lambda: messagebox.showerror("错误", "生成失败，请重试"))

        except Exception as e:
            self.master.after(0, lambda: self.progress_label.configure(text="生成失败"))
            self.master.after(0, lambda: messagebox.showerror("错误", f"生成失败: {str(e)}"))

        finally:
            # 标记为非生成中
            self.is_generating = False
            # 更新所有UI状态
            self.master.after(0, self._update_button_state)
            self.master.after(0, self._update_step_navigation)

    def _on_stream_output(self, text: str):
        """处理流式输出"""
        # 在主线程中更新UI
        if text:  # 确保文本不为空
            # 移除初始提示信息（第一次收到流式输出时）
            if "正在连接LLM，请稍候..." in self.result_text.get("0.0", "end"):
                self.result_text.delete("0.0", "end")

            # 插入新文本
            self.result_text.insert("end", text)
            # 确保滚动到最新位置
            self.result_text.see("end")

    def _on_guidance_focus_in(self, event):
        """用户指导输入框获得焦点时的处理"""
        # 检查是否为占位符状态
        tags = self.guidance_text.tag_names("0.0")
        if "placeholder" in tags:
            # 清除占位符文本
            self.guidance_text.delete("0.0", "end")
            # 移除占位符标签
            self.guidance_text.tag_remove("placeholder", "0.0", "end")
        # 如果不是占位符，用户可以直接编辑内容

    def _on_guidance_focus_out(self, event):
        """用户指导输入框失去焦点时的处理"""
        # 获取当前文本
        current_text = self.guidance_text.get("0.0", "end-1c").strip()

        if not current_text:
            # 如果文本为空，显示占位符
            step_key = STEPS[self.current_step_index]
            format_hint = STEP_USER_GUIDANCE.get(step_key, "")
            self.guidance_text.insert("0.0", format_hint)
            # 标记为占位符状态
            self.guidance_text.tag_config("placeholder", foreground="gray")
            self.guidance_text.tag_add("placeholder", "0.0", "end")
        else:
            # 保存当前用户指导
            self._save_current_guidance()

    def _has_unsaved_changes(self):
        """检查是否有未保存的修改"""
        # 检查当前步骤的用户指导是否有修改
        step_key = STEPS[self.current_step_index]
        current_text = self.guidance_text.get("0.0", "end-1c")
        saved_guidance = self.wizard_logic.get_step_guidance(step_key)

        # 检查是否为占位符文本
        tags = self.guidance_text.tag_names("0.0")
        is_placeholder = "placeholder" in tags

        # 如果是占位符，没有修改
        if is_placeholder:
            return False

        # 检查文本是否与保存的指导一致
        if current_text.strip() != saved_guidance.strip():
            return True

        # 检查是否有已生成但未保存的结果
        result = self.result_text.get("0.0", "end-1c")
        saved_result = self.wizard_logic.get_step_result(step_key)
        if result.strip() != saved_result.strip():
            return True

        return False

    def protocol_handler(self):
        """处理窗口关闭事件"""
        if self.is_generating:
            # 正在生成中，确认是否关闭
            if not messagebox.askyesno(
                "确认",
                "正在生成中，确定要关闭吗？"
            ):
                return
        else:
            # 检查是否有未保存的修改
            if self._has_unsaved_changes():
                # 有未保存的修改，提示保存
                response = messagebox.askyesnocancel(
                    "保存修改",
                    "检测到有未保存的修改，是否保存？\n\n是：保存并关闭\n否：不保存直接关闭\n取消：返回继续编辑"
                )
                if response is None:  # 取消
                    return
                elif response:  # 是，保存
                    self._save_current_guidance()
                    self._save_current_result()
                    # 保存部分数据（如果有）
                    self.wizard_logic._save_partial_data()
                # 否：不保存，直接关闭
            else:
                # 没有未保存的修改，直接关闭（无论是否有已生成的数据）
                pass

        # 调用完成回调来恢复按钮状态
        if self.on_complete:
            self.on_complete(success=False)

        # 关闭窗口
        self.destroy()

    # 重写窗口关闭协议
    def destroy(self):
        """销毁窗口"""
        if hasattr(self, 'generation_thread') and self.generation_thread and self.generation_thread.is_alive():
            # 等待生成线程结束
            self.generation_thread.join(timeout=1.0)
        super().destroy()
