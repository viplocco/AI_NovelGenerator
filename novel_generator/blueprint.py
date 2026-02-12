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
from prompt_definitions import chapter_blueprint_prompt, chunked_chapter_blueprint_prompt
from utils import read_file, clear_file_content, save_string_to_txt

def compute_chunk_size(number_of_chapters: int, max_tokens: int) -> int:
    """
    基于“每章约100 tokens”的粗略估算，
    再结合当前max_tokens，计算分块大小：
      chunk_size = (floor(max_tokens/100/10)*10) - 10
    并确保 chunk_size 不会小于1或大于实际章节数。
    """
    tokens_per_chapter = 100.0
    ratio = max_tokens / tokens_per_chapter
    ratio_rounded_to_10 = int(ratio // 10) * 10
    chunk_size = ratio_rounded_to_10 - 10
    if chunk_size < 1:
        chunk_size = 1
    if chunk_size > number_of_chapters:
        chunk_size = number_of_chapters
    return chunk_size

def parse_blueprint_blocks(blueprint_text: str):
    """
    解析目录中的单元和章节块
    
    返回: (units, chapters)
    - units: 单元块列表，每个元素是单元文本
    - chapters: 章节块列表，每个元素是章节文本
    """
    # 匹配单元和章节
    pattern = r"(第\s*\d+\s*(?:单元|章).*?)(?=第\s*\d+\s*(?:单元|章)|$)"
    blocks = re.findall(pattern, blueprint_text, flags=re.DOTALL)
    
    units = []
    chapters = []
    for block in blocks:
        if "单元" in block:
            units.append(block.strip())
        else:
            chapters.append(block.strip())
    
    return units, chapters

def get_unit_for_chapter(units, chapter_num):
    """
    根据章节号查找所属单元
    单元格式：第X单元 - 标题（包含章节数：N章）
    假设单元按顺序排列，且章节连续
    """
    if not units:
        return None
    
    current_chapter = 1
    for unit_text in units:
        # 提取单元信息
        match = re.search(r"第\s*(\d+)\s*单元.*?（包含章节数\s*[:：]\s*(\d+)\s*章）", unit_text)
        if match:
            unit_num = int(match.group(1))
            chapter_count = int(match.group(2))
            end_chapter = current_chapter + chapter_count - 1
            if current_chapter <= chapter_num <= end_chapter:
                return unit_text
            current_chapter = end_chapter + 1
        else:
            # 如果没有匹配到包含章节数，尝试其他格式
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
    # 匹配单元和章节
    pattern = r"(第\s*\d+\s*(?:单元|章).*?)(?=第\s*\d+\s*(?:单元|章)|$)"
    blocks = re.findall(pattern, blueprint_text, flags=re.DOTALL)
    if not blocks:
        return blueprint_text
    
    # 分离单元和章节
    units = []
    chapters = []
    for block in blocks:
        if "单元" in block:
            units.append(block)
        else:
            chapters.append(block)
    
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
    若 Novel_directory.txt 已存在且内容非空，则表示可能是之前的部分生成结果；
      解析其中已有的章节数，从下一个章节继续分块生成；
      对于已有章节目录，传入时仅保留最近100章目录，避免prompt过长。
    否则：
      - 若章节数 <= chunk_size，直接一次性生成
      - 若章节数 > chunk_size，进行分块生成
    生成完成后输出至 Novel_directory.txt。
    """
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
    
    # 计算每个单元对应的起始章节号
    unit_start_chapters = []
    current_chapter = 1
    for unit_text in units:
        match = re.search(r"第\s*(\d+)\s*单元.*?（包含章节数\s*[:：]\s*(\d+)\s*章）", unit_text)
        if match:
            chapter_count = int(match.group(2))
            unit_start_chapters.append((current_chapter, unit_text))
            current_chapter += chapter_count
        else:
            # 如果无法解析章节数，尝试从单元编号推断
            unit_match = re.search(r"第\s*(\d+)\s*单元", unit_text)
            if unit_match:
                unit_start_chapters.append((current_chapter, unit_text))
                current_chapter += 5  # 默认假设5章
            else:
                unit_start_chapters.append((current_chapter, unit_text))
                current_chapter += 5
    
    # 提取每个章节的章节号
    chapter_with_nums = []
    for chapter_text in chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            chapter_with_nums.append((chapter_num, chapter_text))
        else:
            chapter_with_nums.append((0, chapter_text))
    
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
            result.append(chapter_with_nums[chapter_idx][1])
            chapter_idx += 1
    
    return result

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
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600
) -> None:
    """
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
    """
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
        
        # 暂时将所有单元都保留，让AI在生成时重新生成需要的单元
        # 更复杂的逻辑需要解析单元包含的章节数
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
            generation_requirements=generation_requirements if generation_requirements else "无特殊要求"
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
        
        # 追加新生成的章节
        if final_blueprint:
            final_blueprint += "\n\n" + cleaned_result
        else:
            final_blueprint = cleaned_result
        
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
