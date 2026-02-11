# novel_generator/chapter.py
# -*- coding: utf-8 -*-
"""
章节草稿生成及获取历史章节文本、当前章节摘要等
"""
import os
import json
import logging
import re  # 添加re模块导入
import time  # 添加time模块导入
from llm_adapters import create_llm_adapter
from prompt_definitions import (
    first_chapter_draft_prompt, 
    next_chapter_draft_prompt, 
    summarize_recent_chapters_prompt,
    knowledge_filter_prompt,
    knowledge_search_prompt
)
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import (
    get_relevant_context_from_vector_store,
    load_vector_store  # 添加导入
)

# ============== 角色状态智能筛选功能 ==============

def get_relevant_character_state(filepath: str, characters_involved: str, current_chapter: int) -> str:
    """
    根据章节涉及角色，智能提取相关角色状态
    
    参数:
        filepath: 小说保存路径
        characters_involved: 章节目录中指定的核心人物（逗号分隔）
        current_chapter: 当前章节号
    
    返回:
        筛选后的角色状态文本
    """
    character_state_file = os.path.join(filepath, "character_state.txt")
    
    if not os.path.exists(character_state_file):
        return "（无角色状态）"
    
    full_state = read_file(character_state_file)
    
    # 如果角色状态较短（<8000字），直接返回全部
    if len(full_state) < 8000:
        return full_state
    
    # 如果未指定角色，使用索引提取活跃角色
    if not characters_involved or characters_involved.strip() in ["", "未指定", "无"]:
        return _extract_active_characters(full_state, filepath, current_chapter)
    
    # 解析指定角色列表（支持中英文逗号）
    specified_chars = []
    for c in characters_involved.replace('，', ',').split(','):
        char_name = c.strip()
        if char_name and char_name not in specified_chars:
            specified_chars.append(char_name)
    
    # 尝试提取指定角色的状态
    relevant_state = _extract_character_blocks(full_state, specified_chars)
    
    # 如果提取结果太短（<500字），可能匹配失败，返回活跃角色
    if len(relevant_state) < 500:
        return _extract_active_characters(full_state, filepath, current_chapter)
    
    # 在提取结果末尾添加"新出场角色"部分（如果原状态中有）
    new_chars_section = _extract_new_characters_section(full_state)
    if new_chars_section and new_chars_section not in relevant_state:
        relevant_state += "\n\n" + new_chars_section
    
    return relevant_state


def _extract_character_blocks(full_state: str, char_names: list) -> str:
    """
    从完整状态中提取指定角色的状态块
    
    参数:
        full_state: 完整的角色状态文本
        char_names: 需要提取的角色名列表
    
    返回:
        提取的角色状态文本
    """
    blocks = []
    current_block = []
    capturing = False
    current_char = None
    
    lines = full_state.split('\n')
    
    for i, line in enumerate(lines):
        # 检测角色名行（角色名开头 + 冒号，且不是属性行）
        is_char_header = False
        stripped_line = line.strip()
        
        # 跳过属性行和子属性行
        if stripped_line.startswith('├') or stripped_line.startswith('│') or stripped_line.startswith('└'):
            if capturing:
                current_block.append(line)
            continue
        
        # 检查是否是角色标题行
        for name in char_names:
            if stripped_line == f"{name}：" or stripped_line == f"{name}:" or stripped_line.startswith(f"{name}：") or stripped_line.startswith(f"{name}:"):
                is_char_header = True
                # 保存之前的块
                if capturing and current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
                current_char = name
                capturing = True
                break
        
        if not is_char_header:
            if capturing:
                # 检查是否是另一个角色的开始（非属性行且包含冒号）
                if stripped_line and '：' in stripped_line or ':' in stripped_line:
                    # 检查是否是新角色
                    possible_name = stripped_line.split('：')[0].split(':')[0].strip()
                    if possible_name and not possible_name.startswith('├') and not possible_name.startswith('│'):
                        # 这可能是新角色的开始
                        if possible_name not in char_names:
                            # 结束当前捕获
                            blocks.append('\n'.join(current_block))
                            capturing = False
                            current_block = []
                            continue
                
                current_block.append(line)
    
    # 保存最后一个块
    if capturing and current_block:
        blocks.append('\n'.join(current_block))
    
    return '\n\n'.join(blocks)


def _extract_active_characters(full_state: str, filepath: str, current_chapter: int) -> str:
    """
    提取活跃角色状态（用于状态文件过大时）
    活跃定义：最近30章内出现过的角色
    
    参数:
        full_state: 完整的角色状态文本
        filepath: 小说保存路径
        current_chapter: 当前章节号
    
    返回:
        活跃角色的状态文本
    """
    index_file = os.path.join(filepath, "character_index.json")
    
    # 如果没有索引文件，返回状态文本的后3000字（假设最近更新的角色更相关）
    if not os.path.exists(index_file):
        return full_state[-3000:] if len(full_state) > 3000 else full_state
    
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # 获取活跃角色名（最近30章内出现过）
        active_threshold = 30
        active_chars = []
        for name, info in index.items():
            last_chapter = info.get('last_chapter', 0)
            if current_chapter - last_chapter <= active_threshold:
                active_chars.append(name)
        
        if not active_chars:
            # 没有活跃角色，返回全部
            return full_state
        
        # 提取活跃角色状态
        result = _extract_character_blocks(full_state, active_chars)
        
        # 添加新出场角色部分
        new_chars_section = _extract_new_characters_section(full_state)
        if new_chars_section and new_chars_section not in result:
            result += "\n\n" + new_chars_section
        
        return result
        
    except Exception as e:
        logging.warning(f"读取角色索引失败: {e}，使用截取方式")
        return full_state[-3000:] if len(full_state) > 3000 else full_state


def _extract_new_characters_section(full_state: str) -> str:
    """
    提取"新出场角色"部分
    
    参数:
        full_state: 完整的角色状态文本
    
    返回:
        新出场角色部分文本，如果没有则返回空字符串
    """
    markers = ["新出场角色：", "新出场角色:", "新角色：", "新角色:"]
    
    for marker in markers:
        if marker in full_state:
            idx = full_state.find(marker)
            return full_state[idx:].strip()
    
    return ""

def get_last_n_chapters_text(chapters_dir: str, current_chapter_num: int, n: int = 3) -> list:
    """
    从目录 chapters_dir 中获取最近 n 章的文本内容，返回文本列表。
    """
    texts = []
    start_chap = max(1, current_chapter_num - n)
    for c in range(start_chap, current_chapter_num):
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")
        if os.path.exists(chap_file):
            text = read_file(chap_file).strip()
            texts.append(text)
        else:
            texts.append("")
    return texts

def summarize_recent_chapters(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    chapters_text_list: list,
    novel_number: int,            # 新增参数
    chapter_info: dict,           # 新增参数
    next_chapter_info: dict,      # 新增参数
    timeout: int = 600
) -> str:  # 修改返回值类型为 str，不再是 tuple
    """
    根据前三章内容生成当前章节的精准摘要。
    如果解析失败，则返回空字符串。
    """
    try:
        combined_text = "\n".join(chapters_text_list).strip()
        if not combined_text:
            return ""
            
        # 限制组合文本长度
        max_combined_length = 4000
        if len(combined_text) > max_combined_length:
            combined_text = combined_text[-max_combined_length:]
            
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        # 确保所有参数都有默认值
        chapter_info = chapter_info or {}
        next_chapter_info = next_chapter_info or {}
        
        prompt = summarize_recent_chapters_prompt.format(
            combined_text=combined_text,
            novel_number=novel_number,
            chapter_title=chapter_info.get("chapter_title", "未命名"),
            chapter_role=chapter_info.get("chapter_role", "常规章节"),
            chapter_purpose=chapter_info.get("chapter_purpose", "内容推进"),
            suspense_level=chapter_info.get("suspense_level", "中等"),
            foreshadowing=chapter_info.get("foreshadowing", "无"),
            plot_twist_level=chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            surface_cultivation=chapter_info.get("surface_cultivation", "未设定"),
            actual_cultivation=chapter_info.get("actual_cultivation", "未设定"),
            spatial_coordinates=chapter_info.get("scene_location", "未设定"),
            chapter_summary=chapter_info.get("chapter_summary", ""),
            next_chapter_number=novel_number + 1,
            next_chapter_title=next_chapter_info.get("chapter_title", "（未命名）"),
            next_chapter_role=next_chapter_info.get("chapter_role", "过渡章节"),
            next_chapter_purpose=next_chapter_info.get("chapter_purpose", "承上启下"),
            next_chapter_summary=next_chapter_info.get("chapter_summary", "衔接过渡内容"),
            next_chapter_suspense_level=next_chapter_info.get("suspense_level", "中等"),
            next_chapter_foreshadowing=next_chapter_info.get("foreshadowing", "无特殊伏笔"),
            next_chapter_plot_twist_level=next_chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            next_surface_cultivation=next_chapter_info.get("surface_cultivation", "未设定"),
            next_actual_cultivation=next_chapter_info.get("actual_cultivation", "未设定"),
            next_spatial_coordinates=next_chapter_info.get("scene_location", "未设定")
        )
        
        response_text = invoke_with_cleaning(llm_adapter, prompt)
        summary = extract_summary_from_response(response_text)
        
        if not summary:
            logging.warning("Failed to extract summary, using full response")
            return response_text[:2000]  # 限制长度
            
        return summary[:2000]  # 限制摘要长度
        
    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        return ""

def extract_summary_from_response(response_text: str) -> str:
    """从响应文本中提取摘要部分"""
    if not response_text:
        return ""
        
    # 查找摘要标记
    summary_markers = [
        "当前章节摘要:", 
        "章节摘要:",
        "摘要:",
        "本章摘要:"
    ]
    
    for marker in summary_markers:
        if (marker in response_text):
            parts = response_text.split(marker, 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    return response_text.strip()

def format_chapter_info(chapter_info: dict) -> str:
    """将章节信息字典格式化为文本"""
    template = """
章节编号：第{number}章
章节标题：《{title}》
章节定位：{role}
核心作用：{purpose}
主要人物：{characters}
关键道具：{items}
场景地点：{location}
伏笔设计：{foreshadow}
悬念密度：{suspense}
转折程度：{twist}
主角修为：表面修为{surface_cultivation} | 实际实力{actual_cultivation}
章节简述：{summary}
"""
    return template.format(
        number=chapter_info.get('chapter_number', '未知'),
        title=chapter_info.get('chapter_title', '未知'),
        role=chapter_info.get('chapter_role', '未知'),
        purpose=chapter_info.get('chapter_purpose', '未知'),
        characters=chapter_info.get('characters_involved', '未指定'),
        items=chapter_info.get('key_items', '未指定'),
        location=chapter_info.get('scene_location', '未指定'),
        foreshadow=chapter_info.get('foreshadowing', '无'),
        suspense=chapter_info.get('suspense_level', '一般'),
        twist=chapter_info.get('plot_twist_level', '★☆☆☆☆'),
        surface_cultivation=chapter_info.get('surface_cultivation', '未设定'),
        actual_cultivation=chapter_info.get('actual_cultivation', '未设定'),
        summary=chapter_info.get('chapter_summary', '未提供')
    )

def parse_search_keywords(response_text: str) -> list:
    """解析新版关键词格式（示例输入：'科技公司·数据泄露\n地下实验室·基因编辑'）"""
    return [
        line.strip().replace('·', ' ')
        for line in response_text.strip().split('\n')
        if '·' in line
    ][:5]  # 最多取5组

def apply_content_rules(texts: list, novel_number: int) -> list:
    """应用内容处理规则"""
    processed = []
    for text in texts:
        if re.search(r'第[\d]+章', text) or re.search(r'chapter_[\d]+', text):
            chap_nums = list(map(int, re.findall(r'\d+', text)))
            recent_chap = max(chap_nums) if chap_nums else 0
            time_distance = novel_number - recent_chap
            
            if time_distance <= 2:
                processed.append(f"[SKIP] 跳过近章内容：{text[:120]}...")
            elif 3 <= time_distance <= 5:
                processed.append(f"[MOD40%] {text}（需修改≥40%）")
            else:
                processed.append(f"[OK] {text}（可引用核心）")
        else:
            processed.append(f"[PRIOR] {text}（优先使用）")
    return processed

def apply_knowledge_rules(contexts: list, chapter_num: int) -> list:
    """应用知识库使用规则"""
    processed = []
    for text in contexts:
        # 检测历史章节内容
        if "第" in text and "章" in text:
            # 提取章节号判断时间远近
            chap_nums = [int(s) for s in text.split() if s.isdigit()]
            recent_chap = max(chap_nums) if chap_nums else 0
            time_distance = chapter_num - recent_chap
            
            # 相似度处理规则
            if time_distance <= 3:  # 近三章内容
                processed.append(f"[历史章节限制] 跳过近期内容: {text[:50]}...")
                continue
                
            # 允许引用但需要转换
            processed.append(f"[历史参考] {text} (需进行30%以上改写)")
        else:
            # 第三方知识优先处理
            processed.append(f"[外部知识] {text}")
    return processed

def get_filtered_knowledge_context(
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    embedding_adapter,
    filepath: str,
    chapter_info: dict,
    retrieved_texts: list,
    max_tokens: int = 2048,
    timeout: int = 600
) -> str:
    """优化后的知识过滤处理"""
    if not retrieved_texts:
        return "（无相关知识库内容）"

    try:
        processed_texts = apply_knowledge_rules(retrieved_texts, chapter_info.get('chapter_number', 0))
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        # 限制检索文本长度并格式化
        formatted_texts = []
        max_text_length = 600
        for i, text in enumerate(processed_texts, 1):
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            formatted_texts.append(f"[预处理结果{i}]\n{text}")

        # 使用格式化函数处理章节信息
        formatted_chapter_info = (
            f"当前章节定位：{chapter_info.get('chapter_role', '')}\n"
            f"核心目标：{chapter_info.get('chapter_purpose', '')}\n"
            f"关键要素：{chapter_info.get('characters_involved', '')} | "
            f"{chapter_info.get('key_items', '')} | "
            f"{chapter_info.get('scene_location', '')}"
        )

        prompt = knowledge_filter_prompt.format(
            chapter_number=chapter_info.get('chapter_number', ''),
            chapter_title=chapter_info.get('chapter_title', ''),
            chapter_role=chapter_info.get('chapter_role', ''),
            chapter_purpose=chapter_info.get('chapter_purpose', ''),
            plot_type=chapter_info.get('chapter_purpose', ''),  # Using chapter_purpose as plot_type
            tension_level=chapter_info.get('suspense_level', ''),
            similarity_threshold="0.7",  # Default similarity threshold
            value_density_requirement="中等",  # Default value density requirement
            filter_primary_goal="获取与当前章节高度相关的内容",  # Default primary goal
            filter_secondary_goals="补充背景信息、提供细节描述",  # Default secondary goals
            retrieved_texts="\n\n".join(formatted_texts) if formatted_texts else "（无检索结果）"
        )
        
        filtered_content = invoke_with_cleaning(llm_adapter, prompt)
        return filtered_content if filtered_content else "（知识内容过滤失败）"
        
    except Exception as e:
        logging.error(f"Error in knowledge filtering: {str(e)}")
        return "（内容过滤过程出错）"

def build_chapter_prompt(
    api_key: str,
    base_url: str,
    model_name: str,
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    prompt_callback: callable = None,
    progress_callback: callable = None
) -> str:
    """
    构造当前章节的请求提示词（完整实现版）
    修改重点：
    1. 优化知识库检索流程
    2. 新增内容重复检测机制
    3. 集成提示词应用规则

    参数:
        prompt_callback: 提示词构建进度回调函数，接收文本参数
        progress_callback: 进度更新回调函数，接收(progress, description)参数
    """
    # 读取基础文件
    if progress_callback:
        progress_callback(0.1, "读取基础文件")

    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    novel_architecture_text = read_file(arch_file)
    directory_file = os.path.join(filepath, "Novel_directory.txt")

    # 检查章节目录文件是否存在
    if not os.path.exists(directory_file):
        print(f"警告: 章节目录文件不存在: {directory_file}")
        blueprint_text = ""
    else:
        blueprint_text = read_file(directory_file)
        if not blueprint_text.strip():
            print(f"警告: 章节目录文件为空: {directory_file}")
        else:
            pass
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    global_summary_text = read_file(global_summary_file)
    
    # 使用智能角色筛选功能，只获取相关角色状态
    # 获取章节信息中的角色信息
    temp_chapter_info = get_chapter_info_from_blueprint(blueprint_text if 'blueprint_text' in dir() else read_file(directory_file), novel_number)
    temp_characters = temp_chapter_info.get("characters_involved", characters_involved) if temp_chapter_info else characters_involved
    character_state_text = get_relevant_character_state(filepath, temp_characters, novel_number)
    
    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    plot_arcs_text = ""
    if os.path.exists(plot_arcs_file):
        plot_arcs_text = read_file(plot_arcs_file)
    
    # 获取章节信息
    if not blueprint_text or not blueprint_text.strip():
        print(f"错误: 章节目录为空，无法获取章节 {novel_number} 的信息")
        print(f"提示: 请先生成章节目录（步骤2）")
        # 构建默认提示词
        default_prompt = next_chapter_draft_prompt.format(
            user_guidance=user_guidance if user_guidance else "无特殊指导",
            global_summary=global_summary_text if global_summary_text else "（无全局摘要）",
            previous_chapter_excerpt="（无前文）",
            character_state=character_state_text if character_state_text else "（无角色状态）",
            short_summary="（无章节摘要）",
            novel_number=novel_number,
            chapter_title=f"第{novel_number}章",
            chapter_role="未设定",
            chapter_purpose="未设定",
            suspense_level="未设定",
            foreshadowing="未设定",
            plot_twist_level="★☆☆☆☆",
            chapter_summary="未设定",
            word_number=word_number,
            characters_involved=characters_involved if characters_involved else "未指定",
            key_items=key_items if key_items else "未指定",
            scene_location=scene_location if scene_location else "未设定",
            time_constraint=time_constraint if time_constraint else "未设定",
            next_chapter_number=novel_number + 1,
            next_chapter_title=f"第{novel_number + 1}章",
            next_chapter_role="未设定",
            next_chapter_purpose="未设定",
            next_chapter_suspense_level="未设定",
            next_chapter_foreshadowing="未设定",
            next_chapter_plot_twist_level="★☆☆☆☆",
            next_chapter_summary="未设定",
            filtered_context="（无知识库内容）"
        )
        # 调用回调函数显示提示词内容
        if prompt_callback:
            prompt_callback(f"\n[完整提示词]\n{default_prompt}")
        if progress_callback:
            progress_callback(1.0, "章节目录为空，使用默认提示词")
        return default_prompt

    chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number)

    if progress_callback:
        progress_callback(0.2, "获取章节信息")

    chapter_title = chapter_info.get("chapter_title", f"第{novel_number}章")
    chapter_role = chapter_info.get("chapter_role", "未设定")
    chapter_purpose = chapter_info.get("chapter_purpose", "未设定")
    suspense_level = chapter_info.get("suspense_level", "未设定")
    foreshadowing = chapter_info.get("foreshadowing", "未设定")
    plot_twist_level = chapter_info.get("plot_twist_level", "★☆☆☆☆")
    surface_cultivation = chapter_info.get("surface_cultivation", "未设定")
    actual_cultivation = chapter_info.get("actual_cultivation", "未设定")
    scene_location = chapter_info.get("scene_location", "未设定")
    chapter_summary = chapter_info.get("chapter_summary", "未设定")

    # 获取下一章节信息
    next_chapter_number = novel_number + 1
    next_chapter_info = get_chapter_info_from_blueprint(blueprint_text, next_chapter_number)
    next_chapter_title = next_chapter_info.get("chapter_title", "（未命名）")
    next_chapter_role = next_chapter_info.get("chapter_role", "过渡章节")
    next_chapter_purpose = next_chapter_info.get("chapter_purpose", "承上启下")
    next_chapter_suspense = next_chapter_info.get("suspense_level", "中等")
    next_chapter_foreshadow = next_chapter_info.get("foreshadowing", "无特殊伏笔")
    next_chapter_twist = next_chapter_info.get("plot_twist_level", "★☆☆☆☆")
    next_surface_cultivation = next_chapter_info.get("surface_cultivation", "未设定")
    next_actual_cultivation = next_chapter_info.get("actual_cultivation", "未设定")
    next_scene_location = next_chapter_info.get("scene_location", "未设定")
    next_chapter_summary = next_chapter_info.get("chapter_summary", "衔接过渡内容")

    # 创建章节目录
    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 第一章特殊处理
    if novel_number == 1:
        first_prompt = first_chapter_draft_prompt.format(
            novel_number=novel_number,
            word_number=word_number,
            chapter_title=chapter_title,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            suspense_level=suspense_level,
            foreshadowing=foreshadowing,
            plot_arcs=plot_arcs_text if plot_arcs_text else "（无剧情要点）",
            plot_twist_level=plot_twist_level,
            surface_cultivation=surface_cultivation,
            actual_cultivation=actual_cultivation,
            chapter_summary=chapter_summary,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            user_guidance=user_guidance,
            novel_setting=novel_architecture_text
        )
        # 调用回调函数显示提示词内容
        if prompt_callback:
            prompt_callback(f"\n[完整提示词]\n{first_prompt}")
        if progress_callback:
            progress_callback(1.0, "提示词构建完成")
        return first_prompt

    # 获取前文内容和摘要
    if progress_callback:
        progress_callback(0.3, "准备生成章节摘要")

    recent_texts = get_last_n_chapters_text(chapters_dir, novel_number, n=3)
    
    try:
        if progress_callback:
            progress_callback(0.4, "正在生成章节摘要")

        logging.info("Attempting to generate summary")
        short_summary = summarize_recent_chapters(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            chapters_text_list=recent_texts,
            novel_number=novel_number,
            chapter_info=chapter_info,
            next_chapter_info=next_chapter_info,
            timeout=timeout
        )
        logging.info("Summary generated successfully")

        if prompt_callback:
            prompt_callback(f"\n[章节摘要]\n{short_summary}")

        # 添加延时，让用户能看到进度变化
        time.sleep(1)
    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        short_summary = "（摘要生成失败）"

    # 获取前一章结尾
    previous_excerpt = ""
    for text in reversed(recent_texts):
        if text.strip():
            previous_excerpt = text[-800:] if len(text) > 800 else text
            break

    # 知识库检索和处理
    if progress_callback:
        progress_callback(0.5, "生成知识库检索提示词")

    try:
        # 生成检索关键词
        if progress_callback:
            progress_callback(0.6, "检索知识库")
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        search_prompt = knowledge_search_prompt.format(
            chapter_number=novel_number,
            chapter_title=chapter_title,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            plot_type=chapter_purpose,  # Using chapter_purpose as plot_type
            tension_level=suspense_level,  # Using suspense_level as tension_level
            plot_focus=chapter_role,  # Using chapter_role as plot_focus
            foreshadowing_type=foreshadowing,
            main_characters=characters_involved,
            character_states="",  # Not available in current context
            scene_location=scene_location,
            scene_features="",  # Not available in current context
            time_setting=time_constraint,
            atmosphere="",  # Not available in current context
            key_items=key_items,
            related_technology="",  # Not available in current context
            previous_summary="",  # Not available in current context
            current_summary=short_summary,
            future_expectations="",  # Not available in current context
            user_guidance=user_guidance
        )
        
        search_response = invoke_with_cleaning(llm_adapter, search_prompt)
        keyword_groups = parse_search_keywords(search_response)

        # 执行向量检索
        all_contexts = []
        from embedding_adapters import create_embedding_adapter
        embedding_adapter = create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        )
        
        store = load_vector_store(embedding_adapter, filepath)
        if store:
            collection_size = store._collection.count()
            actual_k = min(embedding_retrieval_k, max(1, collection_size))
            
            for group in keyword_groups:
                context = get_relevant_context_from_vector_store(
                    embedding_adapter=embedding_adapter,
                    query=group,
                    filepath=filepath,
                    k=actual_k
                )
                if context:
                    if any(kw in group.lower() for kw in ["技法", "手法", "模板"]):
                        all_contexts.append(f"[TECHNIQUE] {context}")
                    elif any(kw in group.lower() for kw in ["设定", "技术", "世界观"]):
                        all_contexts.append(f"[SETTING] {context}")
                    else:
                        all_contexts.append(f"[GENERAL] {context}")

        # 应用内容规则
        processed_contexts = apply_content_rules(all_contexts, novel_number)
        
        # 执行知识过滤
        chapter_info_for_filter = {
            "chapter_number": novel_number,
            "chapter_title": chapter_title,
            "chapter_role": chapter_role,
            "chapter_purpose": chapter_purpose,
            "characters_involved": characters_involved,
            "key_items": key_items,
            "scene_location": scene_location,
            "foreshadowing": foreshadowing,  # 修复拼写错误
            "suspense_level": suspense_level,
            "plot_twist_level": plot_twist_level,
            "surface_cultivation": surface_cultivation,
            "actual_cultivation": actual_cultivation,
            "chapter_summary": chapter_summary,
            "time_constraint": time_constraint
        }
        
        filtered_context = get_filtered_knowledge_context(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            interface_format=interface_format,
            embedding_adapter=embedding_adapter,
            filepath=filepath,
            chapter_info=chapter_info_for_filter,
            retrieved_texts=processed_contexts,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
    except Exception as e:
        logging.error(f"知识处理流程异常：{str(e)}")
        filtered_context = "（知识库处理失败）"

    if prompt_callback:
        prompt_callback(f"\n[知识库内容]\n{filtered_context}")

    # 添加延时，让用户能看到进度变化
    time.sleep(1)

    # 返回最终提示词
    if progress_callback:
        progress_callback(0.85, "构建完整提示词")

    # 添加延时，让用户能看到进度变化
    time.sleep(1)

    final_prompt = next_chapter_draft_prompt.format(
        user_guidance=user_guidance if user_guidance else "无特殊指导",
        global_summary=global_summary_text,
        previous_chapter_excerpt=previous_excerpt,
        character_state=character_state_text,
        short_summary=short_summary,
        plot_arcs=plot_arcs_text if plot_arcs_text else "（无剧情要点）",
        novel_number=novel_number,
        chapter_title=chapter_title,
        chapter_role=chapter_role,
        chapter_purpose=chapter_purpose,
        suspense_level=suspense_level,
        foreshadowing=foreshadowing,
        plot_twist_level=plot_twist_level,
        surface_cultivation=surface_cultivation,
        actual_cultivation=actual_cultivation,
        chapter_summary=chapter_summary,
        word_number=word_number,
        characters_involved=characters_involved,
        key_items=key_items,
        scene_location=scene_location,
        time_constraint=time_constraint,
        next_chapter_number=next_chapter_number,
        next_chapter_title=next_chapter_title,
        next_chapter_role=next_chapter_role,
        next_chapter_purpose=next_chapter_purpose,
        next_chapter_suspense_level=next_chapter_suspense,
        next_chapter_foreshadowing=next_chapter_foreshadow,
        next_chapter_plot_twist_level=next_chapter_twist,
        next_surface_cultivation=next_surface_cultivation,
        next_actual_cultivation=next_actual_cultivation,
        next_scene_location=next_scene_location,
        next_chapter_summary=next_chapter_summary,
        filtered_context=filtered_context
    )

    if prompt_callback:
        prompt_callback(f"\n[完整提示词]\n{final_prompt}")

    if progress_callback:
        progress_callback(1.0, "提示词构建完成")

    # 添加延时，让用户能看到最终状态
    time.sleep(1)

    return final_prompt

def generate_chapter_draft(
    api_key: str,
    base_url: str,
    model_name: str, 
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    custom_prompt_text: str = None,
    log_func=None
) -> str:
    """
    生成章节草稿，支持自定义提示词
    
    参数:
        log_func: 可选的日志函数，用于将日志输出到UI。如果为None，则使用logging模块。
    """
    def log(message):
        if log_func:
            log_func(message)
        else:
            logging.info(message)

    log("=" * 60)
    log(f"📖 开始生成第{novel_number}章草稿...")
    log(f"📂 小说路径: {filepath}")
    log(f"📄 目标字数: {word_number}字")
    log("=" * 60)

    # 步骤1: 准备提示词
    log("📋 步骤1/3: 准备提示词")

    if custom_prompt_text is None:
        prompt_text = build_chapter_prompt(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            filepath=filepath,
            novel_number=novel_number,
            word_number=word_number,
            temperature=temperature,
            user_guidance=user_guidance,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_retrieval_k,
            interface_format=interface_format,
            max_tokens=max_tokens,
            timeout=timeout
        )
    else:
        prompt_text = custom_prompt_text
    log(f"✓ 提示词准备完成（共{len(prompt_text)}字）")

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 步骤2: 创建LLM适配器
    log("📋 步骤2/3: 创建LLM适配器")
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    log("✓ LLM适配器创建成功")

    # 步骤3: 生成章节内容
    log("📋 步骤3/3: 生成章节内容")
    log("📝 正在调用LLM生成章节内容...")
    chapter_content = invoke_with_cleaning(llm_adapter, prompt_text)
    if not chapter_content.strip():
        log("⚠️ 章节内容为空，生成失败")
        return chapter_content
    log("✓ 章节内容生成成功")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    log("💾 正在保存章节内容...")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    log("✓ 章节内容保存成功")
    logging.info(f"[Draft] Chapter {novel_number} generated as a draft.")

    log(f"✅ 第{novel_number}章草稿生成完成")

def generate_chapter_draft_stream(
    api_key: str,
    base_url: str,
    model_name: str,
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    custom_prompt_text: str = None,
    stream_callback: callable = None,
    log_func=None
) -> str:
    """
    生成章节草稿，支持流式输出
    
    参数:
        stream_callback: 流式输出回调函数，接收每个token
    
    返回:
        完整的章节内容
    """
    def log(message):
        if log_func:
            log_func(message)
        else:
            logging.info(message)
    
    log("=" * 60)
    log(f"📖 开始生成第{novel_number}章草稿...")
    log(f"📂 小说路径: {filepath}")
    log(f"📄 目标字数: {word_number}字")
    log("=" * 60)
    
    # 步骤1: 准备提示词
    log("📋 步骤1/4: 准备提示词")
    if custom_prompt_text is None:
        prompt_text = build_chapter_prompt(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            filepath=filepath,
            novel_number=novel_number,
            word_number=word_number,
            temperature=temperature,
            user_guidance=user_guidance,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_retrieval_k,
            interface_format=interface_format,
            max_tokens=max_tokens,
            timeout=timeout
        )
    else:
        prompt_text = custom_prompt_text
    log(f"✓ 提示词准备完成（共{len(prompt_text)}字）")

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 步骤2: 创建LLM适配器
    log("📋 步骤2/4: 创建LLM适配器")
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    log("✓ LLM适配器创建成功")

    # 步骤3: 生成章节内容
    log("📋 步骤3/4: 生成章节内容")
    log("📝 正在生成章节内容（流式输出）...")
    # 使用流式输出
    from novel_generator.stream_utils import invoke_with_cleaning_stream
    chapter_content = invoke_with_cleaning_stream(llm_adapter, prompt_text, stream_callback)
    
    if not chapter_content.strip():
        log("⚠️ 章节内容为空，生成失败")
        return chapter_content
    log("✓ 章节内容生成成功")

    # 步骤4: 保存章节内容
    log("📋 步骤4/4: 保存章节内容")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    log("💾 正在保存章节内容...")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    log("✓ 章节内容保存成功")
    logging.info(f"[Draft] Chapter {novel_number} generated as a draft.")
    
    log(f"✅ 第{novel_number}章草稿生成完成")

    
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    logging.info(f"[Draft] Chapter {novel_number} generated as a draft.")
    
    return chapter_content
