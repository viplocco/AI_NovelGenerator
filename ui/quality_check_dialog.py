# ui/quality_check_dialog.py
# -*- coding: utf-8 -*-
"""
章节目录质量检查对话框UI类
"""
import os
import re
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chapter_directory_parser import get_chapter_info_from_blueprint
from .optimize_options_dialog import OptimizeOptionsDialog
from .optimize_progress_dialog import OptimizeProgressDialog
from .optimize_result_dialog import OptimizeResultDialog
from .optimize_detail_dialog import OptimizeDetailDialog
from .optimize_comparison_dialog import OptimizeComparisonDialog


class QualityCheckDialog(ctk.CTkToplevel):
    """
    章节目录质量检查对话框的UI类
    提供章节目录质量检查的界面，支持问题检测和一键优化功能
    """

    def __init__(self, master, directory_content: str, filepath: str, on_apply_optimization=None):
        """
        初始化对话框

        参数:
            master: 父窗口
            directory_content: 章节目录内容
            filepath: 小说保存路径
            on_apply_optimization: 应用优化结果的回调函数
        """
        super().__init__(master)

        self.master = master
        self.directory_content = directory_content
        self.filepath = filepath
        self.on_apply_optimization = on_apply_optimization
        self.issues = []  # 存储检测到的问题
        self.chapter_info_list = []  # 存储章节信息列表

        # 设置窗口
        self._setup_window()

        # 创建UI组件
        self._create_ui()

        # 执行质量检查
        self._perform_quality_check()

    def _setup_window(self):
        """设置窗口属性"""
        self.title("章节目录质量检查")

        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - 1000) // 2
        y = (screen_height - 700) // 2

        # 设置窗口位置和大小
        self.geometry(f'1000x700+{x}+{y}')

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
        self.minsize(800, 600)

        # 设置窗口为模态
        self.grab_set()
        self.focus_set()

    def _create_ui(self):
        """创建UI组件"""
        # 主容器
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 顶部信息区
        self._create_info_area()

        # 问题列表区
        self._create_issues_area()

        # 按钮区
        self._create_button_area()

    def _create_info_area(self):
        """创建顶部信息区"""
        info_frame = ctk.CTkFrame(self.main_container)
        info_frame.pack(fill="x", pady=(0, 10))

        # 标题
        ctk.CTkLabel(
            info_frame,
            text="目录质量检查结果",
            font=("Microsoft YaHei", 14, "bold")
        ).pack(side="left", padx=10, pady=10)

        # 问题数量标签
        self.issue_count_label = ctk.CTkLabel(
            info_frame,
            text="发现问题：0个",
            font=("Microsoft YaHei", 12)
        )
        self.issue_count_label.pack(side="right", padx=10, pady=10)

    def _create_issues_area(self):
        """创建问题列表区"""
        issues_frame = ctk.CTkFrame(self.main_container)
        issues_frame.pack(fill="both", expand=True, pady=(0, 10))

        ctk.CTkLabel(
            issues_frame,
            text="问题列表：",
            font=("Microsoft YaHei", 11)
        ).pack(anchor="w", padx=5, pady=(5, 3))

        # 问题列表文本框
        self.issues_text = ctk.CTkTextbox(
            issues_frame,
            font=("Microsoft YaHei", 11)
        )
        self.issues_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # 初始提示
        self.issues_text.insert("end", "正在检查目录质量，请稍候...\n")

    def _create_button_area(self):
        """创建按钮区"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", pady=(10, 0))

        # 一键优化按钮
        self.btn_optimize = ctk.CTkButton(
            button_frame,
            text="一键优化",
            command=self._on_optimize,
            font=("Microsoft YaHei", 11),
            fg_color=("#28a745", "#28a745"),
            hover_color=("#218838", "#218838"),
            text_color_disabled="gray"
        )
        self.btn_optimize.pack(side="left", padx=5, pady=10)

        # 关闭按钮
        self.btn_close = ctk.CTkButton(
            button_frame,
            text="关闭",
            command=self._on_close,
            font=("Microsoft YaHei", 11)
        )
        self.btn_close.pack(side="right", padx=5, pady=10)

    def _perform_quality_check(self):
        """执行目录质量检查"""
        self.issues = []
        self.chapter_info_list = []

        # 解析章节目录
        try:
            # 提取所有章节
            chapter_pattern = r"第\s*(\d+)\s*章.*?(?=第\s*\d+\s*章|$)"
            chapters = re.findall(chapter_pattern, self.directory_content, re.DOTALL)

            # 为每个章节获取信息
            for chapter_num in range(1, len(chapters) + 1):
                chapter_info = get_chapter_info_from_blueprint(self.directory_content, chapter_num)
                if chapter_info:
                    self.chapter_info_list.append(chapter_info)

            # 执行各项检查
            self._check_cultivation_consistency()
            self._check_spatial_coordinates()
            self._check_chapter_descriptions()
            self._check_character_consistency()
            self._check_plot_continuity()

            # 更新UI显示
            self._update_issues_display()

        except Exception as e:
            self.issues_text.delete("1.0", "end")
            self.issues_text.insert("end", f"检查过程中出现错误: {str(e)}\n")
            self.issue_count_label.configure(text=f"发现问题：0个")

    def _check_cultivation_consistency(self):
        """检查主角修为一致性"""
        # 如果没有章节信息，跳过检查
        if not self.chapter_info_list:
            return

        # 获取修为等级列表（假设修为等级是递增的）
        cultivation_levels = []
        for chapter_info in self.chapter_info_list:
            surface_cultivation = chapter_info.get("surface_cultivation", "未设定")
            actual_cultivation = chapter_info.get("actual_cultivation", "未设定")
            cultivation_levels.append({
                "chapter": chapter_info.get("chapter_number", 0),
                "surface": surface_cultivation,
                "actual": actual_cultivation
            })

        # 检查修为是否合理递增
        for i in range(1, len(cultivation_levels)):
            prev_level = cultivation_levels[i-1]
            curr_level = cultivation_levels[i]

            # 如果表面修为降低，且没有特殊说明，则记录问题
            if (prev_level["surface"] != "未设定" and 
                curr_level["surface"] != "未设定" and
                prev_level["surface"] != curr_level["surface"]):

                # 这里可以添加更复杂的逻辑来判断修为是否合理
                # 例如，检查章节摘要中是否有修为降低的说明
                self.issues.append({
                    "type": "修为变化",
                    "chapter": curr_level["chapter"],
                    "description": f"第{curr_level['chapter']}章表面修为从{prev_level['surface']}变为{curr_level['surface']}，请确认是否符合故事情节需要。",
                    "severity": "警告"
                })

            # 如果实际修为降低，且没有特殊说明，则记录问题
            if (prev_level["actual"] != "未设定" and 
                curr_level["actual"] != "未设定" and
                prev_level["actual"] != curr_level["actual"]):

                self.issues.append({
                    "type": "修为变化",
                    "chapter": curr_level["chapter"],
                    "description": f"第{curr_level['chapter']}章实际修为从{prev_level['actual']}变为{curr_level['actual']}，请确认是否符合故事情节需要。",
                    "severity": "警告"
                })

    def _check_spatial_coordinates(self):
        """检查空间坐标合理性"""
        # 如果没有章节信息，跳过检查
        if not self.chapter_info_list:
            return

        # 检查空间坐标是否合理变化
        for i in range(1, len(self.chapter_info_list)):
            prev_chapter = self.chapter_info_list[i-1]
            curr_chapter = self.chapter_info_list[i]

            prev_location = prev_chapter.get("scene_location", "未设定")
            curr_location = curr_chapter.get("scene_location", "未设定")

            # 如果场景地点突然变化，且没有合理过渡，则记录问题
            if (prev_location != "未设定" and 
                curr_location != "未设定" and 
                prev_location != curr_location):

                # 检查当前章节摘要中是否有场景转移的说明
                curr_summary = curr_chapter.get("chapter_summary", "")
                if not any(keyword in curr_summary for keyword in ["转移", "前往", "到达", "穿越", "传送", "进入"]):
                    self.issues.append({
                        "type": "场景变化",
                        "chapter": curr_chapter.get("chapter_number", 0),
                        "description": f"第{curr_chapter.get('chapter_number', 0)}章场景从{prev_location}变为{curr_location}，但章节摘要中未提及场景转移，请确认是否合理。",
                        "severity": "警告"
                    })

    def _check_chapter_descriptions(self):
        """检查章节描述合理性"""
        # 检查每个章节的描述是否完整
        for chapter_info in self.chapter_info_list:
            chapter_num = chapter_info.get("chapter_number", 0)

            # 检查章节标题
            chapter_title = chapter_info.get("chapter_title", "")
            if not chapter_title or chapter_title == "未命名":
                self.issues.append({
                    "type": "章节信息",
                    "chapter": chapter_num,
                    "description": f"第{chapter_num}章缺少标题。",
                    "severity": "错误"
                })

            # 检查章节摘要
            chapter_summary = chapter_info.get("chapter_summary", "")
            if not chapter_summary or chapter_summary == "未设定":
                self.issues.append({
                    "type": "章节信息",
                    "chapter": chapter_num,
                    "description": f"第{chapter_num}章缺少摘要。",
                    "severity": "错误"
                })

            # 检查主要人物
            characters = chapter_info.get("characters_involved", "")
            if not characters or characters == "未指定":
                self.issues.append({
                    "type": "章节信息",
                    "chapter": chapter_num,
                    "description": f"第{chapter_num}章未指定主要人物。",
                    "severity": "警告"
                })

    def _check_character_consistency(self):
        """检查角色一致性"""
        # 如果没有章节信息，跳过检查
        if not self.chapter_info_list:
            return

        # 收集所有出现过的角色
        all_characters = set()
        for chapter_info in self.chapter_info_list:
            characters = chapter_info.get("characters_involved", "")
            if characters and characters != "未指定":
                # 分割角色列表（支持中英文逗号）
                for char in characters.replace('，', ',').split(','):
                    char_name = char.strip()
                    if char_name:
                        all_characters.add(char_name)

        # 检查角色是否突然消失或出现
        if len(all_characters) > 0:
            # 检查每个角色是否在连续的章节中出现
            for char in all_characters:
                # 找到角色首次出现的章节
                first_appearance = None
                last_appearance = None

                for chapter_info in self.chapter_info_list:
                    characters = chapter_info.get("characters_involved", "")
                    if characters and char in characters.replace('，', ','):
                        if first_appearance is None:
                            first_appearance = chapter_info.get("chapter_number", 0)
                        last_appearance = chapter_info.get("chapter_number", 0)

                # 如果角色在中间章节突然消失，且没有合理的解释，则记录问题
                if first_appearance and last_appearance and (last_appearance - first_appearance) > 5:
                    # 检查角色是否在中间章节中消失
                    for i in range(first_appearance + 1, last_appearance):
                        chapter_info = self.chapter_info_list[i-1]
                        characters = chapter_info.get("characters_involved", "")
                        if characters and char not in characters.replace('，', ','):
                            self.issues.append({
                                "type": "角色一致性",
                                "chapter": i,
                                "description": f"角色{char}在第{first_appearance}章到第{last_appearance}章之间出现，但在第{i}章未出现，请确认是否合理。",
                                "severity": "提示"
                            })
                            break  # 只记录一次

    def _check_plot_continuity(self):
        """检查剧情连贯性"""
        # 检查章节之间的剧情是否连贯
        for i in range(1, len(self.chapter_info_list)):
            prev_chapter = self.chapter_info_list[i-1]
            curr_chapter = self.chapter_info_list[i]

            prev_summary = prev_chapter.get("chapter_summary", "")
            curr_summary = curr_chapter.get("chapter_summary", "")

            # 如果前一章有悬念或伏笔，但后一章没有回应，则记录问题
            prev_foreshadow = prev_chapter.get("foreshadowing", "")
            if prev_foreshadow and prev_foreshadow != "无":
                # 检查当前章节是否回应了前一章的伏笔
                if not any(keyword in curr_summary for keyword in ["揭示", "发现", "解决", "面对", "处理"]):
                    self.issues.append({
                        "type": "剧情连贯性",
                        "chapter": curr_chapter.get("chapter_number", 0),
                        "description": f"第{prev_chapter.get('chapter_number', 0)}章设置了伏笔（{prev_foreshadow}），但第{curr_chapter.get('chapter_number', 0)}章似乎未回应，请确认是否合理。",
                        "severity": "提示"
                    })

    def _update_issues_display(self):
        """更新问题列表显示"""
        self.issues_text.delete("1.0", "end")

        if not self.issues:
            self.issues_text.insert("end", "✓ 未发现问题，目录质量良好！\n")
            self.issue_count_label.configure(text="发现问题：0个")
            self.btn_optimize.configure(state="disabled")
        else:
            # 按严重程度排序：错误 > 警告 > 提示
            severity_order = {"错误": 0, "警告": 1, "提示": 2}
            self.issues.sort(key=lambda x: severity_order.get(x.get("severity", "提示"), 2))

            # 按类型分组显示问题
            current_type = None
            for issue in self.issues:
                issue_type = issue.get("type", "其他")

                # 如果类型变化，添加类型标题
                if issue_type != current_type:
                    self.issues_text.insert("end", f"\n【{issue_type}】\n", "type")
                    current_type = issue_type

                # 添加问题详情
                severity = issue.get("severity", "提示")
                severity_icon = {"错误": "✗", "警告": "⚠", "提示": "ℹ"}.get(severity, "ℹ")

                self.issues_text.insert("end", f"{severity_icon} 第{issue.get('chapter', 0)}章: {issue.get('description', '')}\n")

            # 更新问题数量
            self.issue_count_label.configure(text=f"发现问题：{len(self.issues)}个")
            self.btn_optimize.configure(state="normal")

    def _on_optimize(self):
        """处理一键优化按钮点击"""
        if not self.issues:
            return

        # 显示优化选项对话框
        optimize_options_dialog = OptimizeOptionsDialog(
            self,
            self.issues,
            self._on_optimize_with_options
        )
        try:
            optimize_options_dialog.wait_window()
        except Exception as e:
            print(f"等待优化选项对话框关闭时出错: {e}")

    def _on_optimize_with_options(self, optimize_params):
        """根据优化选项执行优化"""
        # 筛选需要优化的问题
        selected_issues = []
        for issue in self.issues:
            issue_type = issue.get("type", "")
            # 根据优化范围筛选问题
            if (issue_type == "修为变化" and optimize_params["ranges"]["cultivation"]) or \
               (issue_type == "场景变化" and optimize_params["ranges"]["spatial"]) or \
               (issue_type == "章节信息" and optimize_params["ranges"]["chapter_info"]) or \
               (issue_type == "角色一致性" and optimize_params["ranges"]["character"]) or \
               (issue_type == "剧情连贯性" and optimize_params["ranges"]["plot"]):
                selected_issues.append(issue)

        if not selected_issues:
            messagebox.showinfo("提示", "没有选择需要优化的问题")
            return

        # 显示优化进度对话框
        progress_dialog = OptimizeProgressDialog(
            self,
            len(selected_issues),
            self._on_cancel_optimize
        )

        # 更新窗口，确保对话框完全创建
        self.update()

        # 执行优化
        self._perform_optimization(selected_issues, optimize_params, progress_dialog)

        # 等待进度对话框关闭
        try:
            if progress_dialog.winfo_exists():
                progress_dialog.wait_window()
        except Exception as e:
            print(f"等待进度对话框关闭时出错: {e}")

    def _perform_optimization(self, issues, optimize_params, progress_dialog):
        """执行实际的优化逻辑"""
        # 备份原始目录
        if optimize_params["advanced"]["backup"]:
            self._backup_original_content()

        # 初始化优化结果统计
        optimization_results = {
            "cultivation": {"total": 0, "processed": 0},
            "spatial": {"total": 0, "processed": 0},
            "chapter_info": {"total": 0, "processed": 0},
            "character": {"total": 0, "processed": 0},
            "plot": {"total": 0, "processed": 0}
        }

        # 统计各类型问题数量
        for issue in issues:
            issue_type = issue.get("type", "")
            if issue_type in optimization_results:
                optimization_results[issue_type]["total"] += 1

        # 执行优化
        for i, issue in enumerate(issues):
            # 更新进度
            progress_dialog.update_progress(
                i + 1,
                len(issues),
                f"第{issue.get('chapter', 0)}章 - {issue.get('type', '')}"
            )

            # 根据问题类型执行不同的优化策略
            issue_type = issue.get("type", "")
            if issue_type == "修为变化":
                self._optimize_cultivation_issue(issue)
                optimization_results["cultivation"]["processed"] += 1
            elif issue_type == "场景变化":
                self._optimize_spatial_issue(issue)
                optimization_results["spatial"]["processed"] += 1
            elif issue_type == "章节信息":
                self._optimize_chapter_info_issue(issue)
                optimization_results["chapter_info"]["processed"] += 1
            elif issue_type == "角色一致性":
                self._optimize_character_issue(issue)
                optimization_results["character"]["processed"] += 1
            elif issue_type == "剧情连贯性":
                self._optimize_plot_issue(issue)
                optimization_results["plot"]["processed"] += 1

            # 模拟处理延迟
            self.after(100, lambda: None)

        # 关闭进度对话框
        try:
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()
        except Exception as e:
            print(f"关闭进度对话框时出错: {e}")

        # 显示优化结果对话框
        result_dialog = OptimizeResultDialog(
            self,
            optimization_results,
            self._on_apply_optimization,
            self._on_cancel_optimization
        )
        try:
            result_dialog.wait_window()
        except Exception as e:
            print(f"等待结果对话框关闭时出错: {e}")

    def _optimize_cultivation_issue(self, issue):
        """优化修为变化问题"""
        # 这里可以添加实际的修为优化逻辑
        # 例如，调用LLM来生成修为变化的解释
        pass

    def _optimize_spatial_issue(self, issue):
        """优化场景变化问题"""
        # 这里可以添加实际的场景优化逻辑
        # 例如，调用LLM来生成场景转移的说明
        pass

    def _optimize_chapter_info_issue(self, issue):
        """优化章节信息问题"""
        # 这里可以添加实际的章节信息优化逻辑
        # 例如，自动填充缺失的章节标题或摘要
        pass

    def _optimize_character_issue(self, issue):
        """优化角色一致性问题"""
        # 这里可以添加实际的角色一致性优化逻辑
        # 例如，建议在缺失章节中添加角色出场
        pass

    def _optimize_plot_issue(self, issue):
        """优化剧情连贯性问题"""
        # 这里可以添加实际的剧情连贯性优化逻辑
        # 例如，建议在适当章节添加伏笔回应
        pass

    def _backup_original_content(self):
        """备份原始目录内容"""
        try:
            import datetime
            backup_dir = os.path.join(self.filepath, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"Novel_directory_backup_{timestamp}.txt")

            save_string_to_txt(self.directory_content, backup_file)
        except Exception as e:
            print(f"备份失败: {e}")

    def _on_apply_optimization(self, optimization_results):
        """应用优化结果"""
        # 调用回调函数，将优化结果传递给主窗口
        if self.on_apply_optimization:
            self.on_apply_optimization(optimization_results)

    def _on_cancel_optimization(self):
        """取消优化"""
        pass

    def _on_cancel_optimize(self):
        """取消优化进度对话框"""
        pass

    def _on_close(self):
        """处理关闭按钮点击"""
        self.destroy()
