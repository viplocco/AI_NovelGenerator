# simple_integration_test.py
# -*- coding: utf-8 -*-
"""
简单的集成测试
"""
import sys

# 测试1：导入测试
print("="*50)
print("测试1：导入测试")
print("="*50)
try:
    from llm_adapters import create_llm_adapter
    from novel_generator.stream_utils import invoke_with_cleaning_stream
    from novel_generator.architecture_wizard import ArchitectureWizardLogic
    print("✓ 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2：创建适配器
print("\n" + "="*50)
print("测试2：创建适配器")
print("="*50)
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

# 测试3：创建ArchitectureWizardLogic
print("\n" + "="*50)
print("测试3：创建ArchitectureWizardLogic")
print("="*50)
try:
    wizard = ArchitectureWizardLogic(
        interface_format='deepseek',
        api_key='sk-20a8aa3e8abe4fe7a540e6f456b021f5',
        base_url='https://api.deepseek.com',
        llm_model='deepseek-chat',
        topic="测试小说",
        genre="玄幻",
        number_of_chapters=10,
        word_number=3000,
        filepath="E:/Obsidian-note/obsidian-note/小说创作",
        on_stream_callback=None
    )
    print("✓ ArchitectureWizardLogic创建成功")
    print(f"  主题: {wizard.topic}")
    print(f"  类型: {wizard.genre}")
    print(f"  章节数: {wizard.number_of_chapters}")
except Exception as e:
    print(f"✗ ArchitectureWizardLogic创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4：测试流式输出
print("\n" + "="*50)
print("测试4：测试流式输出")
print("="*50)
try:
    stream_output = []

    def stream_callback(text: str):
        stream_output.append(text)
        print(text, end='', flush=True)

    print("\n调用invoke_with_cleaning_stream...")
    result = invoke_with_cleaning_stream(
        adapter,
        "请用一句话介绍你自己。",
        stream_callback=stream_callback
    )
    print(f"\n✓ 流式输出成功")
    print(f"  结果长度: {len(result)}")
    print(f"  收集的输出长度: {sum(len(s) for s in stream_output)}")
except Exception as e:
    print(f"\n✗ 流式输出失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("所有测试完成！")
print("="*50)
