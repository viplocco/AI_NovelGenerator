#novel_generator/finalization.py
# -*- coding: utf-8 -*-
"""
定稿章节和扩写章节（finalize_chapter、enrich_chapter_text）
"""
import os
import logging
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
from prompt_definitions import summary_prompt, update_character_state_prompt, update_plot_arcs_prompt
from novel_generator.common import invoke_with_cleaning
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import update_vector_store

def finalize_chapter(
    novel_number: int,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    filepath: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600
):
    """
    对指定章节做最终处理：更新前文摘要、更新角色状态、插入向量库等。
    默认无需再做扩写操作，若有需要可在外部调用 enrich_chapter_text 处理后再定稿。
    """
    logging.info(f"📖 开始定稿第{novel_number}章...")
    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    chapter_text = read_file(chapter_file).strip()
    if not chapter_text:
        logging.warning(f"⚠️ 第{novel_number}章内容为空，无法定稿")
        return
    logging.info(f"✓ 已读取第{novel_number}章内容（共{len(chapter_text)}字）")

    global_summary_file = os.path.join(filepath, "global_summary.txt")
    old_global_summary = read_file(global_summary_file)
    character_state_file = os.path.join(filepath, "character_state.txt")
    old_character_state = read_file(character_state_file)

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    logging.info("📝 正在更新前文摘要...")
    prompt_summary = summary_prompt.format(
        chapter_text=chapter_text,
        global_summary=old_global_summary
    )
    new_global_summary = invoke_with_cleaning(llm_adapter, prompt_summary)
    if not new_global_summary.strip():
        new_global_summary = old_global_summary
        logging.warning("⚠️ 前文摘要生成失败，保留原摘要")
    logging.info(f"✓ 前文摘要已更新（共{len(new_global_summary)}字）")

    logging.info("👤 正在更新角色状态...")
    prompt_char_state = update_character_state_prompt.format(
        chapter_text=chapter_text,
        old_state=old_character_state
    )
    new_char_state = invoke_with_cleaning(llm_adapter, prompt_char_state)
    if not new_char_state.strip():
        new_char_state = old_character_state
        logging.warning("⚠️ 角色状态更新失败，保留原状态")
    logging.info(f"✓ 角色状态已更新（共{len(new_char_state)}字）")

    # 更新剧情要点
    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    old_plot_arcs = ""
    if os.path.exists(plot_arcs_file):
        old_plot_arcs = read_file(plot_arcs_file)
    prompt_plot_arcs = update_plot_arcs_prompt.format(
        chapter_text=chapter_text,
        old_plot_arcs=old_plot_arcs
    )
    new_plot_arcs = invoke_with_cleaning(llm_adapter, prompt_plot_arcs)
    if not new_plot_arcs.strip():
        new_plot_arcs = old_plot_arcs

    clear_file_content(global_summary_file)
    save_string_to_txt(new_global_summary, global_summary_file)
    clear_file_content(character_state_file)
    save_string_to_txt(new_char_state, character_state_file)
    clear_file_content(plot_arcs_file)
    save_string_to_txt(new_plot_arcs, plot_arcs_file)
    
    # 同步角色库
    _sync_character_library(filepath, new_char_state)

    logging.info("🔍 正在更新向量库...")
    update_vector_store(
        embedding_adapter=create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        ),
        new_chapter=chapter_text,
        filepath=filepath
    )
    logging.info("✓ 向量库更新完成")

    logging.info(f"✅ 第{novel_number}章定稿完成！")

def enrich_chapter_text(
    chapter_text: str,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    interface_format: str,
    max_tokens: int,
    timeout: int=600
) -> str:
    """
    对章节文本进行扩写，使其更接近 word_number 字数，保持剧情连贯。
    """
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    prompt = f"""以下章节文本较短，请在保持剧情连贯的前提下进行扩写，使其更充实，接近 {word_number} 字左右：
原内容：
{chapter_text}
"""
    enriched_text = invoke_with_cleaning(llm_adapter, prompt)
    return enriched_text


def _sync_character_library(filepath: str, character_state: str):
    """
    将角色状态同步到角色库
    """
    import re
    
    # 角色库路径
    library_path = os.path.join(filepath, "角色库")
    os.makedirs(library_path, exist_ok=True)
    
    # 确保"全部"分类存在
    all_category = os.path.join(library_path, "全部")
    os.makedirs(all_category, exist_ok=True)
    
    # 解析角色状态
    characters = _parse_character_state(character_state)
    
    # 更新或创建角色文件
    for char_name, char_data in characters.items():
        char_file = os.path.join(all_category, f"{char_name}.txt")
        
        # 构建角色文件内容
        content_lines = [f"{char_name}："]
        for attr_name, items in char_data.items():
            content_lines.append(f"├──{attr_name}")
            for i, item in enumerate(items):
                prefix = "├──" if i < len(items) - 1 else "└──"
                content_lines.append(f"│  {prefix}{item}")
        
        # 写入文件
        with open(char_file, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))


def _parse_character_state(character_state: str) -> dict:
    """
    解析角色状态文本，返回角色字典
    """
    import re
    
    characters = {}
    current_char = None
    current_attr = None
    
    for line in character_state.split("\n"):
        # 不对行进行strip，以保留│前缀
        original_line = line
        line = line.strip()
        
        # 检测角色名称行（兼容中英文冒号和前后空格）
        role_match = re.match(r"^([\u4e00-\u9fa5a-zA-Z0-9]+)\s*[:：]\s*$", line)
        if role_match:
            current_char = role_match.group(1).strip()
            characters[current_char] = {
                "物品": [],
                "能力": [],
                "状态": [],
                "主要角色间关系网": [],
                "触发或加深的事件": []
            }
            current_attr = None
            continue
        
        if not current_char:
            continue
        
        # 解析属性（支持子属性）
        # 先尝试匹配带│前缀的格式（带或不带冒号）
        # 使用更精确的正则表达式，确保只匹配属性名称，不匹配条目
        attr_match = re.match(r"^│\s+([├└]──)([^：:：]+)\s*[:：]?$", original_line)
        if not attr_match:
            # 再尝试匹配不带│前缀的格式（带或不带冒号）
            attr_match = re.match(r"^([├└]──)([^：:：]+)\s*[:：]?$", original_line)
        if attr_match:
            prefix, attr_name = attr_match.groups()
            attr_name = attr_name.strip()
            # 匹配预设属性
            for preset_attr in characters[current_char]:
                if attr_name == preset_attr:
                    current_attr = preset_attr
                    break
            continue
        
        # 解析属性条目 - 支持两种格式：
        # 1. 以│开头的条目（标准格式）
        # 2. 直接以├──或└──开头的条目（非标准格式）
        # 注意：必须确保不将属性分类行误识别为条目
        item_match = re.match(r"^│\s+([├└]──)\s*(.*)", original_line)
        if item_match and current_attr:
            prefix, content = item_match.groups()
            content = content.strip()
            if content:
                # 检查内容是否是属性分类名称（避免将分类误识别为条目）
                # 只有当内容完全匹配属性分类名称时才跳过
                if content not in ["物品", "能力", "状态", "主要角色间关系网", "触发或加深的事件"]:
                    characters[current_char][current_attr].append(content)
        else:
            # 尝试解析不以│开头的条目
            direct_item_match = re.match(r"^\s+([├└]──)\s*(.*)", original_line)
            if direct_item_match and current_attr:
                prefix, content = direct_item_match.groups()
                content = content.strip()
                if content:
                    # 检查内容是否是属性分类名称（避免将分类误识别为条目）
                    if content not in ["物品", "能力", "状态", "主要角色间关系网", "触发或加深的事件"]:
                        characters[current_char][current_attr].append(content)
    
    return characters
