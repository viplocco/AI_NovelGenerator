# test_stream_simple.py
# -*- coding: utf-8 -*-
"""
简单的流式输出测试
"""
import sys
from llm_adapters import create_llm_adapter

def test_stream():
    """测试流式输出"""
    print("="*50)
    print("开始测试流式输出功能")
    print("="*50)

    # 创建适配器
    print("\n1. 创建DeepSeek适配器...")
    adapter = create_llm_adapter(
        interface_format='deepseek',
        base_url='https://api.deepseek.com',
        model_name='deepseek-chat',
        api_key='sk-20a8aa3e8abe4fe7a540e6f456b021f5',
        temperature=0.7,
        max_tokens=500,
        timeout=60
    )
    print("✓ 适配器创建成功")

    # 测试invoke方法
    print("\n2. 测试invoke方法...")
    try:
        prompt = "请用一句话介绍你自己。"
        response = adapter.invoke(prompt)
        print("✓ invoke成功")
        print(f"响应: {response}")
    except Exception as e:
        print(f"✗ invoke失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试invoke_stream方法
    print("\n3. 测试invoke_stream方法...")
    try:
        prompt = "请用三句话介绍你自己。"
        full_response = ""

        def callback(text: str):
            nonlocal full_response
            full_response += text
            print(text, end='', flush=True)

        response = adapter.invoke_stream(prompt, callback)
        print("\n✓ invoke_stream成功")
        print(f"返回的响应长度: {len(response)}")
        print(f"回调收集的响应长度: {len(full_response)}")
        print(f"响应一致: {response == full_response}")
    except Exception as e:
        print(f"✗ invoke_stream失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试stream_utils
    print("\n4. 测试stream_utils...")
    try:
        from novel_generator.stream_utils import invoke_with_cleaning_stream

        prompt = "请用五句话介绍你自己。"
        result = invoke_with_cleaning_stream(
            adapter,
            prompt,
            stream_callback=lambda text: print(text, end='', flush=True)
        )
        print("\n✓ stream_utils成功")
        print(f"结果长度: {len(result)}")
    except Exception as e:
        print(f"✗ stream_utils失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*50)
    print("所有测试完成！")
    print("="*50)
    return True

if __name__ == "__main__":
    success = test_stream()
    sys.exit(0 if success else 1)
