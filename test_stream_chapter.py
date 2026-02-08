# test_stream_chapter.py
# -*- coding: utf-8 -*-
"""
测试章节草稿流式输出功能
"""
import sys
import os
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_adapters import create_llm_adapter
from novel_generator.chapter import generate_chapter_draft_stream

def test_stream_callback(chunk: str):
    """测试流式输出回调函数"""
    if chunk:
        print(f"[流式输出] 收到chunk，长度: {len(chunk)}")
        print(f"[流式输出] 内容: {chunk}")
    else:
        print("[流式输出] 收到空chunk或None")

def main():
    """主函数"""
    # 测试参数
    api_key = "your_api_key"
    base_url = "https://api.openai.com/v1"
    model_name = "gpt-3.5-turbo"
    filepath = "test_novel"
    novel_number = 1
    word_number = 500
    temperature = 0.7
    user_guidance = "这是一个测试章节"
    characters_involved = "主角"
    key_items = "神秘物品"
    scene_location = "神秘地点"
    time_constraint = "紧迫"
    embedding_api_key = ""
    embedding_url = ""
    embedding_interface_format = "openai"
    embedding_model_name = "text-embedding-ada-002"
    embedding_retrieval_k = 2
    interface_format = "openai"
    max_tokens = 2048
    timeout = 600
    custom_prompt_text = "请写一段关于主角在神秘地点发现神秘物品的章节内容，大约500字。"

    print("="*50)
    print("开始测试章节草稿流式输出功能")
    print("="*50)

    # 创建测试目录
    os.makedirs(filepath, exist_ok=True)

    # 调用流式生成函数
    print("
调用generate_chapter_draft_stream...")
    draft_text = generate_chapter_draft_stream(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        filepath=filepath,
        novel_number=novel_number,
        word_number=word_number,
        temperature=temperature,
        user_guidance=user_guidance,
        characters_involved=characters_involved,
        key_items=key_items,
        scene_location=scene_location,
        time_constraint=time_constraint,
        embedding_api_key=embedding_api_key,
        embedding_url=embedding_url,
        embedding_interface_format=embedding_interface_format,
        embedding_model_name=embedding_model_name,
        embedding_retrieval_k=embedding_retrieval_k,
        interface_format=interface_format,
        max_tokens=max_tokens,
        timeout=timeout,
        custom_prompt_text=custom_prompt_text,
        stream_callback=test_stream_callback
    )

    print("
" + "="*50)
    print("测试完成")
    print("="*50)
    print(f"
生成的章节内容长度: {len(draft_text)}")
    print(f"
生成的章节内容:
{draft_text}")

if __name__ == "__main__":
    main()
