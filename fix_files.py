import re

# 修复1: blueprint_stream.py - 移除重复的 stream_callback 调用
print("修复 blueprint_stream.py...")
with open("novel_generator/blueprint_stream.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到并替换第583-592行（索引582-591）
new_lines = lines[:582]  # 保留583行之前的内容

# 添加替换的注释
new_lines.append("                # 注：流式输出已在 invoke_with_streaming 中完成，此处不再重复调用\n")
new_lines.append("                # 以避免内容重复显示\n")
new_lines.append("                pass\n")

# 添加593行之后的内容（从索引593开始）
new_lines.extend(lines[593:])

with open("novel_generator/blueprint_stream.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("  blueprint_stream.py 修复完成")

# 修复2: chapter_directory_dialog.py - 添加第一个章节的空行分隔逻辑
print("修复 chapter_directory_dialog.py...")
with open("ui/chapter_directory_dialog.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = '''                        if text:
                            # 检查是否是章节标题，如果是，确保在新的一行开始
                            if re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', text):
                                # 获取当前文本框的最后一行
                                current_content = self.output_text.get("end-1c linestart", "end-1c lineend")
                                # 如果最后一行不是空行，先添加换行符
                                if current_content and not current_content.isspace():
                                    self.output_text.insert("end", "\\n")
                            self.output_text.insert("end", text)'''

new_code = '''                        if text:
                            # 检查是否是章节标题，如果是，确保在新的一行开始
                            if re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', text):
                                # 获取当前文本框的全部内容，检查是否已包含章节
                                full_content = self.output_text.get("0.0", "end")
                                has_existing_chapter = bool(re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', full_content))
                                
                                # 获取当前文本框的最后一行
                                current_content = self.output_text.get("end-1c linestart", "end-1c lineend")
                                
                                if not has_existing_chapter:
                                    # 这是第一个章节，需要与单元信息分隔（添加两个空行）
                                    if current_content and not current_content.isspace():
                                        self.output_text.insert("end", "\\n\\n")
                                else:
                                    # 不是第一个章节，正常处理
                                    # 如果最后一行不是空行，先添加换行符
                                    if current_content and not current_content.isspace():
                                        self.output_text.insert("end", "\\n")
                            self.output_text.insert("end", text)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open("ui/chapter_directory_dialog.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("  chapter_directory_dialog.py 修复完成")
else:
    print("  未找到目标代码，可能需要手动检查")

print("所有修复完成！")
