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
    #   第1章 - 紫极光下的预兆（无方括号或星号）
    chapter_number_pattern = re.compile(r'^\*\*第\s*(\d+)\s*章\s*-\s*(.*?)\*\*$|^第\s*(\d+)\s*章\s*-\s*(.*?)$|^第\s*(\d+)\s*章\s*-\s*\[(.*?)\]$')

    # 增强的正则表达式，支持更多格式变体
    # 支持的格式：
    # 1. **字段名**：值
    # 2. ├── 字段名：值
    # 3. 字段名：值
    # 4. 字段名：值（不带冒号）
    # 5. 字段名=值
    role_pattern     = re.compile(r'^\*\*(?:章节|本章)定位\*\*[：:=]\s*(.*)|^├──\s*(?:章节|本章)定位[：:=]\s*(.*)|^(?:章节|本章)定位[：:=]\s*(.*)|^(?:章节|本章)定位\s+(.*)', re.IGNORECASE)
    purpose_pattern  = re.compile(r'^\*\*核心作用\*\*[：:=]\s*(.*)|^├──\s*核心作用[：:=]\s*(.*)|^核心作用[：:=]\s*(.*)|^核心作用\s+(.*)', re.IGNORECASE)
    suspense_pattern = re.compile(r'^\*\*悬念密度\*\*[：:=]\s*(.*)|^├──\s*悬念密度[：:=]\s*(.*)|^悬念密度[：:=]\s*(.*)|^悬念密度\s+(.*)', re.IGNORECASE)
    foreshadow_pattern = re.compile(r'^\*\*伏笔(?:操作|设计)\*\*[：:=]\s*(.*)|^├──\s*伏笔(?:操作|设计)[：:=]\s*(.*)|^伏笔(?:操作|设计)[：:=]\s*(.*)|^伏笔(?:操作|设计)\s+(.*)', re.IGNORECASE)
    twist_pattern       = re.compile(r'^\*\*(?:转折|认知颠覆)\*\*[：:=]\s*(.*)|^├──\s*(?:转折|认知颠覆)[：:=]\s*(.*)|^(?:转折|认知颠覆)[：:=]\s*(.*)|^(?:转折|认知颠覆)\s+(.*)', re.IGNORECASE)
    cognitive_pattern   = re.compile(r'^\*\*认知颠覆\*\*[：:=]\s*(.*)|^├──\s*认知颠覆[：:=]\s*(.*)|^认知颠覆[：:=]\s*(.*)|^认知颠覆\s+(.*)', re.IGNORECASE)
    turn_pattern   = re.compile(r'^\*\*转折程度\*\*[：:=]\s*(.*)|^├──\s*转折程度[：:=]\s*(.*)|^转折程度[：:=]\s*(.*)|^转折程度\s+(.*)', re.IGNORECASE)
    cultivation_pattern = re.compile(r'^\*\*主角修为\*\*[：:=]\s*(.*)|^├──\s*主角修为[：:=]\s*(.*)|^主角修为[：:=]\s*(.*)|^主角修为\s+(.*)', re.IGNORECASE)
    scene_pattern = re.compile(r'^\*\*空间坐标\*\*[：:=]\s*(.*)|^├──\s*空间坐标[：:=]\s*(.*)|^空间坐标[：:=]\s*(.*)|^空间坐标\s+(.*)', re.IGNORECASE)
    summary_pattern = re.compile(r'^\*\*(?:章节|本章)简述\*\*[：:=]\s*(.*)|^├──\s*(?:章节|本章)简述[：:=]\s*(.*)|^(?:章节|本章)简述[：:=]\s*(.*)|^(?:章节|本章)简述\s+(.*)', re.IGNORECASE)

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
        surface_cultivation = ""
        actual_cultivation = ""
        scene_location = ""
        chapter_summary  = ""

        # 先匹配第一行（或前几行），找到章号和标题
        header_match = chapter_number_pattern.match(lines[0].strip())
        if not header_match:
            # 不符合“第X章 - 标题”的格式，跳过
            continue

        # 处理三种格式的章节标题
        if header_match.group(1) is not None:
            # 格式：**第X章 - 标题**
            chapter_number = int(header_match.group(1))
            chapter_title  = header_match.group(2).strip()
        elif header_match.group(3) is not None:
            # 格式：第X章 - 标题
            chapter_number = int(header_match.group(3))
            chapter_title  = header_match.group(4).strip()
        else:
            # 格式：第X章 - [标题]
            chapter_number = int(header_match.group(5))
            chapter_title  = header_match.group(6).strip()

        # 从后面的行匹配其他字段
        for line in lines[1:]:
            if not line or not line.strip():
                continue

            m_role = role_pattern.match(line)
            if m_role:
                # 获取第一个非空的捕获组
                chapter_role = (m_role.group(1) or m_role.group(2) or m_role.group(3) or m_role.group(4)).strip() if (m_role.group(1) or m_role.group(2) or m_role.group(3) or m_role.group(4)) else ""

                continue

            m_purpose = purpose_pattern.match(line)
            if m_purpose:
                # 获取第一个非空的捕获组
                chapter_purpose = (m_purpose.group(1) or m_purpose.group(2) or m_purpose.group(3) or m_purpose.group(4)).strip() if (m_purpose.group(1) or m_purpose.group(2) or m_purpose.group(3) or m_purpose.group(4)) else ""

                continue

            m_suspense = suspense_pattern.match(line)
            if m_suspense:
                # 获取第一个非空的捕获组
                suspense_level = (m_suspense.group(1) or m_suspense.group(2) or m_suspense.group(3) or m_suspense.group(4)).strip() if (m_suspense.group(1) or m_suspense.group(2) or m_suspense.group(3) or m_suspense.group(4)) else ""

                continue

            m_foreshadow = foreshadow_pattern.match(line)
            if m_foreshadow:
                # 获取第一个非空的捕获组
                foreshadowing = (m_foreshadow.group(1) or m_foreshadow.group(2) or m_foreshadow.group(3) or m_foreshadow.group(4)).strip() if (m_foreshadow.group(1) or m_foreshadow.group(2) or m_foreshadow.group(3) or m_foreshadow.group(4)) else ""

                continue

            m_twist = twist_pattern.match(line)
            if m_twist:
                # 获取第一个非空的捕获组
                plot_twist_level = (m_twist.group(1) or m_twist.group(2) or m_twist.group(3) or m_twist.group(4)).strip() if (m_twist.group(1) or m_twist.group(2) or m_twist.group(3) or m_twist.group(4)) else ""

                continue
                
            m_cognitive = cognitive_pattern.match(line)
            if m_cognitive:
                # 获取第一个非空的捕获组
                plot_twist_level = (m_cognitive.group(1) or m_cognitive.group(2) or m_cognitive.group(3) or m_cognitive.group(4)).strip() if (m_cognitive.group(1) or m_cognitive.group(2) or m_cognitive.group(3) or m_cognitive.group(4)) else ""

                continue

            m_turn = turn_pattern.match(line)
            if m_turn:
                # 将"转折程度"映射到"认知颠覆"，获取第一个非空的捕获组
                plot_twist_level = (m_turn.group(1) or m_turn.group(2) or m_turn.group(3) or m_turn.group(4)).strip() if (m_turn.group(1) or m_turn.group(2) or m_turn.group(3) or m_turn.group(4)) else ""

                continue

            m_cultivation = cultivation_pattern.match(line)
            if m_cultivation:
                # 获取第一个非空的捕获组
                cultivation_text = (m_cultivation.group(1) or m_cultivation.group(2) or m_cultivation.group(3) or m_cultivation.group(4)).strip() if (m_cultivation.group(1) or m_cultivation.group(2) or m_cultivation.group(3) or m_cultivation.group(4)) else ""
                # 解析表面修为和实际实力
                if "|" in cultivation_text:
                    surface, actual = cultivation_text.split("|", 1)
                    surface_cultivation = surface.strip().replace("表面修为", "").strip()
                    actual_cultivation = actual.strip().replace("实际实力", "").strip()
                else:
                    surface_cultivation = cultivation_text
                    actual_cultivation = cultivation_text

                continue

            m_scene = scene_pattern.match(line)
            if m_scene:
                # 获取第一个非空的捕获组
                scene_location = (m_scene.group(1) or m_scene.group(2) or m_scene.group(3) or m_scene.group(4)).strip() if (m_scene.group(1) or m_scene.group(2) or m_scene.group(3) or m_scene.group(4)) else ""

                continue

            m_summary = summary_pattern.match(line)
            if m_summary:
                # 获取第一个非空的捕获组
                chapter_summary = (m_summary.group(1) or m_summary.group(2) or m_summary.group(3) or m_summary.group(4)).strip() if (m_summary.group(1) or m_summary.group(2) or m_summary.group(3) or m_summary.group(4)) else ""

                continue

        results.append({
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "chapter_role": chapter_role,
            "chapter_purpose": chapter_purpose,
            "suspense_level": suspense_level,
            "foreshadowing": foreshadowing,
            "plot_twist_level": plot_twist_level,
            "surface_cultivation": surface_cultivation,
            "actual_cultivation": actual_cultivation,
            "scene_location": scene_location,
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
        "surface_cultivation": "未设定",
        "actual_cultivation": "未设定",
        "scene_location": "未设定",
        "chapter_summary": f"第{target_chapter_number}章的剧情发展"
    }
