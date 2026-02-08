# integration_test.py
# -*- coding: utf-8 -*-
"""
集成测试：测试完整的架构生成流程中的流式输出
"""
import sys
import os

# 确保输出不被缓冲
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

def test_integration():
    """测试完整的架构生成流程"""
    print("="*50)
    print("开始集成测试：完整的架构生成流程")
    print("="*50)

    # 测试导入
    print("\n1. 测试导入...")
    try:
        from llm_adapters import create_llm_adapter
        from novel_generator.stream_utils import invoke_with_cleaning_stream
        from novel_generator.architecture_wizard import ArchitectureWizard
        print("✓ 导入成功")
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 创建适配器
    print("\n2. 创建适配器...")
    try:
        adapter = create_llm_adapter(
            interface_format='deepseek',
            base_url='https://api.deepseek.com',
            model_name='deepseek-chat',
            api_key='sk-20a8aa3e8abe4fe7a540e6f456b021f5',
            temperature=0.7,
            max_tokens=1000,
            timeout=60
        )
        print("✓ 适配器创建成功")
    except Exception as e:
        print(f"✗ 适配器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 创建ArchitectureWizard实例
    print("\n3. 创建ArchitectureWizard实例...")
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
            on_stream_callback=None  # 将在后面设置
        )
        print("✓ ArchitectureWizard创建成功")
    except Exception as e:
        print(f"✗ ArchitectureWizard创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试流式输出回调
    print("\n4. 测试流式输出回调...")
    try:
        stream_output = []

        def stream_callback(text: str):
            stream_output.append(text)
            print(text, end='', flush=True)

        # 设置流式输出回调
        wizard.on_stream_callback = stream_callback

        print("✓ 流式输出回调设置成功")
    except Exception as e:
        print(f"✗ 流式输出回调设置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试生成单个步骤
    print("\n5. 测试生成单个步骤...")
    try:
        step = "theme"
        print(f"\n生成步骤: {step}")

        success = wizard.generate_step(
            step,
            stream_callback=stream_callback
        )

        if success:
            print("\n✓ 步骤生成成功")
            result = wizard.step_data[step]["result"]
            print(f"结果长度: {len(result)}")
            print(f"收集的流式输出长度: {sum(len(s) for s in stream_output)}")
        else:
            print("\n✗ 步骤生成失败")
            return False
    except Exception as e:
        print(f"\n✗ 步骤生成异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*50)
    print("集成测试完成！")
    print("="*50)
    return True

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
