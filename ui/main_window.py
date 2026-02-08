# ui/main_window.py
# -*- coding: utf-8 -*-
import os
import threading
import logging
import traceback
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from .role_library import RoleLibrary
from llm_adapters import create_llm_adapter

from config_manager import load_config, save_config, test_llm_config, test_embedding_config
from utils import read_file, save_string_to_txt, clear_file_content
from tooltips import tooltips

from ui.context_menu import TextWidgetContextMenu
from ui.main_tab import build_main_tab, build_left_layout, build_right_layout
from ui.config_tab import build_model_config_area, load_config_btn, save_config_btn
from ui.novel_params_tab import build_novel_params_area, build_optional_buttons_area
from ui.generation_handlers import (
    generate_novel_architecture_ui,
    generate_chapter_blueprint_ui,
    generate_chapter_draft_ui,
    finalize_chapter_ui,
    do_consistency_check,
    import_knowledge_handler,
    clear_vectorstore_handler,
    show_plot_arcs_ui
)
from ui.setting_tab import build_setting_tab, load_novel_architecture, save_novel_architecture
from ui.directory_tab import build_directory_tab, load_chapter_blueprint, save_chapter_blueprint
from ui.character_tab import build_character_tab, load_character_state, save_character_state
from ui.summary_tab import build_summary_tab, load_global_summary, save_global_summary
from ui.chapters_tab import build_chapters_tab, refresh_chapters_list, on_chapter_selected, load_chapter_content, save_current_chapter, prev_chapter, next_chapter

class NovelGeneratorGUI:
    """
    小说生成器的主GUI类，包含所有的界面布局、事件处理、与后端逻辑的交互等。
    """
    def __init__(self, master):
        self.master = master
        self.master.title("小说生成器")
        try:
            if os.path.exists("icon.ico"):
                self.master.iconbitmap("icon.ico")
        except Exception:
            pass
        self.master.geometry("1350x840")
        # 设置窗口的最小尺寸
        self.master.minsize(800, 600)

        # --------------- 配置文件路径 ---------------
        self.config_file = "config.json"
        self.loaded_config = load_config(self.config_file)

        if self.loaded_config:
            last_llm = self.loaded_config.get("last_interface_format", "OpenAI")
            last_embedding = self.loaded_config.get("last_embedding_interface_format", "OpenAI")
        else:
            last_llm = "OpenAI"
            last_embedding = "OpenAI"

        if self.loaded_config and "llm_configs" in self.loaded_config and last_llm in self.loaded_config["llm_configs"]:
            llm_conf = self.loaded_config["llm_configs"][last_llm]
        else:
            llm_conf = {
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "model_name": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 8192,
                "timeout": 600
            }

        if self.loaded_config and "embedding_configs" in self.loaded_config and last_embedding in self.loaded_config["embedding_configs"]:
            emb_conf = self.loaded_config["embedding_configs"][last_embedding]
        else:
            emb_conf = {
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "model_name": "text-embedding-ada-002",
                "retrieval_k": 4
            }

        # -- LLM通用参数 --
        self.api_key_var = ctk.StringVar(value=llm_conf.get("api_key", ""))
        self.base_url_var = ctk.StringVar(value=llm_conf.get("base_url", "https://api.openai.com/v1"))
        self.interface_format_var = ctk.StringVar(value=last_llm)
        self.model_name_var = ctk.StringVar(value=llm_conf.get("model_name", "gpt-4o-mini"))
        self.temperature_var = ctk.DoubleVar(value=llm_conf.get("temperature", 0.7))
        self.max_tokens_var = ctk.IntVar(value=llm_conf.get("max_tokens", 8192))
        self.timeout_var = ctk.IntVar(value=llm_conf.get("timeout", 600))

        # -- Embedding相关 --
        self.embedding_interface_format_var = ctk.StringVar(value=last_embedding)
        self.embedding_api_key_var = ctk.StringVar(value=emb_conf.get("api_key", ""))
        self.embedding_url_var = ctk.StringVar(value=emb_conf.get("base_url", "https://api.openai.com/v1"))
        self.embedding_model_name_var = ctk.StringVar(value=emb_conf.get("model_name", "text-embedding-ada-002"))
        self.embedding_retrieval_k_var = ctk.StringVar(value=str(emb_conf.get("retrieval_k", 4)))

        # -- 小说参数相关 --
        # 初始化变量为空，不从config.json加载默认值，避免覆盖novel_info.json中的值
        self.title_var = ctk.StringVar(value="")
        self.topic_var = ctk.StringVar(value="")
        self.topic_default = ""
        self.genre_var = ctk.StringVar(value="")
        self.num_chapters_var = ctk.StringVar(value="")
        self.word_number_var = ctk.StringVar(value="")
        self.filepath_var = ctk.StringVar(value="")
        self.display_path_var = ctk.StringVar(value="")
        self.chapter_num_var = ctk.StringVar(value="")
        self.characters_involved_var = ctk.StringVar(value="")
        self.key_items_var = ctk.StringVar(value="")
        self.scene_location_var = ctk.StringVar(value="")
        self.time_constraint_var = ctk.StringVar(value="")
        self.user_guidance_default = ""

        # 为StringVar添加trace监听器，以便在值变化时自动保存
        def on_var_change(*args):
            if hasattr(self, '_save_novel_params') and self.current_novel_id:
                self._save_novel_params()

        self.title_var.trace_add("write", on_var_change)
        self.genre_var.trace_add("write", on_var_change)
        self.num_chapters_var.trace_add("write", on_var_change)
        self.word_number_var.trace_add("write", on_var_change)
        self.chapter_num_var.trace_add("write", on_var_change)
        self.characters_involved_var.trace_add("write", on_var_change)
        self.key_items_var.trace_add("write", on_var_change)
        self.scene_location_var.trace_add("write", on_var_change)
        self.time_constraint_var.trace_add("write", on_var_change)

        # --------------- 整体Tab布局 ---------------
        # 创建顶部容器，用于放置tabview
        self.top_container = ctk.CTkFrame(self.master, fg_color="transparent")
        self.top_container.pack(fill="both", expand=True)

        # 创建tabview
        self.tabview = ctk.CTkTabview(self.top_container)
        self.tabview.pack(side="left", fill="both", expand=True)

        # 创建各个标签页
        build_main_tab(self)
        build_setting_tab(self)
        build_directory_tab(self)
        build_character_tab(self)
        build_summary_tab(self)
        build_chapters_tab(self)
        # 添加"小说管理"tab
        self.novel_manager_tab = self.tabview.add("小说管理")
        # 绑定tab切换事件
        self.tabview.configure(command=self._on_tab_changed)
        # 初始隐藏tab切换模块
        self.tabview._segmented_button.grid_remove()
        # 跟踪上一个选中的tab
        self._previous_tab = "小说管理"
        # 设置默认显示"小说管理"tab
        self.tabview.set("小说管理")
        
        # 初始化小说管理器
        self.novel_manager = None
        self.current_novel_id = None
        

        
        # 初始化小说管理UI
        from .novel_manager import NovelManagerUI
        # 创建NovelManager实例
        from .novel_manager import NovelManager
        self.novel_manager = NovelManager()
        # 将NovelManager实例传递给NovelManagerUI
        self.novel_manager_ui = NovelManagerUI(
            self.novel_manager_tab,
            on_novel_opened=self._on_novel_opened,
            manager=self.novel_manager
        )
        self.novel_manager_ui.pack(fill="both", expand=True)
        


    # ----------------- 通用辅助函数 -----------------
    def show_tooltip(self, key: str):
        info_text = tooltips.get(key, "暂无说明")
        messagebox.showinfo("参数说明", info_text)

    def safe_get_int(self, var, default=1):
        try:
            val_str = str(var.get()).strip()
            return int(val_str)
        except:
            var.set(str(default))
            return default

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def safe_log(self, message: str):
        self.master.after(0, lambda: self.log(message))

    def disable_button_safe(self, btn):
        self.master.after(0, lambda: btn.configure(state="disabled"))

    def enable_button_safe(self, btn):
        self.master.after(0, lambda: btn.configure(state="normal"))

    def handle_exception(self, context: str):
        full_message = f"{context}\n{traceback.format_exc()}"
        logging.error(full_message)
        self.safe_log(full_message)

    def show_chapter_in_textbox(self, text: str):
        self.chapter_result.delete("0.0", "end")
        self.chapter_result.insert("0.0", text)
        self.chapter_result.see("end")
    
    def test_llm_config(self):
        """
        测试当前的LLM配置是否可用
        """
        interface_format = self.interface_format_var.get().strip()
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model_name = self.model_name_var.get().strip()
        temperature = self.temperature_var.get()
        max_tokens = self.max_tokens_var.get()
        timeout = self.timeout_var.get()

        test_llm_config(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            log_func=self.safe_log,
            handle_exception_func=self.handle_exception
        )

    def test_embedding_config(self):
        """
        测试当前的Embedding配置是否可用
        """
        api_key = self.embedding_api_key_var.get().strip()
        base_url = self.embedding_url_var.get().strip()
        interface_format = self.embedding_interface_format_var.get().strip()
        model_name = self.embedding_model_name_var.get().strip()

        test_embedding_config(
            api_key=api_key,
            base_url=base_url,
            interface_format=interface_format,
            model_name=model_name,
            log_func=self.safe_log,
            handle_exception_func=self.handle_exception
        )
    
    def browse_folder(self):
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            self.filepath_var.set(selected_dir)
            self.display_path_var.set(selected_dir)

    def show_character_import_window(self):
        """显示角色导入窗口"""
        import_window = ctk.CTkToplevel(self.master)
        import_window.title("导入角色信息")
        import_window.geometry("600x500")
        import_window.transient(self.master)  # 设置为父窗口的临时窗口
        import_window.grab_set()  # 保持窗口在顶层
        
        # 主容器
        main_frame = ctk.CTkFrame(import_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 滚动容器
        scroll_frame = ctk.CTkScrollableFrame(main_frame)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 获取角色库路径
        role_lib_path = os.path.join(self.filepath_var.get().strip(), "角色库")
        self.selected_roles = []  # 存储选中的角色名称
        
        # 动态加载角色分类
        if os.path.exists(role_lib_path):
            # 配置网格布局参数
            scroll_frame.columnconfigure(0, weight=1)
            max_roles_per_row = 4
            current_row = 0
            
            for category in os.listdir(role_lib_path):
                category_path = os.path.join(role_lib_path, category)
                if os.path.isdir(category_path):
                    # 创建分类容器
                    category_frame = ctk.CTkFrame(scroll_frame)
                    category_frame.grid(row=current_row, column=0, sticky="w", pady=(10,5), padx=5)
                    
                    # 添加分类标签
                    category_label = ctk.CTkLabel(category_frame, text=f"【{category}】", 
                                                font=("Microsoft YaHei", 12, "bold"))
                    category_label.grid(row=0, column=0, padx=(0,10), sticky="w")
                    
                    # 初始化角色排列参数
                    role_count = 0
                    row_num = 0
                    col_num = 1  # 从第1列开始（第0列是分类标签）
                    
                    # 添加角色复选框
                    for role_file in os.listdir(category_path):
                        if role_file.endswith(".txt"):
                            role_name = os.path.splitext(role_file)[0]
                            if not any(name == role_name for _, name in self.selected_roles):
                                chk = ctk.CTkCheckBox(category_frame, text=role_name)
                                chk.grid(row=row_num, column=col_num, padx=5, pady=2, sticky="w")
                                self.selected_roles.append((chk, role_name))
                                
                                # 更新行列位置
                                role_count += 1
                                col_num += 1
                                if col_num > max_roles_per_row:
                                    col_num = 1
                                    row_num += 1
                    
                    # 如果没有角色，调整分类标签占满整行
                    if role_count == 0:
                        category_label.grid(columnspan=max_roles_per_row+1, sticky="w")
                    
                    # 更新主布局的行号
                    current_row += 1
                    
                    # 添加分隔线
                    separator = ctk.CTkFrame(scroll_frame, height=1, fg_color="gray")
                    separator.grid(row=current_row, column=0, sticky="ew", pady=5)
                    current_row += 1
        
        # 底部按钮框架
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        # 选择按钮
        def confirm_selection():
            selected = [name for chk, name in self.selected_roles if chk.get() == 1]
            self.char_inv_text.delete("0.0", "end")
            self.char_inv_text.insert("0.0", ", ".join(selected))
            import_window.destroy()
            
        btn_confirm = ctk.CTkButton(btn_frame, text="选择", command=confirm_selection)
        btn_confirm.pack(side="left", padx=20)
        
        # 取消按钮
        btn_cancel = ctk.CTkButton(btn_frame, text="取消", command=import_window.destroy)
        btn_cancel.pack(side="right", padx=20)

    def show_role_library(self):
        save_path = self.filepath_var.get().strip()
        if not save_path:
            messagebox.showwarning("警告", "请先设置保存路径\n\n请先在主界面右侧的\"保存路径\"栏中设置小说的保存路径，然后再打开角色库。")
            return
        
        # 初始化LLM适配器
        llm_adapter = create_llm_adapter(
            interface_format=self.interface_format_var.get(),
            base_url=self.base_url_var.get(),
            model_name=self.model_name_var.get(),
            api_key=self.api_key_var.get(),
            temperature=self.temperature_var.get(),
            max_tokens=self.max_tokens_var.get(),
            timeout=self.timeout_var.get()
        )
        
        # 传递LLM适配器实例到角色库
        if hasattr(self, '_role_lib'):
            if self._role_lib.window and self._role_lib.window.winfo_exists():
                self._role_lib.window.destroy()
        
        self._role_lib = RoleLibrary(self.master, save_path, llm_adapter)  # 新增参数

    # ----------------- 将导入的各模块函数直接赋给类方法 -----------------
    generate_novel_architecture_ui = generate_novel_architecture_ui
    generate_chapter_blueprint_ui = generate_chapter_blueprint_ui
    generate_chapter_draft_ui = generate_chapter_draft_ui
    finalize_chapter_ui = finalize_chapter_ui
    do_consistency_check = do_consistency_check
    import_knowledge_handler = import_knowledge_handler
    clear_vectorstore_handler = clear_vectorstore_handler
    show_plot_arcs_ui = show_plot_arcs_ui
    load_config_btn = load_config_btn
    save_config_btn = save_config_btn
    load_novel_architecture = load_novel_architecture
    save_novel_architecture = save_novel_architecture
    load_chapter_blueprint = load_chapter_blueprint
    save_chapter_blueprint = save_chapter_blueprint
    load_character_state = load_character_state
    save_character_state = save_character_state
    load_global_summary = load_global_summary
    save_global_summary = save_global_summary
    refresh_chapters_list = refresh_chapters_list
    on_chapter_selected = on_chapter_selected
    save_current_chapter = save_current_chapter
    prev_chapter = prev_chapter
    next_chapter = next_chapter
    test_llm_config = test_llm_config
    test_embedding_config = test_embedding_config
    browse_folder = browse_folder

    # ----------------- 小说管理相关方法 -----------------
    def _on_novel_opened(self, novel):
        """打开小说时的回调函数"""
        self.current_novel_id = novel.novel_id
        # 从同一个NovelManager实例中获取novel对象，确保数据一致性
        novel = self.novel_manager.get_novel(novel.novel_id)
        if not novel:
            return
        # 设置小说路径（优先使用save_path，如果没有则使用默认路径）
        if hasattr(novel, "save_path") and novel.save_path:
            novel_path = novel.save_path
        else:
            novel_path = os.path.abspath(os.path.join("data", "novels", novel.novel_id))
        # 确保novel_path指向小说的实际目录，而不是上层目录
        if os.path.basename(novel_path) != novel.novel_id:
            novel_path = os.path.join(novel_path, novel.novel_id)
        # 设置文件路径变量，用于实际文件操作
        self.filepath_var.set(novel_path)
        # 设置显示路径变量，显示小说标题和路径
        display_path = f"{novel.title} - {novel_path}"
        self.display_path_var.set(display_path)
        # 加载小说标题
        if hasattr(self, 'title_var'):
            self.title_var.set(novel.title)
        # 加载小说参数到UI
        self._load_novel_params(novel)
        # 先加载小说数据
        self._load_novel_data()
        # 显示tab切换模块
        self.tabview._segmented_button.grid()
        # 再切换到主功能页面
        self._show_main_view()

    def _on_tab_changed(self, event=None):
        """处理tab切换事件"""
        # 获取当前选中的tab
        selected_tab = self.tabview.get()

        # 如果离开"主功能"tab，保存小说参数
        if hasattr(self, '_previous_tab') and self._previous_tab == "主功能" and hasattr(self, '_save_novel_params'):
            self._save_novel_params()

        # 如果切换到"小说管理"tab，隐藏tab切换按钮并刷新小说列表
        if selected_tab == "小说管理":
            self.tabview._segmented_button.grid_remove()
            # 刷新小说列表，以显示最新的小说名称
            self.novel_manager_ui.refresh_novels()
        else:
            self.tabview._segmented_button.grid()
            # 如果切换到"主功能"tab，加载小说参数
            if selected_tab == "主功能" and self.current_novel_id:
                # 使用已经在main_window中初始化的NovelManager实例
                novel = self.novel_manager.get_novel(self.current_novel_id)
                if novel:
                    self._load_novel_params(novel)

        # 更新上一个选中的tab
        self._previous_tab = selected_tab

    def _show_main_view(self):
        """显示主功能页面"""
        # 切换到主功能tab
        self.tabview.set("主功能")

    def _show_novel_manager(self):
        """显示小说管理页面"""
        # 切换到小说管理tab
        self.tabview.set("小说管理")
        # 刷新小说列表
        self.novel_manager_ui.refresh_novels()

    def _save_novel_params(self):
        """保存小说参数"""
        # 如果正在加载小说参数，则不保存
        if hasattr(self, '_loading_novel_params') and self._loading_novel_params:
            return

        if not self.current_novel_id:
            return

        # 使用已经在main_window中初始化的NovelManager实例
        manager = self.novel_manager

        # 直接从manager._novels字典中获取novel对象，确保是同一个对象
        if self.current_novel_id not in manager._novels:
            return

        novel = manager._novels[self.current_novel_id]

        # 保存小说标题
        if hasattr(self, 'title_var'):
            novel.title = self.title_var.get()

        # 保存主题
        if hasattr(self, 'topic_text'):
            novel.topic = self.topic_text.get("0.0", "end").strip()

        # 保存类型
        if hasattr(self, 'genre_var'):
            novel.genre = self.genre_var.get()

        # 保存章节数
        if hasattr(self, 'num_chapters_var'):
            try:
                novel.num_chapters = int(self.num_chapters_var.get())
            except ValueError:
                pass

        # 保存每章字数
        if hasattr(self, 'word_number_var'):
            try:
                novel.word_number = int(self.word_number_var.get())
            except ValueError:
                pass

        # 保存章节号
        if hasattr(self, 'chapter_num_var'):
            try:
                novel.chapter_num = int(self.chapter_num_var.get())
            except ValueError:
                pass

        # 保存内容指导
        if hasattr(self, 'user_guide_text'):
            novel.user_guidance = self.user_guide_text.get("0.0", "end").strip()

        # 保存核心人物
        if hasattr(self, 'char_inv_text'):
            novel.characters_involved = self.char_inv_text.get("0.0", "end").strip()

        # 保存关键道具
        if hasattr(self, 'key_items_var'):
            novel.key_items = self.key_items_var.get()

        # 保存空间坐标
        if hasattr(self, 'scene_location_var'):
            novel.scene_location = self.scene_location_var.get()

        # 保存时间压力
        if hasattr(self, 'time_constraint_var'):
            novel.time_constraint = self.time_constraint_var.get()

        # 保存小说到文件
        novel.update_timestamp()
        manager._save_novel(novel)

    def _load_novel_params(self, novel):
        """加载小说参数到UI"""
        # 临时禁用自动保存，避免在加载过程中触发保存
        self._loading_novel_params = True

        # 加载小说标题
        if hasattr(novel, 'title') and hasattr(self, 'title_var'):
            self.title_var.set(novel.title)

        # 加载主题
        if hasattr(novel, 'topic') and hasattr(self, 'topic_text'):
            self.topic_text.delete("0.0", "end")
            self.topic_text.insert("0.0", novel.topic)
            self.topic_var.set(novel.topic)

        # 加载类型
        if hasattr(novel, 'genre') and hasattr(self, 'genre_var'):
            self.genre_var.set(novel.genre)

        # 加载章节数
        if hasattr(novel, 'num_chapters') and hasattr(self, 'num_chapters_var'):
            self.num_chapters_var.set(str(novel.num_chapters))

        # 加载每章字数
        if hasattr(novel, 'word_number') and hasattr(self, 'word_number_var'):
            self.word_number_var.set(str(novel.word_number))

        # 加载完成，启用自动保存
        self._loading_novel_params = False

        # 加载章节号
        if hasattr(novel, 'chapter_num') and hasattr(self, 'chapter_num_var'):
            self.chapter_num_var.set(str(novel.chapter_num))

        # 加载内容指导
        if hasattr(novel, 'user_guidance') and hasattr(self, 'user_guide_text'):
            self.user_guide_text.delete("0.0", "end")
            self.user_guide_text.insert("0.0", novel.user_guidance)
            self.user_guidance_default = novel.user_guidance

        # 加载核心人物
        if hasattr(novel, 'characters_involved') and hasattr(self, 'char_inv_text'):
            self.char_inv_text.delete("0.0", "end")
            self.char_inv_text.insert("0.0", novel.characters_involved)
            self.characters_involved_var.set(novel.characters_involved)

        # 加载关键道具
        if hasattr(novel, 'key_items') and hasattr(self, 'key_items_var'):
            self.key_items_var.set(novel.key_items)

        # 加载空间坐标
        if hasattr(novel, 'scene_location') and hasattr(self, 'scene_location_var'):
            self.scene_location_var.set(novel.scene_location)

        # 加载时间压力
        if hasattr(novel, 'time_constraint') and hasattr(self, 'time_constraint_var'):
            self.time_constraint_var.set(novel.time_constraint)

    def _load_novel_data(self):
        """加载小说数据"""
        # 加载小说架构
        self.load_novel_architecture()
        # 加载章节大纲
        self.load_chapter_blueprint()
        # 加载角色状态
        self.load_character_state()
        # 加载全局摘要
        self.load_global_summary()
        # 刷新章节列表
        self.refresh_chapters_list()
        # 更新小说统计信息
        self._update_novel_stats()

    def _update_novel_stats(self):
        """更新小说统计信息"""
        if not self.current_novel_id:
            return
        
        # 使用已经在main_window中初始化的NovelManager实例
        manager = self.novel_manager
        novel = manager.get_novel(self.current_novel_id)
        if novel:
            # 统计章节数
            novel_path = os.path.join("data", "novels", self.current_novel_id)
            chapter_dir = os.path.join(novel_path, "chapter_content")
            chapter_count = 0
            generated_chapters = 0
            word_count = 0
            
            if os.path.exists(chapter_dir):
                for file in os.listdir(chapter_dir):
                    if file.endswith(".txt"):
                        chapter_count += 1
                        file_path = os.path.join(chapter_dir, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip():
                                    generated_chapters += 1
                                    word_count += len(content)
                        except Exception as e:
                            print(f"读取章节文件 {file} 失败: {e}")
            
            # 更新小说统计
            manager.update_novel_stats(
                self.current_novel_id,
                chapter_count=chapter_count,
                generated_chapters=generated_chapters,
                word_count=word_count
            )
