# novel_generator/blueprint_stream.py
# -*- coding: utf-8 -*-
"""
支持流式输出的章节蓝图生成
"""
import os
import re
import logging
from novel_generator.blueprint import (
    compute_chunk_size, 
    limit_chapter_blueprint, 
    parse_blueprint_blocks,
    _interleave_units_and_chapters
)
from llm_adapters import create_llm_adapter
from prompt_definitions import chunked_chapter_blueprint_prompt
from utils import read_file, clear_file_content, save_string_to_txt


def invoke_with_streaming(llm_adapter, prompt: str, stream_callback: callable = None) -> str:
    """
    调用LLM生成内容，支持流式输出

    参数:
        llm_adapter: LLM适配器
        prompt: 提示词
        stream_callback: 流式输出回调函数

    返回:
        str: 完整的生成结果
    """
    result = ""

    try:
        if hasattr(llm_adapter, 'invoke_stream'):
            result = llm_adapter.invoke_stream(prompt, stream_callback if stream_callback else lambda x: None)
        else:
            result = llm_adapter.invoke(prompt)
            if stream_callback:
                chunk_size = 100
                for i in range(0, len(result), chunk_size):
                    chunk = result[i:i+chunk_size]
                    stream_callback(chunk)
    except Exception as e:
        logging.error(f"Error during streaming: {e}")
        try:
            result = llm_adapter.invoke(prompt)
            if stream_callback:
                chunk_size = 100
                for i in range(0, len(result), chunk_size):
                    chunk = result[i:i+chunk_size]
                    stream_callback(chunk)
        except Exception as e2:
            logging.error(f"Error during fallback invoke: {e2}")
            result = ""

    return result


def Chapter_blueprint_generate_range_stream(
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
    timeout: int = 600,
    stream_callback: callable = None
) -> None:
    """
    生成指定章节范围的目录（支持流式输出）

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
        stream_callback: 流式输出回调函数
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

    # ========== 关键修复：使用 parse_blueprint_blocks 解析已有目录 ==========
    # 分离已有目录中的单元和章节
    existing_units, existing_chapter_blocks = parse_blueprint_blocks(existing_blueprint)
    
    if existing_units:
        logging.info(f"Found {len(existing_units)} existing units to preserve.")
    if existing_chapter_blocks:
        logging.info(f"Found {len(existing_chapter_blocks)} existing chapters.")

    # 分离出不在生成范围内的章节
    before_chapters = []   # 起始章节之前的章节
    after_chapters = []    # 结束章节之后的章节
    in_range_chapters = {} # 生成范围内的已有章节（章节号 -> 章节文本）

    for chapter_text in existing_chapter_blocks:
        # 清理章节内容
        chapter_text = chapter_text.strip()
        while chapter_text.startswith("**"):
            chapter_text = chapter_text[2:].lstrip()
        while chapter_text.endswith("**"):
            chapter_text = chapter_text[:-2].rstrip()

        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            if chapter_num < start_chapter:
                before_chapters.append(chapter_text)
            elif chapter_num > end_chapter:
                after_chapters.append(chapter_text)
            else:
                in_range_chapters[chapter_num] = chapter_text

    # 循环生成指定范围内的章节
    current_start = start_chapter
    current_chunk = 0

    while current_start <= end_chapter:
        current_end = min(current_start + chunk_size - 1, end_chapter)

        # 获取上下文目录（限制为最近100章）
        # 包含：所有单元信息 + 起始章节之前的章节 + 生成范围内的已有章节 + 结束章节之后的章节
        context_parts = []
        
        # 添加所有单元信息作为上下文
        context_parts.extend(existing_units)
        
        # 添加章节上下文
        in_range_chapters_list = [text for num, text in sorted(in_range_chapters.items())]
        after_chapters_sample = after_chapters[-50:] if after_chapters else []
        context_parts.extend(before_chapters)
        context_parts.extend(in_range_chapters_list)
        context_parts.extend(after_chapters_sample)
        
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
            world_building=""
        )

        logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")

        # 生成章节目录（带流式输出）
        chunk_result = invoke_with_streaming(
            llm_adapter, 
            chunk_prompt, 
            stream_callback=stream_callback
        )

        if not chunk_result or not chunk_result.strip():
            error_msg = f"章节 [{current_start}..{current_end}] 生成失败：返回内容为空"
            logging.error(error_msg)
            # 保存已有内容（包含单元信息）
            save_parts = _interleave_units_and_chapters(existing_units, before_chapters + [text for _, text in sorted(in_range_chapters.items())] + after_chapters)
            save_blueprint = "\n\n".join(save_parts).strip()
            clear_file_content(filename_dir)
            save_string_to_txt(save_blueprint, filename_dir)
            if stream_callback:
                stream_callback(f"\n\n❌ {error_msg}")
            raise ValueError(error_msg)

        # 清理新生成的内容
        cleaned_result = chunk_result.strip()
        if cleaned_result.startswith("##"):
            cleaned_result = cleaned_result[2:].lstrip()
        while cleaned_result.startswith("\n"):
            cleaned_result = cleaned_result[1:]

        # ========== 关键修复：使用 parse_blueprint_blocks 解析新生成的内容 ==========
        new_units, new_chapter_blocks = parse_blueprint_blocks(cleaned_result)
        
        if new_units:
            logging.info(f"New generation contains {len(new_units)} unit(s).")
        if new_chapter_blocks:
            logging.info(f"New generation contains {len(new_chapter_blocks)} chapter(s).")

        # 处理新生成的单元信息
        # 将新生成的单元合并到已有单元中（替换或新增）
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

        # 处理新生成的章节
        for new_chapter in new_chapter_blocks:
            new_chapter = new_chapter.strip()
            while new_chapter.startswith("**"):
                new_chapter = new_chapter[2:].lstrip()
            while new_chapter.endswith("**"):
                new_chapter = new_chapter[:-2].rstrip()

            new_match = re.search(r"第\s*(\d+)\s*章", new_chapter)
            if new_match:
                new_chapter_num = int(new_match.group(1))
                if new_chapter_num <= 0:
                    logging.warning(f"无效的章节号：{new_chapter_num}，跳过该章节")
                    continue
                if start_chapter <= new_chapter_num <= end_chapter:
                    if new_chapter_num not in in_range_chapters:
                        in_range_chapters[new_chapter_num] = new_chapter
                    # 如果已存在，保留原有内容（不覆盖）

        # ========== 关键修复：构建 final_blueprint 时包含单元信息 ==========
        # 合并所有章节
        all_chapter_texts = []
        for text in before_chapters:
            match = re.search(r"第\s*(\d+)\s*章", text)
            if match:
                all_chapter_texts.append(text)
        
        for chapter_num, text in sorted(in_range_chapters.items()):
            all_chapter_texts.append(text)
        
        for text in after_chapters:
            match = re.search(r"第\s*(\d+)\s*章", text)
            if match:
                all_chapter_texts.append(text)

        # 使用 _interleave_units_and_chapters 按正确顺序排列单元和章节
        final_parts = _interleave_units_and_chapters(existing_units, all_chapter_texts)
        final_blueprint = "\n\n".join(final_parts)

        # 每次生成完一个分块后都保存到文件
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)

        current_chunk += 1
        current_start = current_end + 1

    logging.info(f"Chapters [{start_chapter}..{end_chapter}] blueprint have been generated successfully.")
    logging.info(f"Final blueprint contains {len(existing_units)} units and {len(in_range_chapters) + len(before_chapters) + len(after_chapters)} chapters.")
