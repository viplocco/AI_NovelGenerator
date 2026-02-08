# minimal_test.py
# -*- coding: utf-8 -*-
import sys

# 强制刷新输出
sys.stdout.reconfigure(line_buffering=True)

print("开始测试...", flush=True)

# 测试1：导入llm_adapters
print("\n1. 测试导入llm_adapters...", flush=True)
try:
    import llm_adapters
    print("✓ llm_adapters导入成功", flush=True)
except Exception as e:
    print(f"✗ llm_adapters导入失败: {e}", flush=True)
    sys.exit(1)

# 测试2：创建适配器
print("\n2. 测试创建适配器...", flush=True)
try:
    adapter = llm_adapters.create_llm_adapter(
        interface_format='deepseek',
        base_url='https://api.deepseek.com',
        model_name='deepseek-chat',
        api_key='sk-20a8aa3e8abe4fe7a540e6f456b021f5',
        temperature=0.7,
        max_tokens=500,
        timeout=60
    )
    print("✓ 适配器创建成功", flush=True)
except Exception as e:
    print(f"✗ 适配器创建失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3：测试invoke方法
print("\n3. 测试invoke方法...", flush=True)
try:
    response = adapter.invoke("请用一句话介绍你自己。")
    print(f"✓ invoke成功: {response[:50]}...", flush=True)
except Exception as e:
    print(f"✗ invoke失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4：测试invoke_stream方法
print("\n4. 测试invoke_stream方法...", flush=True)
try:
    output = []
    def callback(text):
        output.append(text)
        print(text, end='', flush=True)

    response = adapter.invoke_stream("请用两句话介绍你自己。", callback)
    print(f"\n✓ invoke_stream成功", flush=True)
    print(f"  返回长度: {len(response)}", flush=True)
    print(f"  收集长度: {sum(len(s) for s in output)}", flush=True)
except Exception as e:
    print(f"\n✗ invoke_stream失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n所有测试完成！", flush=True)
