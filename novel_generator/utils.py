"""
公共工具函数模块
"""

import logging
from string import Formatter


def safe_format(template: str, **kwargs) -> str:
    """安全格式化函数，处理包含花括号的内容

    参数:
        template: 模板字符串
        **kwargs: 要替换的键值对

    返回:
        格式化后的字符串
    """
    # 转义所有字符串值中的花括号
    safe_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, str):
            # 将{替换为{{，}替换为}}，避免被format误认为是占位符
            safe_kwargs[key] = value.replace('{', '{{').replace('}', '}}')
        else:
            safe_kwargs[key] = value

    try:
        return Formatter().format(template, **safe_kwargs)
    except Exception as e:
        # 如果格式化失败，记录错误并返回原始模板
        logging.warning(f"格式化失败: {str(e)}, 使用原始模板")
        return template


def extract_metadata(text: str, tag_name: str) -> str:
    """提取知识库元数据，支持多种格式

    参数:
        text: 包含元数据的文本
        tag_name: 标签名称（如"类型"、"分类"、"关键词"）

    返回:
        提取的元数据值，如果未找到则返回空字符串
    """
    import re

    if not text or not tag_name:
        return ""

    # 支持多种换行符和格式的正则表达式模式
    patterns = [
        rf'【{tag_name}】(.+?)[
]+',  # Windows换行符
        rf'【{tag_name}】(.+?)
',      # Unix换行符
        rf'【{tag_name}】(.+?)(?=【|$)',  # 到下一个标签或结尾
        rf'【{tag_name}】(.+?)\s+',      # 任意空白字符
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return ""
