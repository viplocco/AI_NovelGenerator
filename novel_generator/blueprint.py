#novel_generator/blueprint.py
# -*- coding: utf-8 -*-
"""
章节蓝图生成（Chapter_blueprint_generate 及辅助函数）
"""
import os
import re
import logging
from novel_generator.common import invoke_with_cleaning
from llm_adapters import create_llm_adapter
from prompt_definitions import chapter_blueprint_prompt, chunked_chapter_blueprint_prompt, unit_generation_prompt
from utils import read_file, clear_file_content, save_string_to_txt


# 修为等级映射表 - 将字符串等级转换为数值以便比较
# 数值越大表示修为越高
CULTIVATION_LEVELS = {
    # 炼气期 (1-9层 + 大圆满)
    "炼气一层": 101, "炼气二层": 102, "炼气三层": 103, "炼气四层": 104,
    "炼气五层": 105, "炼气六层": 106, "炼气七层": 107, "炼气八层": 108, "炼气九层": 109,
    "炼气期一层": 101, "炼气期二层": 102, "炼气期三层": 103, "炼气期四层": 104,
    "炼气期五层": 105, "炼气期六层": 106, "炼气期七层": 107, "炼气期八层": 108, "炼气期九层": 109,
    "练气一层": 101, "练气二层": 102, "练气三层": 103, "练气四层": 104,
    "练气五层": 105, "练气六层": 106, "练气七层": 107, "练气八层": 108, "练气九层": 109,
    "练气期一层": 101, "练气期二层": 102, "练气期三层": 103, "练气期四层": 104,
    "练气期五层": 105, "练气期六层": 106, "练气期七层": 107, "练气期八层": 108, "练气期九层": 109,
    "炼气大圆满": 110, "练气大圆满": 110, "炼气期大圆满": 110, "练气期大圆满": 110,
    
    # 筑基期 (初期/中期/后期 + 大圆满)
    "筑基初期": 111, "筑基中期": 115, "筑基后期": 119,
    "筑基期初期": 111, "筑基期中期": 115, "筑基期后期": 119,
    "筑基大圆满": 120, "筑基期大圆满": 120,
    
    # 金丹期 (初期/中期/后期 + 大圆满)
    "金丹初期": 121, "金丹中期": 125, "金丹后期": 129,
    "金丹期初期": 121, "金丹期中期": 125, "金丹期后期": 129,
    "金丹大圆满": 130, "金丹期大圆满": 130,
    
    # 元婴期 (初期/中期/后期 + 大圆满)
    "元婴初期": 131, "元婴中期": 135, "元婴后期": 139,
    "元婴期初期": 131, "元婴期中期": 135, "元婴期后期": 139,
    "元婴大圆满": 140, "元婴期大圆满": 140,
    
    # 化神期 (初期/中期/后期 + 大圆满)
    "化神初期": 141, "化神中期": 145, "化神后期": 149,
    "化神期初期": 141, "化神期中期": 145, "化神期后期": 149,
    "化神大圆满": 150, "化神期大圆满": 150,
    
    # 合体期 (初期/中期/后期 + 大圆满)
    "合体初期": 151, "合体中期": 155, "合体后期": 159,
    "合体期初期": 151, "合体期中期": 155, "合体期后期": 159,
    "合体大圆满": 160, "合体期大圆满": 160,
    
    # 大乘期 (初期/中期/后期 + 大圆满)
    "大乘初期": 161, "大乘中期": 165, "大乘后期": 169,
    "大乘期初期": 161, "大乘期中期": 165, "大乘期后期": 169,
    "大乘大圆满": 170, "大乘期大圆满": 170,
    
    # 渡劫期 (初期/中期/后期 + 大圆满)
    "渡劫初期": 171, "渡劫中期": 175, "渡劫后期": 179,
    "渡劫期初期": 171, "渡劫期中期": 175, "渡劫期后期": 179,
    "渡劫大圆满": 180, "渡劫期大圆满": 180,
    
    # 仙人境界 (80+)
    "仙人": 181, "真仙": 181, "金仙": 190, "大罗金仙": 200,
}


def get_cultivation_value(level_str: str) -> int:
    """
    将修为等级字符串转换为数值
    
    参数:
        level_str: 修为等级字符串，如"炼气一层"
    
    返回:
        int: 修为等级数值，未知等级返回0
    """
    if not level_str:
        return 0
    
    # 清理字符串
    level_str = level_str.strip()
    
    # 直接查找
    if level_str in CULTIVATION_LEVELS:
        return CULTIVATION_LEVELS[level_str]
    
    # 尝试模糊匹配（处理一些常见的变体）
    for key, value in CULTIVATION_LEVELS.items():
        if key in level_str or level_str in key:
            return value
    
    # 尝试解析数字层
    match = re.search(r'(\d+)层', level_str)
    if match:
        layer = int(match.group(1))
        # 假设是炼气期
        return 100 + layer
    
    # 未知等级，记录警告
    logging.warning(f"未知的修为等级: {level_str}")
    return 0


def compare_cultivation_levels(level1: str, level2: str) -> int:
    """
    比较两个修为等级
    
    参数:
        level1: 第一个修为等级
        level2: 第二个修为等级
    
    返回:
        int: -1表示level1<level2, 0表示相等, 1表示level1>level2
    """
    v1 = get_cultivation_value(level1)
    v2 = get_cultivation_value(level2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def validate_and_fix_cultivation_progression(unit_text: str, chapter_text: str) -> str:
    """
    验证并修正章节修为是否与单元修为范围一致

    参数:
        unit_text: 单元信息文本
        chapter_text: 章节信息文本

    返回:
        str: 修正后的章节文本（如果需要修正）
    """
    # 提取单元修为范围，支持多种格式：
    # 格式1: 修为等级范围：[炼气一层 → 炼气二层]
    # 格式2: 修为等级范围：[炼气一层至炼气二层]
    # 格式3: 修为等级范围：[炼气一层]（无变化）
    unit_match = re.search(r'修为等级范围[：:]\s*\[([^→\]]+)(?:\s*[→至]\s*([^\]]+))?\]', unit_text)
    if not unit_match:
        return chapter_text

    unit_start = unit_match.group(1).strip()
    unit_end = unit_match.group(2).strip() if unit_match.group(2) else unit_start

    # 提取章节实际实力
    chapter_match = re.search(r'实际实力\[([^\]]+)\]', chapter_text)
    if not chapter_match:
        return chapter_text

    chapter_actual = chapter_match.group(1)

    # 使用数值比较修为等级
    cmp_start = compare_cultivation_levels(chapter_actual, unit_start)
    cmp_end = compare_cultivation_levels(chapter_actual, unit_end)

    # 如果章节实际实力低于单元起始修为，修正为起始修为
    if cmp_start < 0:
        logging.warning(f"章节实际实力[{chapter_actual}]低于单元起始修为[{unit_start}]，已修正")
        return chapter_text.replace(
            f'实际实力[{chapter_actual}]',
            f'实际实力[{unit_start}]'
        )
    # 如果章节实际实力高于单元结束修为，修正为结束修为
    elif cmp_end > 0:
        logging.warning(f"章节实际实力[{chapter_actual}]高于单元结束修为[{unit_end}]，已修正")
        return chapter_text.replace(
            f'实际实力[{chapter_actual}]',
            f'实际实力[{unit_end}]'
        )

    return chapter_text


def compute_chunk_size(number_of_chapters: int, max_tokens: int) -> int:
    """
    优化的分块大小计算，考虑单元信息和格式开销。

    计算逻辑：
    1. 假设每章约80-120 tokens（平均100 tokens）
    2. 假设每单元约200-300 tokens（用于约束章节生成）
    3. 预留20% buffer空间避免token超限
    4. 使用取整算法得到合理的chunk_size

    参数:
        number_of_chapters: 总章节数
        max_tokens: LLM的最大token限制

    返回:
        int: 合理的分块大小（章节数）
    """
    # 基础参数
    tokens_per_chapter = 100.0
    tokens_per_unit = 250.0  # 单元信息的平均token消耗
    format_overhead = 30.0   # 格式化符号的开销

    # 考虑到单元信息会占用一定token，减少每次生成的章节数
    effective_tokens_per_chapter = tokens_per_chapter + (tokens_per_unit / 3)  # 假设每3章一个单元

    # 计算可用token
    available_tokens = max_tokens * 0.8  # 保留20% buffer

    # 计算章节数
    calculated_size = int(available_tokens / effective_tokens_per_chapter)

    # 向下取整到最接近的10的倍数
    rounded_size = int(calculated_size // 10) * 10

    # 应用padding
    chunk_size = max(1, rounded_size - 5)  # 减去5作为安全边距

    # 确保不超过实际章节数
    if chunk_size > number_of_chapters:
        chunk_size = number_of_chapters

    logging.info(f"compute_chunk_size: max_tokens={max_tokens}, calculated_size={calculated_size}, rounded_size={rounded_size}, chunk_size={chunk_size}")

    return chunk_size

def parse_blueprint_blocks(blueprint_text: str):
    """
    解析目录中的单元和章节块

    返回: (units, chapters)
    - units: 单元块列表，每个元素是单元文本
    - chapters: 章节块列表，每个元素是章节文本
    """
    if not blueprint_text or not blueprint_text.strip():
        return [], []

    units = []
    chapters = []

    # 使用多阶段解析策略
    lines = blueprint_text.strip().split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测单元标题 - 使用更宽松的匹配
        unit_match = re.match(r'^第\s*\d+\s*单元', line)
        if unit_match:
            # 开始收集单元内容
            unit_content = [lines[i]]  # 包含当前行
            j = i + 1  # 从下一行开始收集
            # 收集单元内容，直到遇到下一个单元或章节
            while j < len(lines):
                next_line = lines[j].strip()

                # 如果遇到章节标题，停止收集
                chapter_match = re.match(r'^第\s*\d+\s*章', next_line)
                if chapter_match:
                    break

                # 如果遇到下一个单元，停止收集
                next_unit_match = re.match(r'^第\s*\d+\s*单元', next_line)
                if next_unit_match:
                    break

                # 收集行内容
                unit_content.append(lines[j])

                j += 1

            # 添加单元内容（保留空行）
            unit_text = '\n'.join(unit_content)
            if unit_text.strip():
                units.append(unit_text.strip())
                logging.debug(f"解析到单元：{unit_text[:100]}...")
            i = j
            continue

        # 检测章节标题 - 使用更宽松的匹配
        chapter_match = re.match(r'^第\s*\d+\s*章', line)
        if chapter_match:
            # 开始收集章节内容
            chapter_content = [lines[i]]  # 包含当前行
            j = i + 1  # 从下一行开始收集
            # 收集章节内容，直到遇到下一个单元或章节
            while j < len(lines):
                next_line = lines[j].strip()

                # 如果遇到下一个单元，停止收集
                next_unit_match = re.match(r'^第\s*\d+\s*单元', next_line)
                if next_unit_match:
                    break

                # 如果遇到下一个章节，停止收集（但不包含下一章节的标题行）
                next_chapter_match = re.match(r'^第\s*\d+\s*章', next_line)
                if next_chapter_match:
                    break

                # 收集行内容
                chapter_content.append(lines[j])

                j += 1

            # 添加章节内容
            chapter_text = '\n'.join(chapter_content)
            if chapter_text.strip():
                chapters.append(chapter_text.strip())
                logging.debug(f"解析到章节：{chapter_text[:100]}...")
            i = j
            continue

        i += 1

    logging.info(f"parse_blueprint_blocks: {len(units)}个单元，{len(chapters)}个章节")
    return units, chapters


def validate_chapter_continuity(chapters: list, start: int, end: int) -> tuple:
    """
    校验章节编号是否连续
    
    参数:
        chapters: 章节文本列表
        start: 期望的起始章节号
        end: 期望的结束章节号
    
    返回:
        tuple: (is_valid, missing_chapters, duplicate_chapters)
        - is_valid: 是否连续
        - missing_chapters: 缺失的章节号列表
        - duplicate_chapters: 重复的章节号列表
    """
    if not chapters:
        return False, list(range(start, end + 1)), []
    
    # 提取所有章节号
    chapter_numbers = []
    for chapter_text in chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_numbers.append(int(match.group(1)))
    
    # 检查期望范围内的章节
    expected = set(range(start, end + 1))
    actual = set(chapter_numbers)
    
    # 找出缺失的章节
    missing = sorted(expected - actual)
    
    # 找出重复的章节
    seen = set()
    duplicate = []
    for num in chapter_numbers:
        if num in seen:
            duplicate.append(num)
        seen.add(num)
    
    is_valid = len(missing) == 0 and len(duplicate) == 0
    
    if missing:
        logging.warning(f"章节连续性校验：缺失章节 {missing}")
    if duplicate:
        logging.warning(f"章节连续性校验：重复章节 {duplicate}")
    
    return is_valid, missing, duplicate


def extract_foreshadowing_operations(chapter_text: str) -> dict:
    """
    从章节文本中提取伏笔操作
    
    参数:
        chapter_text: 章节文本
    
    返回:
        dict: {
            "chapter_num": 章节号,
            "bury": [埋设的伏笔列表],
            "reinforce": [强化的伏笔列表],
            "resolve": [回收的伏笔列表]
        }
    """
    result = {
        "chapter_num": 0,
        "bury": [],
        "reinforce": [],
        "resolve": []
    }
    
    # 提取章节号
    chapter_match = re.search(r"第\s*(\d+)\s*章", chapter_text)
    if chapter_match:
        result["chapter_num"] = int(chapter_match.group(1))
    
    # 提取伏笔设计
    foreshadow_match = re.search(r'伏笔(?:操作|设计)[：:=]\s*(.+?)(?:\n|$)', chapter_text)
    if not foreshadow_match:
        # 尝试另一种格式
        foreshadow_match = re.search(r'├──\s*伏笔(?:操作|设计)[：:=]\s*(.+?)(?:\n|$)', chapter_text)
    
    if foreshadow_match:
        foreshadow_text = foreshadow_match.group(1).strip()
        
        # 解析伏笔操作：格式如 "埋设(A线索)→强化(B矛盾)→回收(C悬念)"
        # 匹配埋设操作
        bury_matches = re.findall(r'埋设\(([^)]+)\)', foreshadow_text)
        result["bury"] = [m.strip() for m in bury_matches]
        
        # 匹配强化操作
        reinforce_matches = re.findall(r'强化\(([^)]+)\)', foreshadow_text)
        result["reinforce"] = [m.strip() for m in reinforce_matches]
        
        # 匹配回收操作
        resolve_matches = re.findall(r'回收\(([^)]+)\)', foreshadow_text)
        result["resolve"] = [m.strip() for m in resolve_matches]
    
    return result


def track_foreshadowing(chapters: list) -> dict:
    """
    追踪所有章节中的伏笔，检查是否有未回收的伏笔
    
    参数:
        chapters: 章节文本列表
    
    返回:
        dict: {
            "buried": {伏笔名称: 章节号} - 已埋设但未回收的伏笔,
            "resolved": {伏笔名称: 章节号} - 已回收的伏笔,
            "unresolved": {伏笔名称: 埋设章节号} - 未回收的伏笔,
            "warnings": [警告信息列表]
        }
    """
    tracking = {
        "buried": {},      # 已埋设的伏笔 {名称: 埋设章节号}
        "resolved": {},    # 已回收的伏笔 {名称: 回收章节号}
        "unresolved": {},  # 未回收的伏笔 {名称: 埋设章节号}
        "warnings": []
    }
    
    for chapter_text in chapters:
        ops = extract_foreshadowing_operations(chapter_text)
        chapter_num = ops["chapter_num"]
        
        # 处理埋设操作
        for item in ops["bury"]:
            if item in tracking["buried"]:
                tracking["warnings"].append(
                    f"第{chapter_num}章重复埋设伏笔「{item}」（之前在第{tracking['buried'][item]}章已埋设）"
                )
            else:
                tracking["buried"][item] = chapter_num
        
        # 处理强化操作
        for item in ops["reinforce"]:
            if item not in tracking["buried"]:
                tracking["warnings"].append(
                    f"第{chapter_num}章强化了未埋设的伏笔「{item}」"
                )
        
        # 处理回收操作
        for item in ops["resolve"]:
            if item in tracking["buried"]:
                tracking["resolved"][item] = chapter_num
                # 从已埋设列表中移除（已回收）
                del tracking["buried"][item]
            else:
                tracking["warnings"].append(
                    f"第{chapter_num}章回收了未埋设的伏笔「{item}」"
                )
    
    # 剩余未回收的伏笔
    tracking["unresolved"] = dict(tracking["buried"])
    
    if tracking["unresolved"]:
        tracking["warnings"].append(
            f"发现{len(tracking['unresolved'])}个未回收的伏笔：{list(tracking['unresolved'].keys())}"
        )
    
    return tracking


def extract_spatial_coordinates(chapter_text: str) -> str:
    """
    从章节文本中提取空间坐标
    
    参数:
        chapter_text: 章节文本
    
    返回:
        str: 空间坐标字符串
    """
    # 尝试多种格式匹配
    patterns = [
        r'空间坐标[：:=]\s*(.+?)(?:\n|$)',
        r'├──\s*空间坐标[：:=]\s*(.+?)(?:\n|$)',
        r'\*\*空间坐标\*\*[：:=]\s*(.+?)(?:\n|$)',
        r'场景地点[：:=]\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, chapter_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return ""


def extract_unit_spatial_range(unit_text: str) -> list:
    """
    从单元文本中提取空间坐标范围
    
    参数:
        unit_text: 单元文本
    
    返回:
        list: 空间坐标范围列表，如 ["青云宗外门广场", "试炼场地", "青云宗后山"]
    """
    # 尝试匹配空间坐标范围
    match = re.search(r'空间坐标范围[：:=]\s*(.+?)(?:\n|$)', unit_text)
    if match:
        range_text = match.group(1).strip()
        # 分割路径，支持多种分隔符
        locations = re.split(r'\s*[-→→]+\s*', range_text)
        return [loc.strip() for loc in locations if loc.strip()]
    
    return []


def validate_spatial_coordinates(unit_text: str, chapter_text: str) -> tuple:
    """
    校验章节空间坐标是否在单元空间坐标范围内
    
    参数:
        unit_text: 单元文本
        chapter_text: 章节文本
    
    返回:
        tuple: (is_valid, warning_message)
    """
    unit_spatial_range = extract_unit_spatial_range(unit_text)
    chapter_spatial = extract_spatial_coordinates(chapter_text)
    
    if not unit_spatial_range:
        # 单元没有空间坐标范围，跳过校验
        return True, None
    
    if not chapter_spatial:
        # 章节没有空间坐标，警告但不报错
        return True, f"章节未指定空间坐标"
    
    # 检查章节空间坐标是否包含单元范围内的任一地点
    # 这是一个宽松的检查，只要章节空间坐标包含单元范围内的任一关键词即可
    is_valid = False
    for location in unit_spatial_range:
        # 检查章节空间坐标是否包含该地点关键词
        if location in chapter_spatial:
            is_valid = True
            break
    
    if not is_valid:
        return False, f"章节空间坐标「{chapter_spatial}」不在单元范围「{' → '.join(unit_spatial_range)}」内"
    
    return True, None


def get_unit_for_chapter(units, chapter_num):
    """
    根据章节号查找所属单元
    单元格式：第X单元 - 标题（包含章节：n-m章）
    假设单元按顺序排列，且章节连续
    """
    if not units:
        return None
    
    current_chapter = 1
    for unit_text in units:
        # 提取单元信息，支持多种格式
        match = re.search(r"第\s*(\d+)\s*单元.*?(?:包含章节|章节范围)\s*[:：]\s*(\d+)\s*[-~到至]\s*(\d+)", unit_text, re.DOTALL)
        if match:
            unit_num = int(match.group(1))
            start_chapter = int(match.group(2))
            end_chapter = int(match.group(3))
            if start_chapter <= chapter_num <= end_chapter:
                return unit_text
            current_chapter = end_chapter + 1
        else:
            # 如果没有匹配到包含章节范围，尝试其他格式
            # 简单假设每个单元包含3-5章
            end_chapter = current_chapter + 4  # 假设5章
            if current_chapter <= chapter_num <= end_chapter:
                return unit_text
            current_chapter = end_chapter + 1
    
    return None

def limit_chapter_blueprint(blueprint_text: str, limit_chapters: int = 100) -> str:
    """
    从已有章节目录中只取最近的 limit_chapters 章，同时保留所有单元信息。
    """
    if not blueprint_text or not blueprint_text.strip():
        return blueprint_text

    lines = blueprint_text.strip().split('\n')
    units = []
    chapters = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 检测单元标题
        unit_match = re.match(r'^第\s*\d+\s*单元', line)
        if unit_match:
            # 收集单元内容
            unit_content = [lines[i]]  # 包含当前行
            j = i + 1  # 从下一行开始收集
            while j < len(lines):
                next_line = lines[j].strip()

                # 如果遇到章节标题，停止收集
                chapter_match = re.match(r'^第\s*\d+\s*章', next_line)
                if chapter_match:
                    break

                # 如果遇到下一个单元，停止收集
                next_unit_match = re.match(r'^第\s*\d+\s*单元', next_line)
                if next_unit_match:
                    break

                unit_content.append(lines[j])
                j += 1

            unit_text = '\n'.join(unit_content)
            if unit_text.strip():
                units.append(unit_text.strip())
                logging.debug(f"限制章节时解析到单元")
            i = j
            continue

        # 检测章节标题
        chapter_match = re.match(r'^第\s*\d+\s*章', line)
        if chapter_match:
            # 收集章节内容
            chapter_content = [lines[i]]  # 包含当前行
            j = i + 1  # 从下一行开始收集
            while j < len(lines):
                next_line = lines[j].strip()

                # 如果遇到下一个单元，停止收集
                next_unit_match = re.match(r'^第\s*\d+\s*单元', next_line)
                if next_unit_match:
                    break

                # 如果遇到下一个章节，停止收集
                next_chapter_match = re.match(r'^第\s*\d+\s*章', next_line)
                if next_chapter_match:
                    break

                chapter_content.append(lines[j])
                j += 1

            chapter_text = '\n'.join(chapter_content)
            if chapter_text.strip():
                chapters.append(chapter_text.strip())
                logging.debug(f"限制章节时解析到章节")
            i = j
            continue

        i += 1

    # 如果章节数不超过限制，返回原文本
    if len(chapters) <= limit_chapters:
        return blueprint_text

    # 保留所有单元和最近limit_chapters章
    selected_chapters = chapters[-limit_chapters:]

    # 组合结果：先单元后章节
    result_parts = []
    if units:
        result_parts.extend(units)
    result_parts.extend(selected_chapters)

    return "\n\n".join(result_parts).strip()

def Chapter_blueprint_generate(
    interface_format: str,
    api_key: str,
    base_url: str,
    llm_model: str,
    filepath: str,
    number_of_chapters: int,
    user_guidance: str = "",  # 新增参数
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600
) -> None:
    """
    【已弃用】请使用 Chapter_blueprint_generate_range_stream 代替
    
    若 Novel_directory.txt 已存在且内容非空，则表示可能是之前的部分生成结果；
      解析其中已有的章节数，从下一个章节继续分块生成；
      对于已有章节目录，传入时仅保留最近100章目录，避免prompt过长。
    否则：
      - 若章节数 <= chunk_size，直接一次性生成
      - 若章节数 > chunk_size，进行分块生成
    生成完成后输出至 Novel_directory.txt。
    
    弃用原因：此函数不支持流式输出和完整的校验机制
    推荐使用：novel_generator.blueprint_stream.Chapter_blueprint_generate_range_stream
    """
    import warnings
    warnings.warn(
        "Chapter_blueprint_generate 已弃用，请使用 Chapter_blueprint_generate_range_stream 代替",
        DeprecationWarning,
        stacklevel=2
    )
    
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        logging.warning("Novel_architecture.txt not found. Please generate architecture first.")
        return

    architecture_text = read_file(arch_file).strip()
    if not architecture_text:
        logging.warning("Novel_architecture.txt is empty.")
        return

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=llm_model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        open(filename_dir, "w", encoding="utf-8").close()

    existing_blueprint = read_file(filename_dir).strip()
    chunk_size = compute_chunk_size(number_of_chapters, max_tokens)
    logging.info(f"Number of chapters = {number_of_chapters}, computed chunk_size = {chunk_size}.")

    if existing_blueprint:
        logging.info("Detected existing blueprint content. Will resume chunked generation from that point.")
        pattern = r"第\s*(\d+)\s*章"
        existing_chapter_numbers = re.findall(pattern, existing_blueprint)
        existing_chapter_numbers = [int(x) for x in existing_chapter_numbers if x.isdigit()]
        max_existing_chap = max(existing_chapter_numbers) if existing_chapter_numbers else 0
        logging.info(f"Existing blueprint indicates up to chapter {max_existing_chap} has been generated.")
        final_blueprint = existing_blueprint
        current_start = max_existing_chap + 1
        while current_start <= number_of_chapters:
            current_end = min(current_start + chunk_size - 1, number_of_chapters)
            limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
            chunk_prompt = chunked_chapter_blueprint_prompt.format(
                novel_architecture=architecture_text,
                chapter_list=limited_blueprint,
                number_of_chapters=number_of_chapters,
                n=current_start,
                m=current_end,
                user_guidance=user_guidance  # 新增参数
            )
            logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
            chunk_result = invoke_with_cleaning(llm_adapter, chunk_prompt)
            if not chunk_result.strip():
                logging.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
                clear_file_content(filename_dir)
                save_string_to_txt(final_blueprint.strip(), filename_dir)
                return
            final_blueprint += "\n\n" + chunk_result.strip()
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            current_start = current_end + 1

        logging.info("All chapters blueprint have been generated (resumed chunked).")
        return

    if chunk_size >= number_of_chapters:
        prompt = chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            number_of_chapters=number_of_chapters,
            user_guidance=user_guidance  # 新增参数
        )
        blueprint_text = invoke_with_cleaning(llm_adapter, prompt)
        if not blueprint_text.strip():
            logging.warning("Chapter blueprint generation result is empty.")
            return

        clear_file_content(filename_dir)
        save_string_to_txt(blueprint_text, filename_dir)
        logging.info("Novel_directory.txt (chapter blueprint) has been generated successfully (single-shot).")
        return

    logging.info("Will generate chapter blueprint in chunked mode from scratch.")
    final_blueprint = ""
    current_start = 1
    while current_start <= number_of_chapters:
        current_end = min(current_start + chunk_size - 1, number_of_chapters)
        limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
        chunk_prompt = chunked_chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            chapter_list=limited_blueprint,
            number_of_chapters=number_of_chapters,
            n=current_start,
            m=current_end,
            user_guidance=user_guidance  # 新增参数
        )
        logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
        chunk_result = invoke_with_cleaning(llm_adapter, chunk_prompt)
        if not chunk_result.strip():
            logging.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            return
        if final_blueprint.strip():
            final_blueprint += "\n\n" + chunk_result.strip()
        else:
            final_blueprint = chunk_result.strip()
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
        current_start = current_end + 1

    logging.info("Novel_directory.txt (chapter blueprint) has been generated successfully (chunked).")

def check_existing_chapters(filepath: str, start_chapter: int, end_chapter: int) -> list:
    """
    检测指定章节范围内是否已有目录
    
    参数:
        filepath: 小说目录路径
        start_chapter: 起始章节号
        end_chapter: 结束章节号
    
    返回:
        list: 已存在的章节号列表
    """
    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        return []
    
    existing_blueprint = read_file(filename_dir).strip()
    if not existing_blueprint:
        return []
    
    pattern = r"第\s*(\d+)\s*章"
    existing_chapter_numbers = re.findall(pattern, existing_blueprint)
    existing_chapter_numbers = [int(x) for x in existing_chapter_numbers if x.isdigit()]
    
    # 筛选出指定范围内的章节
    duplicate_chapters = [num for num in existing_chapter_numbers if start_chapter <= num <= end_chapter]
    return sorted(duplicate_chapters)

def remove_chapter_ranges(filepath: str, chapter_ranges: list) -> bool:
    """
    删除指定章节范围的目录，同时保留所有单元信息
    
    参数:
        filepath: 小说目录路径
        chapter_ranges: 章节范围列表，如 [(1,5), (10,15)]
    
    返回:
        bool: 是否成功删除
    """
    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        return True
    
    existing_blueprint = read_file(filename_dir).strip()
    if not existing_blueprint:
        return True
    
    # 使用 parse_blueprint_blocks 分离单元和章节
    units, chapters = parse_blueprint_blocks(existing_blueprint)
    
    # 过滤章节：只保留不在删除范围内的章节
    filtered_chapters = []
    for chapter_text in chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            # 检查是否在要删除的范围内
            should_remove = any(start <= chapter_num <= end for start, end in chapter_ranges)
            if not should_remove:
                # 清理章节文本，去除多余的 ## 和空行
                cleaned_text = chapter_text.strip()
                cleaned_text = re.sub(r"^##\s*", "", cleaned_text)
                cleaned_text = re.sub(r"^\n+", "", cleaned_text)
                cleaned_text = re.sub(r"\n##\s*", "\n", cleaned_text)
                filtered_chapters.append(cleaned_text)
    
    # 重新组合：保留所有单元信息 + 过滤后的章节
    # 按正确顺序插入单元（单元在其包含的章节之前）
    result_parts = _interleave_units_and_chapters(units, filtered_chapters)
    
    if result_parts:
        new_blueprint = "\n\n".join(result_parts).strip()
    else:
        new_blueprint = ""
    clear_file_content(filename_dir)
    save_string_to_txt(new_blueprint, filename_dir)
    
    return True


def _interleave_units_and_chapters(units: list, chapters: list) -> list:
    """
    将单元信息和章节按正确顺序交错排列。
    单元应该出现在其包含的第一个章节之前。

    参数:
        units: 单元文本列表
        chapters: 章节文本列表

    返回:
        list: 按正确顺序排列的单元和章节列表
    """
    if not units:
        return chapters
    if not chapters:
        return units

    logging.info(f"_interleave_units_and_chapters: {len(units)}个单元，{len(chapters)}个章节")

    # 计算每个单元对应的起始章节号
    unit_start_chapters = []
    current_chapter = 1
    for unit_text in units:
        # 尝试多种格式匹配单元章节范围
        # 格式1: （包含章节：1-3章）
        match = re.search(r"第\s*(\d+)\s*单元.*?(?:包含章节|章节范围)\s*[:：]\s*(\d+)\s*[-~到至]\s*(\d+)", unit_text, re.DOTALL)
        if not match:
            # 格式2: 包含章节：1-3章（无括号）
            match = re.search(r"第\s*(\d+)\s*单元.*?包含章节\s*[:：]\s*(\d+)\s*[-~到至]\s*(\d+)\s*章", unit_text, re.DOTALL)
        if not match:
            # 格式3: 更宽松的匹配
            match = re.search(r"第\s*(\d+)\s*单元.*?(\d+)\s*[-~到至]\s*(\d+)\s*章", unit_text, re.DOTALL)
        
        if match:
            start_chapter = int(match.group(2))
            end_chapter = int(match.group(3))
            unit_start_chapters.append((start_chapter, unit_text))
            current_chapter = end_chapter + 1
            logging.debug(f"解析单元章节范围：第{start_chapter}-{end_chapter}章")
        else:
            # 如果无法解析章节范围，尝试从单元编号推断
            unit_match = re.search(r"第\s*(\d+)\s*单元", unit_text)
            if unit_match:
                unit_start_chapters.append((current_chapter, unit_text))
                current_chapter += 5  # 默认假设5章
                logging.debug(f"无法解析单元章节范围，使用推断值：第{current_chapter-5}章开始")
            else:
                unit_start_chapters.append((current_chapter, unit_text))
                current_chapter += 5

    logging.debug(f"_interleave_units_and_chapters: 解析到{len(unit_start_chapters)}个单元的起始章节")

    # 提取每个章节的章节号
    chapter_with_nums = []
    for chapter_text in chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            chapter_with_nums.append((chapter_num, chapter_text))
        else:
            chapter_with_nums.append((0, chapter_text))

    logging.debug(f"_interleave_units_and_chapters: 解析到{len(chapter_with_nums)}个章节")

    # 按顺序交错排列
    result = []
    unit_idx = 0
    chapter_idx = 0
    
    while unit_idx < len(unit_start_chapters) or chapter_idx < len(chapter_with_nums):
        # 检查是否需要插入单元
        if unit_idx < len(unit_start_chapters):
            unit_start, unit_text = unit_start_chapters[unit_idx]
            # 如果没有更多章节，或者当前章节号 >= 单元起始章节号，插入单元
            if chapter_idx >= len(chapter_with_nums) or chapter_with_nums[chapter_idx][0] >= unit_start:
                result.append(unit_text)
                unit_idx += 1
                continue
        
        # 插入章节
        if chapter_idx < len(chapter_with_nums):
            chapter_num, chapter_text = chapter_with_nums[chapter_idx]
            result.append(chapter_text)
            chapter_idx += 1
            logging.debug(f"_interleave_units_and_chapters: 插入章节 {chapter_num}")

    logging.info(f"_interleave_units_and_chapters完成: 返回{len(result)}个块")
    return result

def generate_units_for_range(
    llm_adapter,
    architecture_text: str,
    existing_blueprint: str,
    start_chapter: int,
    end_chapter: int,
    number_of_chapters: int,
    user_guidance: str,
    world_building: str
) -> str:
    """
    为指定章节范围生成单元信息（非流式版本）

    参数:
        llm_adapter: LLM适配器
        architecture_text: 小说架构文本
        existing_blueprint: 已有目录文本
        start_chapter: 起始章节号
        end_chapter: 结束章节号
        number_of_chapters: 总章节数
        user_guidance: 用户指导
        world_building: 世界观

    返回:
        str: 生成的单元信息
    """
    # 限制已有目录为最近100章
    limited_blueprint = limit_chapter_blueprint(existing_blueprint, 100)

    # 构建单元生成提示词
    unit_prompt = unit_generation_prompt.format(
        novel_architecture=architecture_text,
        chapter_list=limited_blueprint,
        number_of_chapters=number_of_chapters,
        n=start_chapter,
        m=end_chapter,
        user_guidance=user_guidance,
        world_building=world_building
    )

    logging.info(f"Generating units for chapters [{start_chapter}..{end_chapter}]...")

    # 生成单元信息
    unit_result = invoke_with_cleaning(llm_adapter, unit_prompt)

    if not unit_result or not unit_result.strip():
        error_msg = f"单元 [{start_chapter}..{end_chapter}] 生成失败：返回内容为空"
        logging.error(error_msg)
        raise ValueError(error_msg)

    # 清理生成的单元信息
    cleaned_result = unit_result.strip()
    if cleaned_result.startswith("##"):
        cleaned_result = cleaned_result[2:].lstrip()
    while cleaned_result.startswith("\n"):
        cleaned_result = cleaned_result[1:]

    return cleaned_result

def Chapter_blueprint_generate_range(
    interface_format: str,
    api_key: str,
    base_url: str,
    llm_model: str,
    filepath: str,
    start_chapter: int,
    end_chapter: int,
    number_of_chapters: int,
    user_guidance: str = "",
    generation_requirements: str = "",
    world_building: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600
) -> None:
    """
    【已弃用】请使用 Chapter_blueprint_generate_range_stream 代替
    
    生成指定章节范围的目录
    
    参数:
        interface_format: 接口格式
        api_key: API密钥
        base_url: API基础URL
        llm_model: 模型名称
        filepath: 小说目录路径
        start_chapter: 起始章节号
        end_chapter: 结束章节号
        number_of_chapters: 总章节数
        user_guidance: 用户指导
        generation_requirements: 生成要求
        temperature: 温度参数
        max_tokens: 最大token数
        timeout: 超时时间
    
    弃用原因：此函数不支持流式输出和完整的校验机制
    推荐使用：novel_generator.blueprint_stream.Chapter_blueprint_generate_range_stream
    """
    import warnings
    warnings.warn(
        "Chapter_blueprint_generate_range 已弃用，请使用 Chapter_blueprint_generate_range_stream 代替",
        DeprecationWarning,
        stacklevel=2
    )
    
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        logging.warning("Novel_architecture.txt not found. Please generate architecture first.")
        return

    architecture_text = read_file(arch_file).strip()
    if not architecture_text:
        logging.warning("Novel_architecture.txt is empty.")
        return

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=llm_model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        open(filename_dir, "w", encoding="utf-8").close()

    # 读取已有目录作为上下文
    existing_blueprint = read_file(filename_dir)
    if existing_blueprint:
        existing_blueprint = existing_blueprint.strip()
    else:
        existing_blueprint = ""
    
    # 计算分块大小
    chunk_size = compute_chunk_size(end_chapter - start_chapter + 1, max_tokens)
    logging.info(f"Generating chapters [{start_chapter}..{end_chapter}], computed chunk_size = {chunk_size}.")

    # ========== 第一阶段：生成单元信息 ==========
    logging.info("Phase 1: Generating unit information...")

    # 生成单元信息
    units_result = generate_units_for_range(
        llm_adapter,
        architecture_text,
        existing_blueprint,
        start_chapter,
        end_chapter,
        number_of_chapters,
        user_guidance,
        world_building
    )

    # 解析生成的单元信息
    new_units, _ = parse_blueprint_blocks(units_result)

    # 解析已有目录中的单元和章节
    existing_units, existing_chapters = parse_blueprint_blocks(existing_blueprint)

    # 合并单元信息
    for new_unit in new_units:
        new_unit_match = re.search(r"第\s*(\d+)\s*单元", new_unit)
        if new_unit_match:
            new_unit_num = int(new_unit_match.group(1))
            # 检查是否已存在同编号的单元
            replaced = False
            for i, existing_unit in enumerate(existing_units):
                existing_unit_match = re.search(r"第\s*(\d+)\s*单元", existing_unit)
                if existing_unit_match and int(existing_unit_match.group(1)) == new_unit_num:
                    # 替换已有单元
                    existing_units[i] = new_unit.strip()
                    replaced = True
                    logging.info(f"Replaced existing unit {new_unit_num} with new content.")
                    break
            if not replaced:
                # 新增单元
                existing_units.append(new_unit.strip())
                logging.info(f"Added new unit {new_unit_num}.")

    # ========== 第二阶段：根据单元信息生成章节目录 ==========
    logging.info("Phase 2: Generating chapter directory based on unit information...")

    # 构建单元信息字符串
    unit_info = "\n\n".join(existing_units)

    
    # 解析已有目录中的单元和章节
    existing_units, existing_chapters = parse_blueprint_blocks(existing_blueprint)
    
    # 分离出不在生成范围内的内容
    keep_units = []       # 需要保留的单元（在start_chapter之前）
    regenerate_units = [] # 需要重新生成的单元（与生成范围有重叠）
    keep_before = []      # 起始章节之前的章节
    keep_after = []       # 结束章节之后的章节
    
    # 处理单元
    for unit_text in existing_units:
        # 尝试提取单元包含的章节范围
        # 假设单元按顺序排列，我们通过查找单元后的第一个章节来推断
        # 这是一个简化实现，实际应该使用更精确的解析
        keep_unit = True
        # 检查单元是否完全在生成范围之前
        # 如果单元包含的章节与生成范围有重叠，则需要重新生成
        # 简化：假设如果单元包含任何在生成范围内的章节，就重新生成
        # 实际上我们需要更精确的判断，但这里先这样处理
        for chapter_text in existing_chapters:
            match = re.search(r"第\s*(\d+)\s*章", chapter_text)
            if match:
                chapter_num = int(match.group(1))
                # 如果这个章节属于当前单元（简化：按顺序）
                # 我们假设单元和章节是按顺序排列的
                pass
        
        # 提取单元包含的章节范围
        unit_match = re.search(r"第\s*(\d+)\s*单元.*?（包含章节\s*[:：]\s*(\d+)\s*[-~到]\s*(\d+)\s*章）", unit_text)
        
        if unit_match:
            unit_start = int(unit_match.group(2))
            unit_end = int(unit_match.group(3))
            
            # 判断单元与生成范围的关系
            if unit_end < start_chapter:
                # 单元完全在生成范围之前，保留
                keep_units.append(unit_text)
            elif unit_start > end_chapter:
                # 单元完全在生成范围之后，保留
                keep_units.append(unit_text)
            else:
                # 单元与生成范围有重叠，需要重新生成
                regenerate_units.append(unit_text)
        else:
            # 无法解析单元范围，默认保留
            keep_units.append(unit_text)
    
    # 处理章节
    for chapter_text in existing_chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            if chapter_num < start_chapter:
                keep_before.append(chapter_text)
            elif chapter_num > end_chapter:
                keep_after.append(chapter_text)
            # 在生成范围内的章节将被重新生成，所以不保留
    
    # 准备最终目录内容：保留的单元 + 保留的之前章节
    final_parts = []
    
    # 添加保留的单元
    for unit_text in keep_units:
        # 检查这个单元是否完全在生成范围之前
        # 如果是，保留；否则需要重新生成
        # 简化：暂时都保留
        final_parts.append(unit_text)
    
    # 添加保留的之前章节
    if keep_before:
        final_parts.extend(keep_before)
    
    final_blueprint = "\n\n".join(final_parts)
    if final_blueprint:
        final_blueprint += "\n\n"
    
    # 循环生成指定范围内的章节
    current_start = start_chapter
    while current_start <= end_chapter:
        current_end = min(current_start + chunk_size - 1, end_chapter)
        
        # 获取上下文目录：保留的单元 + 保留的章节（前后）
        context_parts = []
        
        # 添加所有保留的单元（确保单元信息在上下文中）
        for unit_text in keep_units:
            context_parts.append(unit_text)
        
        # 添加上下文章节：之前保留的章节 + 之后保留的章节（最近50个）
        if keep_before:
            context_parts.extend(keep_before[-50:])  # 最多50个
        
        if keep_after:
            context_parts.extend(keep_after[-50:])   # 最多50个
        
        context_blueprint = "\n\n".join(context_parts)
        limited_blueprint = limit_chapter_blueprint(context_blueprint, 100)
        
        # 构建提示词
        chunk_prompt = chunked_chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            chapter_list=limited_blueprint,
            number_of_chapters=number_of_chapters,
            n=current_start,
            m=current_end,
            user_guidance=user_guidance,
            generation_requirements=generation_requirements if generation_requirements else "无特殊要求",
            world_building=world_building
        )
        
        logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
        chunk_result = invoke_with_cleaning(llm_adapter, chunk_prompt)

        if not chunk_result.strip():
            logging.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
            # 保存已有内容
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            return

        # 清理新生成的章节内容
        cleaned_result = chunk_result.strip()
        cleaned_result = re.sub(r"^##\s*", "", cleaned_result)
        cleaned_result = re.sub(r"^\n+", "", cleaned_result)
        cleaned_result = re.sub(r"\n##\s*", "\n", cleaned_result)

        # 解析新生成的单元和章节
        new_units, new_chapters = parse_blueprint_blocks(cleaned_result)

        if new_units:
            logging.info(f"Generated {len(new_units)} unit(s).")
        if new_chapters:
            logging.info(f"Generated {len(new_chapters)} chapter(s).")

        # 对每个新生成的章节进行修为范围校验和修正
        for new_chapter in new_chapters:
            new_chapter = new_chapter.strip()
            # 验证并修正修为范围
            new_chapter = validate_and_fix_cultivation_progression(new_unit, new_chapter)
            # 追加修正后的章节
            if final_blueprint:
                final_blueprint += "\n\n" + new_chapter
            else:
                final_blueprint = new_chapter

        # 保存到文件
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
        
        current_start = current_end + 1
    
    # 追加结束章节之后的章节
    if keep_after:
        final_blueprint += "\n\n" + "\n\n".join(keep_after)
        # 保存到文件
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
    
    logging.info(f"Chapters [{start_chapter}..{end_chapter}] blueprint have been generated successfully.")
