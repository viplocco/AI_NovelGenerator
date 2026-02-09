# ui/generation_handlers.py
# -*- coding: utf-8 -*-
import os
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import traceback
from utils import read_file, save_string_to_txt, clear_file_content
from ui.directory_tab import load_chapter_blueprint
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    Chapter_blueprint_generate_range,
    check_existing_chapters,
    remove_chapter_ranges,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    enrich_chapter_text
)
from consistency_checker import check_consistency

def show_directory_generation_dialog(master, max_chapters):
    """
    显示目录生成参数对话框
    
    参数:
        master: 父窗口
        max_chapters: 最大章节数
    
    返回:
        dict: 包含 start_chapter, end_chapter, requirements 的字典
              如果用户取消则返回 None
    """
    result = {"start_chapter": None, "end_chapter": None, "requirements": None}
    event = threading.Event()
    
    def create_dialog():
        dialog = ctk.CTkToplevel(master)
        dialog.title("生成章节目录")
        dialog.geometry("550x480")
        dialog.transient(master)
        dialog.grab_set()
        # 居中显示弹窗
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # 主框架（无填充色）
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 章节范围框架（无填充色）
        chapter_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chapter_frame.pack(fill="x", pady=(0, 10))
        
        # 起始章节
        ctk.CTkLabel(chapter_frame, text="起始章节:", font=("Microsoft YaHei", 11), fg_color="transparent").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        start_entry = ctk.CTkEntry(chapter_frame, font=("Microsoft YaHei", 11), width=100)
        start_entry.insert(0, "1")
        start_entry.grid(row=0, column=1, padx=5, pady=8)
        
        # 结束章节
        ctk.CTkLabel(chapter_frame, text="结束章节:", font=("Microsoft YaHei", 11), fg_color="transparent").grid(row=0, column=2, padx=5, pady=8, sticky="w")
        end_entry = ctk.CTkEntry(chapter_frame, font=("Microsoft YaHei", 11), width=100)
        end_entry.insert(0, str(max_chapters))
        end_entry.grid(row=0, column=3, padx=5, pady=8)
        
        # 生成要求标签
        ctk.CTkLabel(main_frame, text="生成要求:", font=("Microsoft YaHei", 11), fg_color="transparent").pack(anchor="w", pady=(5, 3))
        
        # 文本框容器（无填充色）
        text_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        text_container.pack(fill="both", expand=True, pady=(0, 5))
        
        # 生成要求文本框
        requirements_text = ctk.CTkTextbox(text_container, font=("Microsoft YaHei", 11))
        requirements_text.pack(fill="both", expand=True)
        
        # 字数统计标签（另起一行）
        wordcount_label = ctk.CTkLabel(main_frame, text="字数：0", font=("Microsoft YaHei", 10), fg_color="transparent")
        wordcount_label.pack(anchor="e", pady=(0, 10))
        
        def update_word_count(event=None):
            text = requirements_text.get("0.0", "end-1c")
            text_length = len(text)
            wordcount_label.configure(text=f"字数：{text_length}")
        
        requirements_text.bind("<KeyRelease>", update_word_count)
        requirements_text.bind("<ButtonRelease>", update_word_count)
        update_word_count()
        
        # 按钮框架
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        def on_confirm():
            try:
                start = int(start_entry.get().strip())
                end = int(end_entry.get().strip())
                
                if start < 1:
                    messagebox.showwarning("输入错误", "起始章节必须大于等于1")
                    return
                if end > max_chapters:
                    messagebox.showwarning("输入错误", f"结束章节不能大于总章节数({max_chapters})")
                    return
                if start > end:
                    messagebox.showwarning("输入错误", "起始章节不能大于结束章节")
                    return
                
                result["start_chapter"] = start
                result["end_chapter"] = end
                result["requirements"] = requirements_text.get("0.0", "end").strip()
                dialog.destroy()
                event.set()
            except ValueError:
                messagebox.showwarning("输入错误", "请输入有效的章节号")
        
        def on_cancel():
            result["start_chapter"] = None
            result["end_chapter"] = None
            result["requirements"] = None
            dialog.destroy()
            event.set()
        
        btn_confirm = ctk.CTkButton(button_frame, text="确认", font=("Microsoft YaHei", 11), height=32, command=on_confirm)
        btn_confirm.pack(side="left", padx=(0, 8), expand=True, fill="x")
        
        btn_cancel = ctk.CTkButton(button_frame, text="取消", font=("Microsoft YaHei", 11), height=32, command=on_cancel)
        btn_cancel.pack(side="left", expand=True, fill="x")
        
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    
    master.after(0, create_dialog)
    event.wait()
    
    if result["start_chapter"] is None:
        return None
    return result

def generate_novel_architecture_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    # 禁用按钮
    self.disable_button_safe(self.btn_generate_architecture)

    try:
        interface_format = self.interface_format_var.get().strip()
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model_name = self.model_name_var.get().strip()
        temperature = self.temperature_var.get()
        max_tokens = self.max_tokens_var.get()
        timeout_val = self.safe_get_int(self.timeout_var, 600)

        topic = self.topic_text.get("0.0", "end").strip()
        genre = self.genre_var.get().strip()
        num_chapters = self.safe_get_int(self.num_chapters_var, 10)
        word_number = self.safe_get_int(self.word_number_var, 3000)
        # 获取全局用户指导
        global_guidance = self.user_guide_text.get("0.0", "end").strip()

        # 创建向导弹窗
        from ui.architecture_wizard_ui import ArchitectureWizardUI

        def on_complete(success=False):
            """向导关闭后的回调

            参数:
                success: 是否成功完成（True=完成，False=取消）
            """
            if success:
                # 成功完成，显示日志并加载文件
                self.safe_log("✅ 小说架构生成完成。请在 '小说架构' 标签页查看或编辑。")
                self.load_novel_architecture()
                # 更新按钮状态
                self.update_step_buttons_state()
                self.update_optional_buttons_state()
            else:
                # 用户取消，只显示提示
                self.safe_log("⏸️ 架构生成已取消。已生成的内容已保存到partial_architecture.json")

            # 启用按钮
            self.enable_button_safe(self.btn_generate_architecture)

        # 显示向导弹窗
        wizard = ArchitectureWizardUI(
            master=self.master,
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            llm_model=model_name,
            topic=topic,
            genre=genre,
            number_of_chapters=num_chapters,
            word_number=word_number,
            filepath=filepath,
            global_guidance=global_guidance,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout_val,
            on_complete=on_complete
        )

        # 设置窗口关闭协议
        wizard.protocol("WM_DELETE_WINDOW", wizard.protocol_handler)

    except Exception:
        self.handle_exception("打开架构生成向导时出错")
        self.enable_button_safe(self.btn_generate_architecture)

def generate_chapter_blueprint_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    # 禁用按钮
    self.disable_button_safe(self.btn_generate_directory)

    try:
        number_of_chapters = self.safe_get_int(self.num_chapters_var, 10)
        
        # 显示对话框获取用户输入
        # 创建完成回调函数
        def on_complete(success=False):
            """对话框关闭后的回调

            参数:
                success: 是否成功完成（True=完成，False=取消）
            """
            if success:
                # 成功完成，显示日志并加载文件
                self.safe_log("✅ 章节目录生成完成。请在 '章节大纲' 标签页查看或编辑。")
                load_chapter_blueprint(self)
                # 更新按钮状态
                self.update_step_buttons_state()
                self.update_optional_buttons_state()
            else:
                # 用户取消，只显示提示
                self.safe_log("⏸️ 章节目录生成已取消。")

            # 启用按钮
            self.enable_button_safe(self.btn_generate_directory)

        # 显示章节目录对话框
        from ui.chapter_directory_dialog import ChapterDirectoryDialog
        
        # 获取配置参数
        interface_format = self.interface_format_var.get().strip()
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        llm_model = self.model_name_var.get().strip()
        temperature = self.temperature_var.get()
        max_tokens = self.max_tokens_var.get()
        timeout_val = self.safe_get_int(self.timeout_var, 600)
        user_guidance = self.user_guide_text.get("0.0", "end").strip()
        
        dialog = ChapterDirectoryDialog(
            master=self.master,
            max_chapters=number_of_chapters,
            filepath=filepath,
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            llm_model=llm_model,
            number_of_chapters=number_of_chapters,
            user_guidance=user_guidance,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout_val,
            on_complete=on_complete
        )

    except Exception:
        self.handle_exception("打开章节目录生成对话框时出错")
        self.enable_button_safe(self.btn_generate_directory)
        
def generate_chapter_draft_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_generate_chapter)
        try:
            interface_format = self.interface_format_var.get().strip()
            api_key = self.api_key_var.get().strip()
            base_url = self.base_url_var.get().strip()
            model_name = self.model_name_var.get().strip()
            temperature = self.temperature_var.get()
            max_tokens = self.max_tokens_var.get()
            timeout_val = self.safe_get_int(self.timeout_var, 600)

            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            word_number = self.safe_get_int(self.word_number_var, 3000)
            user_guidance = self.user_guide_text.get("0.0", "end").strip()

            char_inv = self.characters_involved_var.get().strip()
            key_items = self.key_items_var.get().strip()
            scene_loc = self.scene_location_var.get().strip()
            time_constr = self.time_constraint_var.get().strip()

            embedding_api_key = self.embedding_api_key_var.get().strip()
            embedding_url = self.embedding_url_var.get().strip()
            embedding_interface_format = self.embedding_interface_format_var.get().strip()
            embedding_model_name = self.embedding_model_name_var.get().strip()
            embedding_k = self.safe_get_int(self.embedding_retrieval_k_var, 4)

            self.safe_log(f"生成第{chap_num}章草稿：准备生成请求提示词...")

            # 调用新添加的 build_chapter_prompt 函数构造初始提示词
            from novel_generator.chapter import build_chapter_prompt
            prompt_text = build_chapter_prompt(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                filepath=filepath,
                novel_number=chap_num,
                word_number=word_number,
                temperature=temperature,
                user_guidance=user_guidance,
                characters_involved=char_inv,
                key_items=key_items,
                scene_location=scene_loc,
                time_constraint=time_constr,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                embedding_retrieval_k=embedding_k,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val
            )

            # 弹出可编辑提示词对话框，等待用户确认或取消
            result = {"prompt": None}
            event = threading.Event()

            def create_dialog():
                dialog = ctk.CTkToplevel(self.master)
                dialog.title("当前章节请求提示词（可编辑）")
                dialog.geometry("600x400")
                text_box = ctk.CTkTextbox(dialog, wrap="word", font=("Microsoft YaHei", 12))
                text_box.pack(fill="both", expand=True, padx=10, pady=10)

                # 字数统计标签
                wordcount_label = ctk.CTkLabel(dialog, text="字数：0", font=("Microsoft YaHei", 12))
                wordcount_label.pack(side="left", padx=(10,0), pady=5)
                
                # 插入角色内容
                final_prompt = prompt_text
                role_names = [name.strip() for name in self.char_inv_text.get("0.0", "end").strip().split(',') if name.strip()]
                role_lib_path = os.path.join(filepath, "角色库")
                role_contents = []
                
                if os.path.exists(role_lib_path):
                    for root, dirs, files in os.walk(role_lib_path):
                        for file in files:
                            if file.endswith(".txt") and os.path.splitext(file)[0] in role_names:
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        role_contents.append(f.read().strip())  # 直接使用文件内容，不添加重复名字
                                except Exception as e:
                                    self.safe_log(f"读取角色文件 {file} 失败: {str(e)}")
                
                if role_contents:
                    role_content_str = "\n".join(role_contents)
                    # 更精确的替换逻辑，处理不同情况下的占位符
                    placeholder_variations = [
                        "核心人物(可能未指定)：{characters_involved}",
                        "核心人物：{characters_involved}",
                        "核心人物(可能未指定):{characters_involved}",
                        "核心人物:{characters_involved}"
                    ]
                    
                    for placeholder in placeholder_variations:
                        if placeholder in final_prompt:
                            final_prompt = final_prompt.replace(
                                placeholder,
                                f"核心人物：\n{role_content_str}"
                            )
                            break
                    else:  # 如果没有找到任何已知占位符变体
                        lines = final_prompt.split('\n')
                        for i, line in enumerate(lines):
                            if "核心人物" in line and "：" in line:
                                lines[i] = f"核心人物：\n{role_content_str}"
                                break
                        final_prompt = '\n'.join(lines)

                text_box.insert("0.0", final_prompt)
                # 更新字数函数
                def update_word_count(event=None):
                    text = text_box.get("0.0", "end-1c")
                    text_length = len(text)
                    wordcount_label.configure(text=f"字数：{text_length}")

                text_box.bind("<KeyRelease>", update_word_count)
                text_box.bind("<ButtonRelease>", update_word_count)
                update_word_count()  # 初始化统计

                button_frame = ctk.CTkFrame(dialog)
                button_frame.pack(pady=10)
                def on_confirm():
                    result["prompt"] = text_box.get("1.0", "end").strip()
                    dialog.destroy()
                    event.set()
                def on_cancel():
                    result["prompt"] = None
                    dialog.destroy()
                    event.set()
                btn_confirm = ctk.CTkButton(button_frame, text="确认使用", font=("Microsoft YaHei", 12), command=on_confirm)
                btn_confirm.pack(side="left", padx=10)
                btn_cancel = ctk.CTkButton(button_frame, text="取消请求", font=("Microsoft YaHei", 12), command=on_cancel)
                btn_cancel.pack(side="left", padx=10)
                # 若用户直接关闭弹窗，则调用 on_cancel 处理
                dialog.protocol("WM_DELETE_WINDOW", on_cancel)
                dialog.grab_set()
            self.master.after(0, create_dialog)
            event.wait()  # 等待用户操作完成
            edited_prompt = result["prompt"]
            if edited_prompt is None:
                self.safe_log("❌ 用户取消了草稿生成请求。")
                return

            self.safe_log("开始生成章节草稿...")
            
            # 清空章节文本框
            self.master.after(0, lambda: self.chapter_result.delete("0.0", "end"))
            
            # 流式输出回调函数
            def stream_callback(chunk: str):
                """流式输出回调函数，实时更新UI显示"""
                if chunk:
                    # 在主线程中更新UI
                    # 使用闭包捕获chunk的值
                    def update_ui():
                        self.chapter_result.insert("end", chunk)
                        self.chapter_result.see("end")
                        self.update_word_count()
                    self.master.after(0, update_ui)
                else:
                    # 添加调试日志
                    print("收到空chunk或None")
            
            from novel_generator.chapter import generate_chapter_draft_stream
            draft_text = generate_chapter_draft_stream(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                filepath=filepath,
                novel_number=chap_num,
                word_number=word_number,
                temperature=temperature,
                user_guidance=user_guidance,
                characters_involved=char_inv,
                key_items=key_items,
                scene_location=scene_loc,
                time_constraint=time_constr,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                embedding_retrieval_k=embedding_k,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val,
                custom_prompt_text=edited_prompt,  # 使用用户编辑后的提示词
                stream_callback=stream_callback  # 流式输出回调函数
            )
            
            # 恢复编辑功能
            self.master.after(0, lambda: self.set_chapter_editable(True))
            
            if draft_text:
                self.safe_log(f"✅ 第{chap_num}章草稿生成完成。请在左侧查看或编辑。")
                # 更新按钮状态
                self.update_step_buttons_state()
            else:
                self.safe_log("⚠️ 本章草稿生成失败或无内容。")
        except Exception:
            self.handle_exception("生成章节草稿时出错")
        finally:
            self.enable_button_safe(self.btn_generate_chapter)
    threading.Thread(target=task, daemon=True).start()

def finalize_chapter_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        if not messagebox.askyesno("确认", "确定要定稿当前章节吗？"):
            self.enable_button_safe(self.btn_finalize_chapter)
            return

        self.disable_button_safe(self.btn_finalize_chapter)
        try:
            interface_format = self.interface_format_var.get().strip()
            api_key = self.api_key_var.get().strip()
            base_url = self.base_url_var.get().strip()
            model_name = self.model_name_var.get().strip()
            temperature = self.temperature_var.get()
            max_tokens = self.max_tokens_var.get()
            timeout_val = self.safe_get_int(self.timeout_var, 600)

            embedding_api_key = self.embedding_api_key_var.get().strip()
            embedding_url = self.embedding_url_var.get().strip()
            embedding_interface_format = self.embedding_interface_format_var.get().strip()
            embedding_model_name = self.embedding_model_name_var.get().strip()

            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            word_number = self.safe_get_int(self.word_number_var, 3000)

            self.safe_log(f"开始定稿第{chap_num}章...")

            chapters_dir = os.path.join(filepath, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")

            edited_text = self.chapter_result.get("0.0", "end").strip()

            if len(edited_text) < 0.7 * word_number:
                ask = messagebox.askyesno("字数不足", f"当前章节字数 ({len(edited_text)}) 低于目标字数({word_number})的70%，是否要尝试扩写？")
                if ask:
                    self.safe_log("正在扩写章节内容...")
                    enriched = enrich_chapter_text(
                        chapter_text=edited_text,
                        word_number=word_number,
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                        temperature=temperature,
                        interface_format=interface_format,
                        max_tokens=max_tokens,
                        timeout=timeout_val
                    )
                    edited_text = enriched
                    self.master.after(0, lambda: self.chapter_result.delete("0.0", "end"))
                    self.master.after(0, lambda: self.chapter_result.insert("0.0", edited_text))
            clear_file_content(chapter_file)
            save_string_to_txt(edited_text, chapter_file)

            finalize_chapter(
                novel_number=chap_num,
                word_number=word_number,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                filepath=filepath,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val
            )
            self.safe_log(f"✅ 第{chap_num}章定稿完成（已更新前文摘要、角色状态、向量库）。")
            
            # 在主线程中更新UI
            def update_ui():
                # 更新按钮状态
                self.update_step_buttons_state()
                # 显示最终文本
                final_text = read_file(chapter_file)
                self.show_chapter_in_textbox(final_text)
                # 最后启用定稿按钮
                self.enable_button_safe(self.btn_finalize_chapter)
            
            self.master.after(0, update_ui)
        except Exception:
            self.handle_exception("定稿章节时出错")
            # 出错时也要启用按钮
            self.master.after(0, lambda: self.enable_button_safe(self.btn_finalize_chapter))
    threading.Thread(target=task, daemon=True).start()

def do_consistency_check(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_check_consistency)
        try:
            api_key = self.api_key_var.get().strip()
            base_url = self.base_url_var.get().strip()
            model_name = self.model_name_var.get().strip()
            temperature = self.temperature_var.get()
            interface_format = self.interface_format_var.get()
            max_tokens = self.max_tokens_var.get()
            timeout = self.timeout_var.get()

            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            chap_file = os.path.join(filepath, "chapters", f"chapter_{chap_num}.txt")
            chapter_text = read_file(chap_file)

            if not chapter_text.strip():
                self.safe_log("⚠️ 当前章节文件为空或不存在，无法审校。")
                return

            self.safe_log("开始一致性审校...")
            # 读取剧情要点
            plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
            plot_arcs = ""
            if os.path.exists(plot_arcs_file):
                plot_arcs = read_file(plot_arcs_file)
            
            result = check_consistency(
                novel_setting="",
                character_state=read_file(os.path.join(filepath, "character_state.txt")),
                global_summary=read_file(os.path.join(filepath, "global_summary.txt")),
                chapter_text=chapter_text,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout,
                plot_arcs=plot_arcs
            )
            self.safe_log("审校结果：")
            self.safe_log(result)
        except Exception:
            self.handle_exception("审校时出错")
        finally:
            self.enable_button_safe(self.btn_check_consistency)
    threading.Thread(target=task, daemon=True).start()

def import_knowledge_handler(self):
    selected_file = tk.filedialog.askopenfilename(
        title="选择要导入的知识库文件",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if selected_file:
        def task():
            self.disable_button_safe(self.btn_import_knowledge)
            try:
                emb_api_key = self.embedding_api_key_var.get().strip()
                emb_url = self.embedding_url_var.get().strip()
                emb_format = self.embedding_interface_format_var.get().strip()
                emb_model = self.embedding_model_name_var.get().strip()

                # 尝试不同编码读取文件
                content = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'ansi']
                for encoding in encodings:
                    try:
                        with open(selected_file, 'r', encoding=encoding) as f:
                            content = f.read()
                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        self.safe_log(f"读取文件时发生错误: {str(e)}")
                        raise

                if content is None:
                    raise Exception("无法以任何已知编码格式读取文件")

                # 创建临时UTF-8文件
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as temp:
                    temp.write(content)
                    temp_path = temp.name

                try:
                    self.safe_log(f"开始导入知识库文件: {selected_file}")
                    import_knowledge_file(
                        embedding_api_key=emb_api_key,
                        embedding_url=emb_url,
                        embedding_interface_format=emb_format,
                        embedding_model_name=emb_model,
                        file_path=temp_path,
                        filepath=self.filepath_var.get().strip()
                    )
                    self.safe_log("✅ 知识库文件导入完成。")
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except Exception:
                self.handle_exception("导入知识库时出错")
            finally:
                self.enable_button_safe(self.btn_import_knowledge)

        try:
            thread = threading.Thread(target=task, daemon=True)
            thread.start()
        except Exception as e:
            self.enable_button_safe(self.btn_import_knowledge)
            messagebox.showerror("错误", f"线程启动失败: {str(e)}")

def clear_vectorstore_handler(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    first_confirm = messagebox.askyesno("警告", "确定要清空本地向量库吗？此操作不可恢复！")
    if first_confirm:
        second_confirm = messagebox.askyesno("二次确认", "你确定真的要删除所有向量数据吗？此操作不可恢复！")
        if second_confirm:
            if clear_vector_store(filepath):
                self.log("已清空向量库。")
            else:
                self.log(f"未能清空向量库，请关闭程序后手动删除 {filepath} 下的 vectorstore 文件夹。")

def show_plot_arcs_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先在主Tab中设置保存文件路径")
        return

    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    if not os.path.exists(plot_arcs_file):
        messagebox.showinfo("剧情要点", "当前还未生成任何剧情要点或冲突记录。")
        return

    arcs_text = read_file(plot_arcs_file).strip()
    if not arcs_text:
        arcs_text = "当前没有记录的剧情要点或冲突。"

    top = ctk.CTkToplevel(self.master)
    top.title("剧情要点/未解决冲突")
    top.geometry("600x400")
    text_area = ctk.CTkTextbox(top, wrap="word", font=("Microsoft YaHei", 12))
    text_area.pack(fill="both", expand=True, padx=10, pady=10)
    text_area.insert("0.0", arcs_text)
    text_area.configure(state="disabled")
