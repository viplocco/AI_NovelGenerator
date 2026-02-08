# chapter_blueprint_parser.py
# -*- coding: utf-8 -*-
import re

def parse_chapter_blueprint(blueprint_text: str):
    """
    解析整份章节蓝图文本，返回一个列表，每个元素是一个 dict：
    {
      "chapter_number": int,
      "chapter_title": str,
      "chapter_role": str,       # 本章定位
      "chapter_purpose": str,    # 核心作用
      "suspense_level": str,     # 悬念密度
      "foreshadowing": str,      # 伏笔操作
      "plot_twist_level": str,   # 认知颠覆
      "chapter_summary": str     # 本章简述
    }
    """

    # 先按空行进行分块，以免多章之间混淆
    chunks = re.split(r'\n\s*\n', blueprint_text.strip())
    results = []

    # 兼容多种章节标题格式
    # 例如：
    #   第1章 - 紫极光下的预兆
    #   第1章 - [紫极光下的预兆]
    #   **第1章 - 紫极光下的预兆**
    chapter_number_pattern = re.compile(r'^\*\*第\s*(\d+)\s*章\s*-\s*(.*?)\*\*$|^第\s*(\d+)\s*章\s*-\s*\[?(.*?)\]?$')

    # 增强的正则表达式，支持更多格式变体，包括带 ├── 前缀的行和不带前缀的行
    role_pattern     = re.compile(r'^├──\s*(?:章节|本章)定位[：:]\s*(.*)|^(?:章节|本章)定位[：:]\s*(.*)')
    purpose_pattern  = re.compile(r'^├──\s*核心作用[：:]\s*(.*)|^核心作用[：:]\s*(.*)')
    suspense_pattern = re.compile(r'^├──\s*悬念密度[：:]\s*(.*)|^悬念密度[：:]\s*(.*)')
    foreshadow_pattern = re.compile(r'^├──\s*伏笔(?:操作|设计)[：:]\s*(.*)|^伏笔(?:操作|设计)[：:]\s*(.*)')
    twist_pattern       = re.compile(r'^├──\s*(?:转折|认知颠覆)[：:]\s*(.*)|^(?:转折|认知颠覆)[：:]\s*(.*)')
    # 添加对"认知颠覆"字段的直接支持
    cognitive_pattern   = re.compile(r'^├──\s*认知颠覆[：:]\s*(.*)|^认知颠覆[：:]\s*(.*)')
    # 添加对"转折程度"字段的直接支持，将其映射到认知颠覆
    turn_pattern   = re.compile(r'^├──\s*转折程度[：:]\s*(.*)|^转折程度[：:]\s*(.*)')
    summary_pattern = re.compile(r'^├──\s*(?:章节|本章)简述[：:]\s*(.*)|^(?:章节|本章)简述[：:]\s*(.*)')

    for chunk in chunks:
        lines = chunk.strip().splitlines()
        if not lines:
            continue


        chapter_number   = None
        chapter_title    = ""
        chapter_role     = ""
        chapter_purpose  = ""
        suspense_level   = ""
        foreshadowing    = ""
        plot_twist_level = ""
        chapter_summary  = ""

        # 先匹配第一行（或前几行），找到章号和标题
        header_match = chapter_number_pattern.match(lines[0].strip())
        if not header_match:
            # 不符合“第X章 - 标题”的格式，跳过
            continue

        # 处理两种格式的章节标题
        if header_match.group(1) is not None:
            # 格式：**第X章 - 标题**
            chapter_number = int(header_match.group(1))
            chapter_title  = header_match.group(2).strip()
        else:
            # 格式：第X章 - 标题 或 第X章 - [标题]
            chapter_number = int(header_match.group(3))
            chapter_title  = header_match.group(4).strip()

        # 从后面的行匹配其他字段
        for line in lines[1:]:
            if not line or not line.strip():
                continue

            m_role = role_pattern.match(line)
            if m_role:
                # 获取第一个非空的捕获组
                chapter_role = (m_role.group(1) or m_role.group(2)).strip() if (m_role.group(1) or m_role.group(2)) else ""

                continue

            m_purpose = purpose_pattern.match(line)
            if m_purpose:
                # 获取第一个非空的捕获组
                chapter_purpose = (m_purpose.group(1) or m_purpose.group(2)).strip() if (m_purpose.group(1) or m_purpose.group(2)) else ""

                continue

            m_suspense = suspense_pattern.match(line)
            if m_suspense:
                # 获取第一个非空的捕获组
                suspense_level = (m_suspense.group(1) or m_suspense.group(2)).strip() if (m_suspense.group(1) or m_suspense.group(2)) else ""

                continue

            m_foreshadow = foreshadow_pattern.match(line)
            if m_foreshadow:
                # 获取第一个非空的捕获组
                foreshadowing = (m_foreshadow.group(1) or m_foreshadow.group(2)).strip() if (m_foreshadow.group(1) or m_foreshadow.group(2)) else ""

                continue

            m_twist = twist_pattern.match(line)
            if m_twist:
                # 获取第一个非空的捕获组
                plot_twist_level = (m_twist.group(1) or m_twist.group(2)).strip() if (m_twist.group(1) or m_twist.group(2)) else ""

                continue
                
            m_cognitive = cognitive_pattern.match(line)
            if m_cognitive:
                # 获取第一个非空的捕获组
                plot_twist_level = (m_cognitive.group(1) or m_cognitive.group(2)).strip() if (m_cognitive.group(1) or m_cognitive.group(2)) else ""

                continue

            m_turn = turn_pattern.match(line)
            if m_turn:
                # 将"转折程度"映射到"认知颠覆"，获取第一个非空的捕获组
                plot_twist_level = (m_turn.group(1) or m_turn.group(2)).strip() if (m_turn.group(1) or m_turn.group(2)) else ""

                continue

            m_summary = summary_pattern.match(line)
            if m_summary:
                # 获取第一个非空的捕获组
                chapter_summary = (m_summary.group(1) or m_summary.group(2)).strip() if (m_summary.group(1) or m_summary.group(2)) else ""

                continue

        results.append({
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "chapter_role": chapter_role,
            "chapter_purpose": chapter_purpose,
            "suspense_level": suspense_level,
            "foreshadowing": foreshadowing,
            "plot_twist_level": plot_twist_level,
            "chapter_summary": chapter_summary
        })

    # 按照 chapter_number 排序后返回
    results.sort(key=lambda x: x["chapter_number"])
    return results


def get_chapter_info_from_blueprint(blueprint_text: str, target_chapter_number: int):
    """
    在已经加载好的章节蓝图文本中，找到对应章号的结构化信息，返回一个 dict。
    若找不到则返回一个默认的结构。
    """
    all_chapters = parse_chapter_blueprint(blueprint_text)

    for ch in all_chapters:

        if ch["chapter_number"] == target_chapter_number:
            return ch

    # 默认返回，提供更有意义的默认值
    return {
        "chapter_number": target_chapter_number,
        "chapter_title": f"第{target_chapter_number}章",
        "chapter_role": "常规章节",
        "chapter_purpose": "内容推进",
        "suspense_level": "中等",
        "foreshadowing": "无特殊伏笔",
        "plot_twist_level": "★☆☆☆☆",
        "chapter_summary": f"第{target_chapter_number}章的剧情发展"
    }
