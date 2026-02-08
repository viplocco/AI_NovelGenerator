# quick_test.py
# -*- coding: utf-8 -*-
import sys
import os

# 确保输出不被缓冲
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

# 测试导入
print("1. 测试导入...")
try:
    from llm_adapters import create_llm_adapter
    from novel_generator.stream_utils import invoke_with_cleaning_stream
    print("✓ 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试创建适配器
print("\n2. 测试创建适配器...")
try:
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
except Exception as e:
    print(f"✗ 适配器创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试invoke方法
print("\n3. 测试invoke方法...")
try:
    prompt = "请用一句话介绍你自己。"
    response = adapter.invoke(prompt)
    print("✓ invoke成功")
    print(f"响应: {response}")
except Exception as e:
    print(f"✗ invoke失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试invoke_stream方法
print("\n4. 测试invoke_stream方法...")
try:
    prompt = "请用三句话介绍你自己。"

    class StreamCallback:
        def __init__(self):
            self.full_response = ""

        def __call__(self, text: str):
            self.full_response += text
            print(text, end='', flush=True)

    callback = StreamCallback()
    response = adapter.invoke_stream(prompt, callback)
    print("\n✓ invoke_stream成功")
    print(f"返回的响应长度: {len(response)}")
    print(f"回调收集的响应长度: {len(callback.full_response)}")
    print(f"响应一致: {response == callback.full_response}")
except Exception as e:
    print(f"✗ invoke_stream失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("所有测试完成！")
print("="*50)
