# novel_generator/stream_utils.py
# -*- coding: utf-8 -*-
"""
流式输出工具函数
"""
import logging
import time

def invoke_with_cleaning_stream(llm_adapter, prompt: str, stream_callback, max_retries: int = 3) -> str:
    """
    调用 LLM 并清理返回结果（支持流式输出）

    参数:
        llm_adapter: LLM适配器
        prompt: 提示词
        stream_callback: 流式输出回调函数
        max_retries: 最大重试次数

    返回:
        清理后的结果
    """
    print("\n" + "="*50)
    print("发送到 LLM 的提示词:")
    print("-"*50)
    print(prompt)
    print("="*50 + "\n")

    result = ""
    retry_count = 0

    while retry_count < max_retries:
        try:
            # 检查是否支持真正的流式输出
            if hasattr(llm_adapter, 'invoke_stream'):
                logging.info("使用真正的流式输出")

                def on_chunk(text: str):
                    nonlocal result
                    result += text
                    if stream_callback:
                        stream_callback(text)

                result = llm_adapter.invoke_stream(prompt, on_chunk)

                # 清理结果中的特殊格式标记
                result = result.replace("```", "").strip()

                print("\n" + "="*50)
                print("LLM 返回的内容:")
                print("-"*50)
                print(result)
                print("="*50 + "\n")

                if result:
                    return result
                else:
                    print(f"LLM返回空内容，准备重试 ({retry_count + 1}/{max_retries})")
                    retry_count += 1
            else:
                # 回退到假流式输出
                logging.info("适配器不支持流式输出，使用假流式输出")
                response = llm_adapter.invoke(prompt)

                print("\n" + "="*50)
                print("LLM 返回的内容:")
                print("-"*50)
                print(response)
                print("="*50 + "\n")

                # 清理结果中的特殊格式标记
                response = response.replace("```", "").strip()

                if response:
                    # 优化假流式输出：减小chunk_size，加快输出速度
                    chunk_size = 10  # 从50改为10
                    for i in range(0, len(response), chunk_size):
                        chunk = response[i:i + chunk_size]
                        if stream_callback:
                            stream_callback(chunk)
                        # 减少延迟
                        time.sleep(0.005)  # 从0.01改为0.005

                    return response
                else:
                    # response为空，需要重试
                    print(f"LLM返回空内容，准备重试 ({retry_count + 1}/{max_retries})")
                    retry_count += 1
        except Exception as e:
            print(f"调用失败 ({retry_count + 1}/{max_retries}): {str(e)}")
            retry_count += 1
            if retry_count >= max_retries:
                raise e

    return ""  # 所有重试都失败，返回空字符串
