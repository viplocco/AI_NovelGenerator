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

def limit_chapter_blueprint(blueprint_text: str, limit_chapters: int = 100) -> str:
    """
    从已有章节目录中只取最近的 limit_chapters 章，以避免 prompt 超长。
    """
    pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
    chapters = re.findall(pattern, blueprint_text, flags=re.DOTALL)
    if not chapters:
        return blueprint_text
    if len(chapters) <= limit_chapters:
        return blueprint_text
    selected = chapters[-limit_chapters:]
    return "\n\n".join(selected).strip()

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
    删除指定章节范围的目录
    
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
    
    # 使用正则表达式匹配所有章节块
    pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
    chapters = re.findall(pattern, existing_blueprint, flags=re.DOTALL)
    
    # 提取章节号并过滤
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
    
    # 重新组合并保存
    if filtered_chapters:
        new_blueprint = "\n\n".join(filtered_chapters).strip()
    else:
        new_blueprint = ""
    clear_file_content(filename_dir)
    save_string_to_txt(new_blueprint, filename_dir)
    
    return True

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
    
    # 将已有目录分割成章节列表
    existing_chapters = []
    if existing_blueprint:
        pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
        existing_chapters = re.findall(pattern, existing_blueprint, flags=re.DOTALL)
    
    # 分离出不在生成范围内的章节
    before_chapters = []  # 起始章节之前的章节
    after_chapters = []   # 结束章节之后的章节
    
    for chapter_text in existing_chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            if chapter_num < start_chapter:
                before_chapters.append(chapter_text)
            elif chapter_num > end_chapter:
                after_chapters.append(chapter_text)
    
    # 准备最终目录内容
    final_blueprint = "\n\n".join(before_chapters)
    if final_blueprint:
        final_blueprint += "\n\n"
    
    # 循环生成指定范围内的章节
    current_start = start_chapter
    while current_start <= end_chapter:
        current_end = min(current_start + chunk_size - 1, end_chapter)
        
        # 获取上下文目录（限制为最近100章）
        context_blueprint = "\n\n".join(before_chapters + after_chapters[-50:])
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
    if after_chapters:
        final_blueprint += "\n\n" + "\n\n".join(after_chapters)
        # 保存到文件
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
    
    logging.info(f"Chapters [{start_chapter}..{end_chapter}] blueprint have been generated successfully.")
