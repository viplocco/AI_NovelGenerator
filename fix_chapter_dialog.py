import re

# 读取文件
with open("ui/chapter_directory_dialog.py", "r", encoding="utf-8") as f:
    content = f.read()

# 定义旧代码和新代码
old_code = """                        if text:
                            # 检查是否是章节标题，如果是，确保在新的一行开始
                            if re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', text):
                                # 获取当前文本框的最后一行
                                current_content = self.output_text.get("end-1c linestart", "end-1c lineend")
                                # 如果最后一行不是空行，先添加换行符
                                if current_content and not current_content.isspace():
                                    self.output_text.insert("end", "\\n")
                            self.output_text.insert("end", text)"""

new_code = """                        if text:
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
                            self.output_text.insert("end", text)"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open("ui/chapter_directory_dialog.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("修复成功")
else:
    print("未找到目标代码")
