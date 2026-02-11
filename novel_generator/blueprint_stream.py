
# novel_generator/blueprint_stream.py
# -*- coding: utf-8 -*-
"""
支持流式输出的章节蓝图生成
"""
import os
import re
import logging
from novel_generator.blueprint import compute_chunk_size, limit_chapter_blueprint
from llm_adapters import create_llm_adapter
from prompt_definitions import chunked_chapter_blueprint_prompt
from utils import read_file, clear_file_content, save_string_to_txt


def extract_cluster_headers(blueprint_text: str) -> list:
    """
    提取章节目录中的集群标题和元数据块
    
    支持的格式示例：
    ## 第一集群：幸存者之誓（第1-5章）
    **修为范围：** 炼气一层 → 炼气一层稳固  
    **空间范围：** 西山村废墟 → 后山坟地 → 山林逃亡
    
    或：
    # 第十二集群：罪民后裔（第96-100章）
    **修为范围：** 炼气八层门槛 → 炼气八层  
    **空间范围：** 绿洲遗迹 → 地下洞穴 → 部落聚居地
    
    返回: [(起始章节号, 集群标题完整内容), ...]
    """
    cluster_headers = []
    
    # 更灵活的匹配模式：
    # 1. 支持 # 或 ## 开头
    # 2. 集群名称后可能有冒号也可能没有
    # 3. 章节范围支持多种分隔符和括号格式
    title_pattern = r'^#{1,2}\s*第([一二三四五六七八九十百千万]+)集群\s*[：:\uFF1A]?\s*[^\n]*?[（(]?\s*第\s*(\d+)\s*[-—~至]+\s*(\d+)\s*章'
    
    # 找到所有集群标题的位置
    title_matches = list(re.finditer(title_pattern, blueprint_text, flags=re.MULTILINE))
    
    for i, match in enumerate(title_matches):
        start_pos = match.start()
        # 集群内容结束位置：下一个集群开始前，或文件末尾
        end_pos = title_matches[i + 1].start() if i + 1 < len(title_matches) else len(blueprint_text)
        
        # 提取完整的集群内容（包括后续的元数据行）
        cluster_content = blueprint_text[start_pos:end_pos].strip()
        
        # 提取起始章节号
        start_chapter = int(match.group(2)) if match.group(2) else 0
        if start_chapter > 0:
            cluster_headers.append((start_chapter, cluster_content))
    
    return cluster_headers

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
    # 这里需要根据实际的LLM适配器实现流式输出
    # 如果LLM适配器支持流式输出，则使用流式输出
    # 否则，使用普通方式生成，然后模拟流式输出

    result = ""

    # 尝试使用流式输出
    try:
        # 检查LLM适配器是否支持流式输出
        if hasattr(llm_adapter, 'invoke_stream'):
            # 使用流式输出
            result = llm_adapter.invoke_stream(prompt, stream_callback if stream_callback else lambda x: None)
        else:
            # 不支持流式输出，使用普通方式
            result = llm_adapter.invoke(prompt)
            if stream_callback:
                # 模拟流式输出
                chunk_size = 100  # 每次输出100个字符
                for i in range(0, len(result), chunk_size):
                    chunk = result[i:i+chunk_size]
                    stream_callback(chunk)
    except Exception as e:
        logging.error(f"Error during streaming: {e}")
        # 如果流式输出失败，尝试使用普通方式
        try:
            result = llm_adapter.invoke(prompt)
            if stream_callback:
                # 模拟流式输出
                chunk_size = 100  # 每次输出100个字符
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

    # 提取集群标题和元数据（在处理章节前先保存）
    cluster_headers = []
    if existing_blueprint:
        cluster_headers = extract_cluster_headers(existing_blueprint)
        if cluster_headers:
            logging.info(f"Found {len(cluster_headers)} cluster headers to preserve.")

    # 将已有目录分割成章节列表
    existing_chapters = []
    if existing_blueprint:
        # 使用更精确的模式匹配章节，确保捕获完整的章节内容
        pattern = r"(第\s*\d+\s*章[\s\S]*?)(?=第\s*\d+\s*章[\s\S]*?$|$)"
        existing_chapters = re.findall(pattern, existing_blueprint, flags=re.DOTALL)

    # 分离出不在生成范围内的章节
    before_chapters = []  # 起始章节之前的章节
    after_chapters = []   # 结束章节之后的章节
    in_range_chapters = {}  # 生成范围内的已有章节（用于去重）
    # 用于跟踪所有已生成的章节（包括之前生成的）
    all_generated_chapters = {}  # 章节号 -> 章节内容

    for chapter_text in existing_chapters:
        match = re.search(r"第\s*(\d+)\s*章", chapter_text)
        if match:
            chapter_num = int(match.group(1))
            # 清理章节内容，去除开头和结尾的"**"等markdown格式符号
            chapter_text = chapter_text.strip()
            # 去除开头的"**"
            while chapter_text.startswith("**"):
                chapter_text = chapter_text[2:].lstrip()
            # 去除结尾的"**"
            while chapter_text.endswith("**"):
                chapter_text = chapter_text[:-2].rstrip()

            if chapter_num < start_chapter:
                before_chapters.append(chapter_text)
                all_generated_chapters[chapter_num] = chapter_text
            elif chapter_num > end_chapter:
                after_chapters.append(chapter_text)
                all_generated_chapters[chapter_num] = chapter_text
            else:
                # 保存生成范围内的已有章节，用于后续去重
                in_range_chapters[chapter_num] = chapter_text
                all_generated_chapters[chapter_num] = chapter_text

    # 准备最终目录内容（只在第一次循环时初始化）
    final_blueprint = "\n\n".join(before_chapters)
    if final_blueprint:
        final_blueprint += "\n\n"
    
    # 用于跟踪是否是最后一次循环
    is_last_chunk = False

    # 循环生成指定范围内的章节
    current_start = start_chapter
    total_chunks = (end_chapter - start_chapter + chunk_size) // chunk_size
    current_chunk = 0

    while current_start <= end_chapter:
        current_end = min(current_start + chunk_size - 1, end_chapter)
        
        # 检查是否是最后一次循环
        is_last_chunk = (current_end == end_chapter)

        # 获取上下文目录（限制为最近100章）
        # 包含：起始章节之前的章节 + 生成范围内的已有章节 + 结束章节之后的章节（最多50章）
        in_range_chapters_list = [text for num, text in sorted(in_range_chapters.items())]
        # 确保after_chapters不为空时才进行切片
        after_chapters_sample = after_chapters[-50:] if after_chapters else []
        context_blueprint = "\n\n".join(before_chapters + in_range_chapters_list + after_chapters_sample)
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
            world_building=""  # 添加world_building参数，设为空字符串
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
            # 保存已有内容
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            # 通过回调函数通知用户
            if stream_callback:
                stream_callback(f"\n\n❌ {error_msg}")
            raise ValueError(error_msg)

        # 清理新生成的章节内容（仅清理明显的格式问题，保留原有格式）
        cleaned_result = chunk_result.strip()
        # 只清理开头的 ## 标记（如果存在）
        if cleaned_result.startswith("##"):
            cleaned_result = cleaned_result[2:].lstrip()
        # 清理开头的空行
        while cleaned_result.startswith("\n"):
            cleaned_result = cleaned_result[1:]

        # 将新生成的章节分割成单独的章节
        new_chapters = []
        new_pattern = r"(第\s*\d+\s*章[\s\S]*?)(?=第\s*\d+\s*章[\s\S]*?$|$)"
        new_chapters_text = re.findall(new_pattern, cleaned_result, flags=re.DOTALL)
        
        # 处理新生成的章节
        for new_chapter in new_chapters_text:
            # 清理章节内容，去除开头和结尾的"**"等markdown格式符号
            new_chapter = new_chapter.strip()
            # 去除开头的"**"
            while new_chapter.startswith("**"):
                new_chapter = new_chapter[2:].lstrip()
            # 去除结尾的"**"
            while new_chapter.endswith("**"):
                new_chapter = new_chapter[:-2].rstrip()

            # 提取章节号
            new_match = re.search(r"第\s*(\d+)\s*章", new_chapter)
            if new_match:
                new_chapter_num = int(new_match.group(1))
                # 验证章节号的有效性
                if new_chapter_num <= 0:
                    logging.warning(f"无效的章节号：{new_chapter_num}，跳过该章节")
                    continue
                # 检查是否在生成范围内
                if start_chapter <= new_chapter_num <= end_chapter:
                    # 检查是否已存在该章节
                    if new_chapter_num in in_range_chapters:
                        # 章节已存在，跳过（保留原有内容）
                        continue
                    # 添加新章节
                    new_chapters.append((new_chapter_num, new_chapter))
                    # 更新 in_range_chapters，防止重复
                    in_range_chapters[new_chapter_num] = new_chapter
        
        # 按章节号排序新章节
        new_chapters.sort(key=lambda x: x[0])
        
        # 构建完整的章节列表（包括 before、新生成的、after）
        all_chapters = []
        
        # 添加 before_chapters（使用章节号作为键）
        for text in before_chapters:
            match = re.search(r"第\s*(\d+)\s*章", text)
            if match:
                chapter_num = int(match.group(1))
                all_chapters.append((chapter_num, text))
        
        # 添加 in_range_chapters（生成范围内的已有章节）
        if in_range_chapters:  # 确保in_range_chapters不为空
            for chapter_num, text in sorted(in_range_chapters.items()):
                all_chapters.append((chapter_num, text))

        # 添加新生成的章节
        for new_chapter_num, new_chapter_text in new_chapters:
            # 找到正确的插入位置
            insert_index = len(all_chapters)
            for i, (chapter_num, text) in enumerate(all_chapters):
                if chapter_num > new_chapter_num:
                    insert_index = i
                    break
            
            # 检查是否已存在于all_chapters中（避免重复）
            if any(chapter_num == new_chapter_num for chapter_num, _ in all_chapters):
                # 章节已存在，替换为新内容
                for i, (chapter_num, _) in enumerate(all_chapters):
                    if chapter_num == new_chapter_num:
                        all_chapters[i] = (new_chapter_num, new_chapter_text)
                        break
            else:
                # 插入新章节
                all_chapters.insert(insert_index, (new_chapter_num, new_chapter_text))
        
        # 添加 after_chapters（使用章节号作为键）
        for text in after_chapters:
            match = re.search(r"第\s*(\d+)\s*章", text)
            if match:
                chapter_num = int(match.group(1))
                all_chapters.append((chapter_num, text))
        
        # 按章节号排序所有章节，确保顺序正确
        all_chapters.sort(key=lambda x: x[0])

        # 重新构建 final_blueprint
        final_blueprint = "\n\n".join([text for _, text in all_chapters])

        # 每次生成完一个分块后都保存到文件，避免生成过程中断导致内容丢失
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)

        # 更新进度
        current_chunk += 1
        # 不再输出进度信息到结果中，避免干扰用户查看内容
        # 进度信息仅在UI进度条和标签中显示

        current_start = current_end + 1

    # 重新构建最终结果，插入集群标题（仅在有集群标题时执行）
    if cluster_headers:
        # 有集群标题，需要重新解析并插入
        cluster_headers.sort(key=lambda x: x[0])
        final_parts = []
        inserted_clusters = set()  # 记录已插入的集群标题
        
        # 将 final_blueprint 重新分割成章节
        final_chapters = re.findall(r"(第\s*\d+\s*章[\s\S]*?)(?=第\s*\d+\s*章[\s\S]*?$|$)", final_blueprint, flags=re.DOTALL)
        
        for chapter_text in final_chapters:
            chapter_text = chapter_text.strip()
            match = re.search(r"第\s*(\d+)\s*章", chapter_text)
            if match:
                chapter_num = int(match.group(1))
                
                # 检查是否需要在此章节之前插入集群标题
                for cluster_start, cluster_content in cluster_headers:
                    if cluster_start == chapter_num and cluster_start not in inserted_clusters:
                        final_parts.append(cluster_content)
                        inserted_clusters.add(cluster_start)
                        logging.info(f"Inserted cluster header at chapter {cluster_start}")
                
                # 添加章节内容
                final_parts.append(chapter_text)
        
        # 检查是否有集群标题在所有章节之前（处理边界情况）
        if final_chapters:
            first_chapter_match = re.search(r"第\s*(\d+)\s*章", final_chapters[0])
            if first_chapter_match:
                first_chapter_num = int(first_chapter_match.group(1))
                # 检查是否有集群标题起始章节小于第一章
                for cluster_start, cluster_content in cluster_headers:
                    if cluster_start < first_chapter_num and cluster_start not in inserted_clusters:
                        final_parts.insert(0, cluster_content)
                        inserted_clusters.add(cluster_start)
                        logging.info(f"Inserted cluster header at beginning (chapter {cluster_start})")
        
        # 构建最终的目录内容
        final_blueprint_with_headers = "\n\n".join(final_parts)
        logging.info(f"Blueprint rebuilt with {len(inserted_clusters)} cluster headers inserted.")
    else:
        # 没有集群标题，直接使用原有内容
        final_blueprint_with_headers = final_blueprint
        logging.info("No cluster headers found, using original blueprint content")

    # 保存最终结果到文件
    clear_file_content(filename_dir)
    save_string_to_txt(final_blueprint_with_headers.strip(), filename_dir)

    logging.info(f"Chapters [{start_chapter}..{end_chapter}] blueprint have been generated successfully.")
