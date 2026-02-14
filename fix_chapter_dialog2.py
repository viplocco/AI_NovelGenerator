import re

print("修复 chapter_directory_dialog.py...")
with open("ui/chapter_directory_dialog.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = '''                    def update_ui():
                        # 移除初始提示信息
                        if "正在生成章节目录，请稍候..." in self.output_text.get("0.0", "end"):
                            self.output_text.delete("0.0", "end")

                        # 插入新文本
                        self.output_text.insert("end", chunk)'''

new_code = '''                    def update_ui():
                        # 移除初始提示信息
                        if "正在生成章节目录，请稍候..." in self.output_text.get("0.0", "end"):
                            self.output_text.delete("0.0", "end")

                        # 检查是否是章节标题，如果是第一个章节，添加空行分隔
                        if re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', chunk):
                            full_content = self.output_text.get("0.0", "end")
                            # 检查是否已包含章节标题
                            if not re.search(r'第\\s*\\d+\\s*章(?!\\s*单元)', full_content):
                                # 这是第一个章节，添加两个空行与单元信息分隔
                                self.output_text.insert("end", "\\n\\n")

                        # 插入新文本
                        self.output_text.insert("end", chunk)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open("ui/chapter_directory_dialog.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("  chapter_directory_dialog.py 修复完成")
else:
    print("  未找到目标代码")
    # 打印一些上下文帮助调试
    idx = content.find("def update_ui()")
    if idx >= 0:
        print("  Found 'def update_ui()' at position", idx)
        print("  Context:", repr(content[idx:idx+200]))

print("修复完成！")
