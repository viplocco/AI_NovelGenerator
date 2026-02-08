@echo off
cd /d "e:\项目文件\个人学习\AI_NovelGenerator"
python test_parser.py > test_output.txt 2>&1
type test_output.txt
