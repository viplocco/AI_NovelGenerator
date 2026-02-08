# novel_generator/architecture_wizard.py
# -*- coding: utf-8 -*-
"""
小说架构生成向导逻辑类
"""
import os
import json
import logging
from typing import Dict, Optional, Callable
from llm_adapters import create_llm_adapter
from prompt_definitions import (
    core_seed_prompt,
    character_dynamics_prompt,
    world_building_prompt,
    plot_architecture_prompt,
    create_character_state_prompt
)

def get_latest_chapter_text(filepath: str) -> Optional[str]:
    """
    获取最新章节的正文内容

    参数:
        filepath: 项目路径

    返回:
        最新章节的正文内容，如果没有章节则返回None
    """
    chapters_dir = os.path.join(filepath, "chapters")
    if not os.path.exists(chapters_dir):
        return None

    # 获取所有章节文件
    chapter_files = [f for f in os.listdir(chapters_dir) if f.startswith("chapter_") and f.endswith(".txt")]
    if not chapter_files:
        return None

    # 提取章节编号并找到最大编号
    chapter_numbers = []
    for f in chapter_files:
        try:
            num = int(f.replace("chapter_", "").replace(".txt", ""))
            chapter_numbers.append(num)
        except ValueError:
            continue

    if not chapter_numbers:
        return None

    latest_chapter_num = max(chapter_numbers)
    latest_chapter_file = os.path.join(chapters_dir, f"chapter_{latest_chapter_num}.txt")

    if os.path.exists(latest_chapter_file):
        from utils import read_file
        return read_file(latest_chapter_file).strip()

    return None

# 每个步骤的预制用户指导模板
STEP_USER_GUIDANCE = {
    "core_seed": """请生成小说的核心种子，包括：
1. 核心冲突：故事的主要矛盾和冲突点
2. 主题思想：故事想要表达的核心思想
3. 故事基调：故事的整体风格和氛围
4. 核心悬念：吸引读者继续阅读的关键点
5. 创新点：与同类作品的差异化特点
""",

    "character_design": """请生成角色动力学设定，包括：
1. 主角设定：性格、背景、动机、成长弧光
2. 反派设定：与主角的对比和冲突
3. 配角设定：主要配角的定位和作用
4. 角色关系：角色之间的复杂关系网
5. 角色冲突：角色间的矛盾和冲突点
""",

    "character_state": """请生成角色状态表，包括：
1. 基于角色动力学设定生成初始角色状态表
2. 为后续章节生成提供角色状态参考
""",

    "world_building": """请生成世界观设定，包括：
1. 时代背景：古代/现代/未来等
2. 地理环境：地点、地形、气候等
3. 社会结构：政治、经济、文化等
4. 特殊设定：魔法、科技、规则等
5. 世界规则：这个世界特有的规则和限制
""",

    "plot_architecture": """请生成三幕式情节架构，包括：
1. 第一幕：铺垫和激励事件
2. 第二幕：发展和高潮
3. 两幕之间的转折点
4. 第三幕：结局和收尾
5. 每幕的关键事件和情节节点
"""
}

# 步骤定义
STEPS = [
    "core_seed",
    "world_building",
    "character_design",
    "character_state",
    "plot_architecture"
]

# 步骤名称映射
STEP_NAMES = {
    "core_seed": "核心种子",
    "character_design": "核心角色设计",
    "character_state": "角色状态表",
    "world_building": "世界观",
    "plot_architecture": "三幕式情节"
}

class ArchitectureWizardLogic:
    """
    小说架构生成向导的逻辑处理类
    负责管理生成流程、步骤数据、LLM调用等
    """

    def __init__(
        self,
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
        on_stream_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化向导逻辑

        参数:
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
            on_stream_callback: 流式输出回调函数
        """
        self.interface_format = interface_format
        self.api_key = api_key
        self.base_url = base_url
        self.llm_model = llm_model
        self.topic = topic
        self.genre = genre
        self.number_of_chapters = number_of_chapters
        self.word_number = word_number
        self.filepath = filepath
        self.global_guidance = global_guidance
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.on_stream_callback = on_stream_callback

        # 确保目录存在
        os.makedirs(filepath, exist_ok=True)

        # 初始化LLM适配器
        self.llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=llm_model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )

        # 初始化步骤数据
        self.step_data = self._initialize_step_data()

        # 加载已有的部分数据
        self._load_partial_data()

    def _initialize_step_data(self) -> Dict:
        """
        初始化步骤数据结构
        """
        return {
            step: {
                "guidance": "",  # 初始化为空字符串，由_load_partial_data加载
                "result": "",
                "status": "pending"  # pending/completed/modified
            }
            for step in STEPS
        }

    def _load_partial_data(self):
        """
        从partial_architecture.json加载已有的部分数据
        """
        partial_file = os.path.join(self.filepath, "partial_architecture.json")
        if not os.path.exists(partial_file):
            return

        try:
            with open(partial_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 恢复步骤数据
            for step in STEPS:
                if step in data:
                    step_info = data[step]
                    # 加载用户指导
                    if "guidance" in step_info:
                        self.step_data[step]["guidance"] = step_info["guidance"]
                    # 加载生成结果
                    if "result" in step_info:
                        self.step_data[step]["result"] = step_info["result"]
                    # 加载步骤状态
                    if "status" in step_info:
                        self.step_data[step]["status"] = step_info["status"]
                    else:
                        self.step_data[step]["status"] = "completed"

            # 数据迁移：如果存在旧的"character_dynamics"步骤，迁移到"character_design"
            if "character_dynamics" in data and "character_design" not in data:
                step_info = data["character_dynamics"]
                if "result" in step_info:
                    self.step_data["character_design"]["result"] = step_info["result"]
                    self.step_data["character_design"]["status"] = "completed"
                if "guidance" in step_info:
                    self.step_data["character_design"]["guidance"] = step_info["guidance"]

            logging.info("已从partial_architecture.json加载部分数据")
        except Exception as e:
            logging.warning(f"加载partial_architecture.json失败: {e}")

    def _save_partial_data(self):
        """
        保存当前步骤数据到partial_architecture.json
        """
        partial_file = os.path.join(self.filepath, "partial_architecture.json")
        try:
            # 保存所有步骤的完整数据（包括用户指导、生成结果和状态）
            data = {}
            for step in STEPS:
                step_info = self.step_data[step]
                # 如果步骤已完成或已修改，或者有用户指导，则保存
                if step_info["status"] != "pending" or step_info["guidance"]:
                    data[step] = {
                        "guidance": step_info["guidance"],
                        "result": step_info["result"],
                        "status": step_info["status"]
                    }

            with open(partial_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logging.info("已保存部分数据到partial_architecture.json")
        except Exception as e:
            logging.warning(f"保存partial_architecture.json失败: {e}")

    def get_step_guidance(self, step: str) -> str:
        """
        获取指定步骤的用户指导

        参数:
            step: 步骤标识

        返回:
            用户指导文本
        """
        return self.step_data.get(step, {}).get("guidance", "")

    def set_step_guidance(self, step: str, guidance: str):
        """
        设置指定步骤的用户指导

        参数:
            step: 步骤标识
            guidance: 用户指导文本
        """
        if step in self.step_data:
            self.step_data[step]["guidance"] = guidance

    def get_step_result(self, step: str) -> str:
        """
        获取指定步骤的生成结果

        参数:
            step: 步骤标识

        返回:
            生成结果文本
        """
        return self.step_data.get(step, {}).get("result", "")

    def set_step_result(self, step: str, result: str):
        """
        设置指定步骤的生成结果

        参数:
            step: 步骤标识
            result: 生成结果文本
        """
        if step in self.step_data:
            self.step_data[step]["result"] = result
            self.step_data[step]["status"] = "modified"

    def get_step_status(self, step: str) -> str:
        """
        获取指定步骤的状态

        参数:
            step: 步骤标识

        返回:
            状态: pending/completed/modified
        """
        return self.step_data.get(step, {}).get("status", "pending")

    def generate_step(self, step: str, stream_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        生成指定步骤的内容（支持流式输出）

        参数:
            step: 步骤标识
            stream_callback: 流式输出回调函数

        返回:
            是否生成成功
        """
        if step not in STEPS:
            logging.error(f"未知的步骤: {step}")
            return False

        # 获取当前步骤的用户指导
        step_guidance = self.step_data[step]["guidance"]

        # 合并全局用户指导和步骤特定指导
        final_guidance = f"{self.global_guidance}\n\n{step_guidance}" if self.global_guidance else step_guidance

        # 构建prompt
        prompt = self._build_prompt(step, final_guidance)

        try:
            # 调用LLM生成
            result = ""

            # 使用流式输出
            def on_stream(text: str):
                nonlocal result
                result += text
                if stream_callback:
                    stream_callback(text)
                elif self.on_stream_callback:
                    self.on_stream_callback(text)

            # 调用LLM（使用流式输出）
            from novel_generator.stream_utils import invoke_with_cleaning_stream
            result = invoke_with_cleaning_stream(self.llm_adapter, prompt, on_stream)

            if not result.strip():
                logging.error(f"{step}生成失败: 返回空内容")
                return False

            # 保存结果
            self.step_data[step]["result"] = result
            self.step_data[step]["status"] = "completed"

            # 保存部分数据
            self._save_partial_data()

            return True

        except Exception as e:
            logging.error(f"{step}生成失败: {e}")
            return False

    def _build_prompt(self, step: str, guidance: str) -> str:
        """
        构建指定步骤的prompt

        参数:
            step: 步骤标识
            guidance: 用户指导

        返回:
            构建好的prompt
        """
        if step == "core_seed":
            return core_seed_prompt.format(
                topic=self.topic,
                genre=self.genre,
                number_of_chapters=self.number_of_chapters,
                word_number=self.word_number,
                user_guidance=guidance
            )
        elif step == "character_design":
            core_seed = self.step_data["core_seed"]["result"]
            world_building = self.step_data["world_building"]["result"]
            return character_dynamics_prompt.format(
                core_seed=core_seed,
                world_building=world_building,
                user_guidance=guidance
            )
        elif step == "character_state":
            core_seed = self.step_data["core_seed"]["result"]
            world_building = self.step_data["world_building"]["result"]
            character_dynamics = self.step_data["character_design"]["result"]
            latest_chapter = get_latest_chapter_text(self.filepath)
            return create_character_state_prompt.format(
                core_seed=core_seed,
                world_building=world_building,
                character_dynamics=character_dynamics,
                latest_chapter=latest_chapter if latest_chapter else "（暂无章节正文）",
                user_guidance=guidance
            )
        elif step == "world_building":
            core_seed = self.step_data["core_seed"]["result"]
            return world_building_prompt.format(
                core_seed=core_seed,
                user_guidance=guidance
            )
        elif step == "plot_architecture":
            core_seed = self.step_data["core_seed"]["result"]
            character_dynamics = self.step_data["character_design"]["result"]
            world_building = self.step_data["world_building"]["result"]
            return plot_architecture_prompt.format(
                core_seed=core_seed,
                character_dynamics=character_dynamics,
                world_building=world_building,
                user_guidance=guidance
            )
        else:
            raise ValueError(f"未知的步骤: {step}")

    def check_step_dependencies(self, step: str) -> bool:
        """
        检查指定步骤的前置依赖是否完成

        参数:
            step: 步骤标识

        返回:
            前置依赖是否完成
        """
        step_index = STEPS.index(step)
        if step_index == 0:
            return True

        # 检查所有前置步骤是否完成
        for i in range(step_index):
            prev_step = STEPS[i]
            if self.step_data[prev_step]["status"] == "pending":
                return False

        return True

    def mark_subsequent_steps_pending(self, step: str):
        """
        将指定步骤之后的所有步骤标记为待执行

        参数:
            step: 步骤标识
        """
        step_index = STEPS.index(step)
        for i in range(step_index + 1, len(STEPS)):
            next_step = STEPS[i]
            self.step_data[next_step]["status"] = "pending"

    def finalize_architecture(self) -> bool:
        """
        完成架构生成，合并所有步骤内容并保存

        返回:
            是否成功
        """
        try:
            # 检查所有步骤是否完成
            for step in STEPS:
                if self.step_data[step]["status"] == "pending":
                    logging.error(f"步骤{step}未完成，无法完成架构生成")
                    return False

            # 合并所有步骤内容
            final_content = self._merge_step_results()

            # 保存到Novel_architecture.txt
            arch_file = os.path.join(self.filepath, "Novel_architecture.txt")
            from utils import clear_file_content, save_string_to_txt
            clear_file_content(arch_file)
            save_string_to_txt(final_content, arch_file)

            # 删除partial_architecture.json
            partial_file = os.path.join(self.filepath, "partial_architecture.json")
            if os.path.exists(partial_file):
                os.remove(partial_file)
                logging.info("已删除partial_architecture.json")

            logging.info("小说架构生成完成")
            return True

        except Exception as e:
            logging.error(f"完成架构生成失败: {e}")
            return False

    def _merge_step_results(self) -> str:
        """
        合并所有步骤的生成结果

        返回:
            合并后的完整内容
        """
        core_seed_result = self.step_data["core_seed"]["result"]
        character_design_result = self.step_data["character_design"]["result"]
        character_state_result = self.step_data["character_state"]["result"]
        world_building_result = self.step_data["world_building"]["result"]
        plot_arch_result = self.step_data["plot_architecture"]["result"]

        final_content = (
            "#=== 0) 小说设定 ===\n"
            f"主题：{self.topic},类型：{self.genre},篇幅：约{self.number_of_chapters}章（每章{self.word_number}字）\n\n"
            "#=== 1) 核心种子 ===\n"
            f"{core_seed_result}\n\n"
            "#=== 2) 世界观 ===\n"
            f"{world_building_result}\n\n"
            "#=== 3) 角色动力学 ===\n"
            f"{character_design_result}\n\n"
            "#=== 3.1) 角色状态表 ===\n"
            f"{character_state_result}\n\n"
            "#=== 4) 三幕式情节架构 ===\n"
            f"{plot_arch_result}\n"
        )

        return final_content
