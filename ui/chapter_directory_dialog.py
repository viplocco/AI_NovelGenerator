
# ui/chapter_directory_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录生成对话框UI类
"""
import os
import threading
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content

class ChapterDirectoryDialog(ctk.CTkToplevel):
    """
    章节目录生成对话框的UI类
    提供章节目录生成的界面，支持流式输出和数据持久化
    """

    def __init__(
        self,
        master,
        max_chapters: int,
        filepath: str,
        interface_format: str = "",
        api_key: str = "",
        base_url: str = "",
        llm_model: str = "",
        number_of_chapters: int = 10,
        user_guidance: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 600,
        on_complete: callable = None
    ):
        """
        初始化对话框

        参数:
            master: 父窗口
            max_chapters: 最大章节数
            filepath: 小说保存路径
            interface_format: LLM接口格式
            api_key: API密钥
            base_url: API基础URL
            llm_model: 模型名称
            number_of_chapters: 章节数量
            user_guidance: 用户指导
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            on_complete: 完成回调函数
        """
        super().__init__(master)

        self.master = master
        self.max_chapters = max_chapters
        self.filepath = filepath
        self.on_complete = on_complete
        self.is_generating = False
        self.has_generated = False  # 标记是否已经生成过
        self.generation_thread = None
        
        # 保存配置参数
        self.interface_format = interface_format
        self.api_key = api_key
        self.base_url = base_url
        self.llm_model = llm_model
        self.number_of_chapters = number_of_chapters
        self.user_guidance = user_guidance
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # 加载保存的状态
        self._load_dialog_state()

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

        # 设置窗口关闭协议
        self.protocol("WM_DELETE_WINDOW", self.protocol_handler)

    def _setup_window(self):
        """设置窗口属性"""
        self.title("生成章节目录")

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

        # 章节范围区
        self._create_chapter_range_area()

        # 生成要求区
        self._create_requirements_area()

        # 输出结果区
        self._create_output_area()

        # 按钮区
        self._create_button_area()

    def _create_chapter_range_area(self):
        """创建章节范围区"""
        chapter_frame = ctk.CTkFrame(self.main_container)
        chapter_frame.pack(fill="x", pady=(0, 10))

        # 起始章节
        ctk.CTkLabel(
            chapter_frame,
            text="起始章节:",
            font=("Microsoft YaHei", 11)
        ).grid(row=0, column=0, padx=5, pady=8, sticky="w")

        self.start_entry = ctk.CTkEntry(
            chapter_frame,
            font=("Microsoft YaHei", 11),
            width=100
        )
        self.start_entry.grid(row=0, column=1, padx=5, pady=8)

        # 结束章节
        ctk.CTkLabel(
            chapter_frame,
            text="结束章节:",
            font=("Microsoft YaHei", 11)
        ).grid(row=0, column=2, padx=5, pady=8, sticky="w")

        self.end_entry = ctk.CTkEntry(
            chapter_frame,
            font=("Microsoft YaHei", 11),
            width=100
        )
        self.end_entry.grid(row=0, column=3, padx=5, pady=8)

        # 恢复保存的值
        if hasattr(self, 'saved_start_chapter'):
            self.start_entry.insert(0, str(self.saved_start_chapter))
        else:
            self.start_entry.insert(0, "1")

        if hasattr(self, 'saved_end_chapter'):
            self.end_entry.insert(0, str(self.saved_end_chapter))
        else:
            self.end_entry.insert(0, str(self.max_chapters))

    def _create_requirements_area(self):
        """创建生成要求区"""
        requirements_frame = ctk.CTkFrame(self.main_container)
        requirements_frame.pack(fill="x", pady=(0, 10))

        # 标题行：生成要求 + 字数统计
        title_frame = ctk.CTkFrame(requirements_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=5, pady=(5, 3))

        ctk.CTkLabel(
            title_frame,
            text="生成要求:",
            font=("Microsoft YaHei", 11)
        ).pack(side="left")

        # 字数统计标签（放在最右侧）
        self.wordcount_label = ctk.CTkLabel(
            title_frame,
            text="字数：0",
            font=("Microsoft YaHei", 10)
        )
        self.wordcount_label.pack(side="right")

        # 文本框容器
        text_container = ctk.CTkFrame(requirements_frame)
        text_container.pack(fill="both", expand=True, pady=(0, 5))

        # 生成要求文本框（固定高度）
        self.requirements_text = ctk.CTkTextbox(
            text_container,
            font=("Microsoft YaHei", 11),
            height=100
        )
        self.requirements_text.pack(fill="x", pady=(0, 5))

        # 定义占位文字
        self.placeholder_text = "请输入生成要求，例如：\n1. 主角在第3章遇到关键转折点\n2. 第5章需要加入伏笔\n3. 每章字数控制在3000字左右\n4. 主角修为: 表面修为[境界/等级] | 实际实力[隐藏境界/等级]\n（此项可留空，留空时将使用默认设置）"

        # 显示占位文字
        def show_placeholder():
            if not self.requirements_text.get("0.0", "end-1c").strip():
                self.requirements_text.delete("0.0", "end")
                self.requirements_text.insert("0.0", self.placeholder_text)
                self.requirements_text.configure(text_color="gray")

        # 隐藏占位文字
        def hide_placeholder(event):
            if self.requirements_text.get("0.0", "end-1c") == self.placeholder_text:
                self.requirements_text.delete("0.0", "end")
                self.requirements_text.configure(text_color="black")

        # 检查是否需要显示占位文字
        def check_placeholder(event=None):
            text = self.requirements_text.get("0.0", "end-1c")
            if not text.strip():
                show_placeholder()
            elif text == self.placeholder_text:
                self.requirements_text.configure(text_color="gray")
            else:
                self.requirements_text.configure(text_color="black")
            update_word_count()

        def update_word_count(event=None):
            text = self.requirements_text.get("0.0", "end-1c")
            # 如果当前显示的是占位文字，不计入字数
            if text == self.placeholder_text:
                text_length = 0
            else:
                text_length = len(text)
            self.wordcount_label.configure(text=f"字数：{text_length}")

        # 绑定事件
        self.requirements_text.bind("<FocusIn>", hide_placeholder)
        self.requirements_text.bind("<FocusOut>", check_placeholder)
        self.requirements_text.bind("<KeyRelease>", check_placeholder)
        self.requirements_text.bind("<ButtonRelease>", check_placeholder)

        # 恢复保存的值
        if hasattr(self, 'saved_requirements') and self.saved_requirements.strip():
            self.requirements_text.insert("0.0", self.saved_requirements)
            self.requirements_text.configure(text_color="black")
        else:
            show_placeholder()

        update_word_count()

    def _create_output_area(self):
        """创建输出结果区"""
        output_frame = ctk.CTkFrame(self.main_container)
        output_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            output_frame,
            text="输出结果（可编辑）:",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=5, pady=(5, 3))

        # 输出结果文本框
        self.output_text = ctk.CTkTextbox(
            output_frame,
            font=("Microsoft YaHei", 11)
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # 标记是否正在初始化
        self._is_initializing = True
        
        # 绑定文本变化事件，自动更新按钮状态
        def on_output_change(event=None):
            # 如果正在初始化，不更新按钮状态
            if not self._is_initializing:
                self._update_button_state()
        self.output_text.bind("<KeyRelease>", on_output_change)
        self.output_text.bind("<ButtonRelease>", on_output_change)

        # 进度指示器
        progress_frame = ctk.CTkFrame(output_frame)
        progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=("Microsoft YaHei", 10)
        )
        self.progress_label.pack(side="left", padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=200
        )
        self.progress_bar.pack(side="left", padx=5, pady=5)
        self.progress_bar.set(0)

        # 恢复保存的输出结果（仅在有效内容时）
        if hasattr(self, 'saved_output') and self.saved_output.strip():
            self.output_text.insert("0.0", self.saved_output)
        

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0))

        # 开始生成按钮
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

        # 取消按钮
        self.btn_cancel = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self._on_cancel,
            font=("Microsoft YaHei", 11)
        )
        self.btn_cancel.pack(side="right", padx=5, pady=10)
        
        # 初始化完成，重置初始化标志

        # 根据是否有保存的输出来设置按钮文本
        if self.has_generated:
            self._update_generate_button_text(is_regenerating=True)
        else:
            self._update_generate_button_text(is_regenerating=False)
        self._is_initializing = False
        
        # 初始化按钮状态
        self._update_button_state()

    def _load_dialog_state(self):
        """加载对话框保存的状态"""
        state_file = os.path.join(self.filepath, "dialog_state.json")
        if os.path.exists(state_file):
            try:
                import json
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.saved_start_chapter = state.get('start_chapter', 1)
                    self.saved_end_chapter = state.get('end_chapter', self.max_chapters)
                    self.saved_requirements = state.get('requirements', '')
                    self.saved_output = state.get('output', '')
                    # 检查是否有有效的生成结果
                    self.has_generated = bool(self.saved_output.strip())
            except Exception as e:
                print(f"加载对话框状态失败: {e}")

    def _save_dialog_state(self):
        """保存对话框状态"""
        state_file = os.path.join(self.filepath, "dialog_state.json")
        try:
            import json
            # 获取生成要求（排除占位文字）
            requirements = self.requirements_text.get("0.0", "end").strip()
            # 如果当前内容是占位文字，则保存为空
            if requirements == self.placeholder_text.strip():
                requirements = ""

            state = {
                'start_chapter': self.start_entry.get().strip(),
                'end_chapter': self.end_entry.get().strip(),
                'requirements': requirements,
                'output': self.output_text.get("0.0", "end").strip()
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话框状态失败: {e}")

    def _on_generate(self):
        """处理开始生成按钮点击"""
        if self.is_generating:
            return

        # 验证输入
        try:
            start = int(self.start_entry.get().strip())
            end = int(self.end_entry.get().strip())

            if start < 1:
                messagebox.showwarning("输入错误", "起始章节必须大于等于1")
                return
            if end > self.max_chapters:
                messagebox.showwarning("输入错误", f"结束章节不能大于总章节数({self.max_chapters})")
                return
            if start > end:
                messagebox.showwarning("输入错误", "起始章节不能大于结束章节")
                return
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的章节号")
            return

        # 检查是否有重复生成的章节
        duplicate_chapters = self._check_duplicate_chapters(start, end)
        if duplicate_chapters:
            # 构建提示信息
            chapter_list = "、".join([f"第{ch}章" for ch in duplicate_chapters])
            message = f"本次拟生成{start}-{end}章的章节目录，其中{chapter_list}会删除并重新生成，请确认！"
            result = messagebox.askyesno("确认重新生成", message, parent=self)
            if result:
                # 用户确认重新生成，先删除这些章节
                from novel_generator.blueprint import remove_chapter_ranges
                # 将重复章节转换为连续的范围
                chapter_ranges = []
                if duplicate_chapters:
                    duplicate_chapters.sort()
                    start_range = duplicate_chapters[0]
                    end_range = start_range
                    for ch in duplicate_chapters[1:]:
                        if ch == end_range + 1:
                            end_range = ch
                        else:
                            chapter_ranges.append((start_range, end_range))
                            start_range = ch
                            end_range = ch
                    chapter_ranges.append((start_range, end_range))
                    # 删除这些章节
                    remove_chapter_ranges(self.filepath, chapter_ranges)
            else:
                return

        # 保存当前状态
        self._save_dialog_state()

        # 如果已经生成过，更新按钮文本为"重新生成"
        if self.has_generated:
            self._update_generate_button_text(is_regenerating=True)

        # 标记为生成中
        self.is_generating = True
        self._update_button_state()

        # 清空输出文本框
        self.output_text.delete("0.0", "end")

        # 添加初始提示信息
        self.output_text.insert("end", "正在连接LLM，请稍候...\n\n")
        
        # 更新按钮状态
        self._update_button_state()

        # 更新进度标签
        self.progress_label.configure(text="正在连接LLM...")
        self.progress_bar.set(0)

        # 创建生成线程
        self.generation_thread = threading.Thread(
            target=self._generate_chapters,
            args=(start, end),
            daemon=True
        )
        self.generation_thread.start()

    def _generate_chapters(self, start_chapter, end_chapter):
        """在后台线程中生成章节目录"""
        # 初始化错误标志
        generation_failed = False
        error_msg = ""
        
        try:
            # 导入必要的模块
            from novel_generator.blueprint_stream import Chapter_blueprint_generate_range_stream

            # 获取生成要求（排除占位文字）
            requirements = self.requirements_text.get("0.0", "end").strip()
            # 如果当前内容是占位文字，则视为空
            if requirements == self.placeholder_text.strip():
                requirements = ""

            # 更新进度标签为"生成中"
            self.master.after(0, lambda: self.progress_label.configure(text="生成中..."))

            # 清空输出文本框
            def clear_output():
                self.output_text.delete("0.0", "end")
                self.output_text.insert("end", "正在生成章节目录，请稍候...\n\n")
                # 更新按钮状态
                self._update_button_state()
            self.master.after(0, clear_output)

            # 定义流式输出回调函数
            def stream_callback(chunk: str):
                """流式输出回调函数"""
                if chunk:
                    # 在主线程中更新UI
                    def update_ui():
                        # 移除初始提示信息
                        if "正在生成章节目录，请稍候..." in self.output_text.get("0.0", "end"):
                            self.output_text.delete("0.0", "end")

                        # 插入新文本
                        self.output_text.insert("end", chunk)
                        # 确保滚动到最新位置
                        self.output_text.see("end")
                        # 更新按钮状态
                        self._update_button_state()
                    self.master.after(0, update_ui)

            # 生成章节目录
            Chapter_blueprint_generate_range_stream(
                interface_format=self.interface_format,
                api_key=self.api_key,
                base_url=self.base_url,
                llm_model=self.llm_model,
                filepath=self.filepath,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                number_of_chapters=self.number_of_chapters,
                user_guidance=self.user_guidance,
                generation_requirements=requirements,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                stream_callback=stream_callback
            )

            # 更新进度
            self.master.after(0, lambda: self.progress_bar.set(1))
            self.master.after(0, lambda: self.progress_label.configure(text="生成完成"))

            # 保存状态
            self.master.after(0, self._save_dialog_state)

            # 从文件中读取实际保存的内容并更新UI显示
            # 注意：blueprint_stream.py已经保存了完整内容，不需要再次调用_on_save
            def update_ui_with_saved_content():
                filename_dir = os.path.join(self.filepath, "Novel_directory.txt")
                saved_content = read_file(filename_dir)
                if saved_content and saved_content.strip():
                    # 提取新生成的章节内容
                    import re
                    # 匹配生成范围内的章节
                    pattern = r"(第\s*\d+\s*章[\s\S]*?)(?=第\s*\d+\s*章[\s\S]*?$|$)"
                    chapters = re.findall(pattern, saved_content.strip(), flags=re.DOTALL)

                    # 筛选出在生成范围内的章节
                    new_chapters = []
                    for chapter in chapters:
                        match = re.search(r"第\s*(\d+)\s*章", chapter)
                        if match:
                            chapter_num = int(match.group(1))
                            if start_chapter <= chapter_num <= end_chapter:
                                new_chapters.append(chapter)

                    # 清空当前显示
                    self.output_text.delete("0.0", "end")
                    # 只显示新生成的章节内容
                    if new_chapters:
                        self.output_text.insert("0.0", "\n\n".join(new_chapters))
            self.master.after(0, update_ui_with_saved_content)

        except Exception as e:
            generation_failed = True
            error_msg = str(e)
            
        finally:
            # 标记为非生成中
            self.is_generating = False
            # 标记已经生成过
            self.has_generated = True
            
            # 更新所有UI状态
            def update_final_state():
                self._update_button_state()
                # 更新按钮文本为"重新生成"
                self._update_generate_button_text(is_regenerating=True)
                
                if generation_failed:
                    # 清除"正在连接LLM，请稍候..."的提示信息
                    self.progress_label.configure(text="生成失败")
                    output_content = self.output_text.get("0.0", "end")
                    if "正在连接LLM，请稍候..." in output_content:
                        self.output_text.delete("0.0", "end")
                    # 显示错误消息
                    messagebox.showerror("错误", f"生成失败: {error_msg}")
                    
            self.master.after(0, update_final_state)

    def _on_save(self, show_message=True):
        """处理保存按钮点击

        参数:
            show_message: 是否显示保存成功提示框，默认为True
        """
        # 保存当前状态
        self._save_dialog_state()

        # 保存输出结果到文件
        output = self.output_text.get("0.0", "end").strip()
        if output:
            filename_dir = os.path.join(self.filepath, "Novel_directory.txt")
            clear_file_content(filename_dir)
            save_string_to_txt(output, filename_dir)
            if show_message:
                messagebox.showinfo("保存成功", "章节目录已保存")
        else:
            if show_message:
                messagebox.showwarning("警告", "没有可保存的内容")

    def _on_cancel(self):
        """处理取消按钮点击"""
        if self.is_generating:
            # 正在生成中，确认是否关闭
            if not messagebox.askyesno(
                "确认",
                "正在生成中，确定要取消吗？"
            ):
                return

        # 保存当前状态
        self._save_dialog_state()

        # 调用完成回调
        if self.on_complete:
            # 如果已经生成过，则视为成功；否则视为取消
            success = self.has_generated
            self.on_complete(success=success)

        # 关闭窗口
        self.destroy()

    def _update_button_state(self):
        """更新按钮状态"""
        # 检查输出文本框是否有内容
        has_output = bool(self.output_text.get("0.0", "end").strip())
        
        # 开始生成/重新生成按钮 - 生成中禁用，否则启用
        self.btn_generate.configure(
            state="normal" if not self.is_generating else "disabled"
        )

        # 取消按钮 - 始终启用
        self.btn_cancel.configure(state="normal")

    def _update_generate_button_text(self, is_regenerating=False):
        """更新生成按钮的文本
        
        参数:
            is_regenerating: 是否为重新生成
        """
        if is_regenerating:
            self.btn_generate.configure(text="重新生成")
        else:
            self.btn_generate.configure(text="开始生成")

    def _check_duplicate_chapters(self, start: int, end: int) -> list:
        """检查是否有重复生成的章节"""
        import re
        
        # 读取现有目录文件
        directory_file = os.path.join(self.filepath, "Novel_directory.txt")
        
        if not os.path.exists(directory_file):
            return []
        
        try:
            content = read_file(directory_file)
            if not content:
                return []
            
            # 使用正则表达式提取所有章节号
            pattern = r"第\s*(\d+)\s*章"
            matches = re.findall(pattern, content)
            existing_chapters = [int(m) for m in matches if m.isdigit()]
            
            # 找出在生成范围内已存在的章节
            duplicate_chapters = [ch for ch in existing_chapters if start <= ch <= end]
            
            return duplicate_chapters
        except Exception as e:
            print(f"检查重复章节时出错: {e}")
            return []

    def protocol_handler(self):
        """处理窗口关闭事件"""
        if self.is_generating:
            # 正在生成中，确认是否关闭
            if not messagebox.askyesno(
                "确认",
                "正在生成中，确定要关闭吗？"
            ):
                return

        # 保存当前状态
        self._save_dialog_state()

        # 调用完成回调
        if self.on_complete:
            self.on_complete(success=False)

        # 关闭窗口
        self.destroy()

    def destroy(self):
        """销毁窗口"""
        if hasattr(self, 'generation_thread') and self.generation_thread and self.generation_thread.is_alive():
            # 等待生成线程结束
            self.generation_thread.join(timeout=1.0)
        super().destroy()
