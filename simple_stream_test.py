# simple_stream_test.py
# -*- coding: utf-8 -*-
"""
简单测试流式输出回调函数
"""
def test_stream_callback(chunk: str):
    """测试流式输出回调函数"""
    if chunk:
        print(f"[流式输出] 收到chunk，长度: {len(chunk)}")
        print(f"[流式输出] 内容: {chunk}")
    else:
        print("[流式输出] 收到空chunk或None")

def main():
    """主函数"""
    print("="*50)
    print("开始测试流式输出回调函数")
    print("="*50)

    # 模拟流式输出
    test_chunks = [
        "这是第一章的内容。",
        "主角来到了神秘地点，",
        "发现了一个神秘的物品。",
        "物品散发着奇异的光芒，",
        "主角决定仔细观察。",
        "突然，一阵风吹过，",
        "物品开始发出声音。",
        "主角意识到这可能是一个重要的发现。",
        "他决定将物品带回研究。",
        "这是故事的开始。"
    ]

    print("模拟流式输出...")
    for i, chunk in enumerate(test_chunks):
        print(f"发送第{i+1}个chunk...")
        test_stream_callback(chunk)

    print("="*50)
    print("测试完成")
    print("="*50)

if __name__ == "__main__":
    main()
