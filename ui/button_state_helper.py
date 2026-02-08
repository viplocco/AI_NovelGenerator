# ui/button_state_helper.py
# -*- coding: utf-8 -*-
"""
按钮状态管理辅助函数
"""
import os


def check_file_exists_and_not_empty(filepath):
    """检查文件是否存在且不为空

    参数:
        filepath: 文件路径

    返回:
        bool: 文件是否存在且不为空
    """
    try:
        if not os.path.exists(filepath):
            return False
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return len(content) > 0
    except Exception as e:
        print(f"检查文件时出错: {e}")
        return False


def is_architecture_generated(filepath_var):
    """检查架构是否已生成

    参数:
        filepath_var: 文件路径变量

    返回:
        bool: 架构是否已生成
    """
    filepath = filepath_var.get().strip()
    if not filepath:
        return False
    architecture_file = os.path.join(filepath, "Novel_architecture.txt")
    return check_file_exists_and_not_empty(architecture_file)


def is_directory_generated(filepath_var):
    """检查目录是否已生成

    参数:
        filepath_var: 文件路径变量

    返回:
        bool: 目录是否已生成
    """
    filepath = filepath_var.get().strip()
    if not filepath:
        return False
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    return check_file_exists_and_not_empty(directory_file)


def is_chapter_draft_generated(filepath_var, chapter_num_var, safe_get_int_func):
    """检查当前章节草稿是否已生成

    参数:
        filepath_var: 文件路径变量
        chapter_num_var: 章节号变量
        safe_get_int_func: 安全获取整数的函数

    返回:
        bool: 当前章节草稿是否已生成
    """
    filepath = filepath_var.get().strip()
    if not filepath:
        return False
    chap_num = safe_get_int_func(chapter_num_var, 1)
    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")
    return check_file_exists_and_not_empty(chapter_file)


def is_chapter_finalized(filepath_var, chapter_num_var, safe_get_int_func):
    """检查当前章节是否已定稿

    参数:
        filepath_var: 文件路径变量
        chapter_num_var: 章节号变量
        safe_get_int_func: 安全获取整数的函数

    返回:
        bool: 当前章节是否已定稿
    """
    # 定稿和草稿使用相同的文件，所以这里返回与is_chapter_draft_generated相同的结果
    return is_chapter_draft_generated(filepath_var, chapter_num_var, safe_get_int_func)
