# test_stream.py
# -*- coding: utf-8 -*-
"""
测试流式输出功能
"""
import logging
from llm_adapters import create_llm_adapter

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_stream_output():
    """测试流式输出功能"""

    # 测试配置 - 使用实际的DeepSeek API配置
    config = {
        'interface_format': 'deepseek',  # 使用DeepSeek适配器
        'api_key': 'sk-20a8aa3e8abe4fe7a540e6f456b021f5',  # DeepSeek API密钥
        'base_url': 'https://api.deepseek.com',  # DeepSeek API地址
        'model_name': 'deepseek-chat',  # DeepSeek模型
        'temperature': 0.7,
        'max_tokens': 1000,
        'timeout': 60
    }

    # 创建适配器
    print(f"创建适配器: {config['interface_format']}")
    adapter = create_llm_adapter(
        interface_format=config['interface_format'],
        base_url=config['base_url'],
        model_name=config['model_name'],
        api_key=config['api_key'],
        temperature=config['temperature'],
        max_tokens=config['max_tokens'],
        timeout=config['timeout']
    )

    # 测试invoke方法
    print("\n" + "="*50)
    print("测试1: 普通invoke方法")
    print("="*50)
    try:
        prompt = "请用一句话介绍你自己。"
        response = adapter.invoke(prompt)
        print(f"响应: {response}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试invoke_stream方法
    print("\n" + "="*50)
    print("测试2: 流式invoke_stream方法")
    print("="*50)
    try:
        prompt = "请用三句话介绍你自己。"
        full_response = ""

        def callback(text: str):
            nonlocal full_response
            full_response += text
            print(text, end='', flush=True)

        response = adapter.invoke_stream(prompt, callback)
        print(f"\n完整响应: {response}")
        print(f"回调收集的响应: {full_response}")
    except Exception as e:
        print(f"错误: {e}")

    # 测试stream_utils
    print("\n" + "="*50)
    print("测试3: stream_utils.invoke_with_cleaning_stream")
    print("="*50)
    try:
        from novel_generator.stream_utils import invoke_with_cleaning_stream

        prompt = "请用五句话介绍你自己。"
        result = invoke_with_cleaning_stream(
            adapter,
            prompt,
            stream_callback=lambda text: print(text, end='', flush=True)
        )
        print(f"\n完整结果: {result}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_stream_output()
