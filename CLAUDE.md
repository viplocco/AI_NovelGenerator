# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

AI小说生成器是一个基于 Python 的桌面应用程序，使用大语言模型辅助创作小说。它遵循"雪花写作法"，并集成了角色弧光理论和悬念建模。应用程序通过基于向量的语义检索保持长篇写作的连贯性。

## 核心架构

### 入口点
- `main.py` - 创建 CustomTkinter 应用程序实例

### 分层架构

**1. UI 层** ([ui/](ui/))
- 基于 CustomTkinter 的 GUI，包含 24 个模块
- 主入口：`ui/main_window.py` (NovelGeneratorGUI 类)
- 每个功能区在独立的标签页中：
  - 小说管理、参数、设置、目录、角色、摘要、章节
  - UI 特定逻辑在 `ui/generation_handlers.py`

**2. 核心生成层** ([novel_generator/](novel_generator/))
- 将生成逻辑与展示分离
- 关键模块：
  - `architecture.py` / `architecture_wizard.py` - 世界观架构向导
  - `blueprint.py` / `blueprint_stream.py` - 章节目录生成
  - `chapter.py` - 带上下文检索的章节内容生成
  - `finalization.py` - 生成后处理（摘要更新、向量库）
  - `knowledge.py` - 知识库集成
  - `vectorstore_utils.py` - 基于 ChromaDB 的语义搜索
- 公共 API 在 `novel_generator/__init__.py`

**3. 适配器层**
- `llm_adapters.py` - 统一的 LLM 接口，支持 10+ 个提供商
- `embedding_adapters.py` - Embedding 服务适配器
- 支持：OpenAI、DeepSeek、Ollama、Gemini、Azure、硅基流动等

**4. 配置与工具**
- `config_manager.py` - 基于 JSON 的配置，管理 API 密钥
- `prompt_definitions.py` - 集中化的提示词模板（雪花写作法、角色弧光理论）
- `consistency_checker.py` - 质量校验，检测剧情不一致
- `chapter_directory_parser.py` - 解析生成的目录结构

**5. 数据存储**
```
data/novels/{novel_id}/
├── novel_info.json
├── Novel_architecture.txt
├── Novel_directory.txt
├── character_state.txt
├── global_summary.txt
├── plot_arcs.txt
├── 角色库/
├── chapters/
└── vectorstore/  # ChromaDB
```

## 开发命令

### 运行
```bash
# 主应用程序
python main.py

# 安装依赖
pip install -r requirements.txt
```

### 打包（可选）
```bash
pip install pyinstaller
pyinstaller main.spec
```

## 重要架构模式

### 提示词管理
所有提示词集中在 [prompt_definitions.py](prompt_definitions.py) 中，包含以下模板：
- 雪花写作法步骤
- 角色弧光追踪
- 章节结构（承继→发展→铺垫）
- 悬念元素平衡
- 上下文感知生成

### 长篇写作的上下文管理
1. **向量数据库**：ChromaDB 存储生成内容的语义向量
2. **角色状态**：追踪修为、装备、位置
3. **全局摘要**：维护故事弧光进展
4. **相关性检索**：`vectorstore_utils.get_relevant_context_from_vector_store()` 检索语义相似的前文内容

### 配置流程
- 通过 `config_manager.load_config()` 从 `config.json` 加载
- 通过 `create_llm_adapter()` 动态创建 LLM 适配器
- 支持存储在配置中的多个模型配置文件

### UI-后端交互
- UI 事件触发 `ui/generation_handlers.py` 中的方法
- 处理函数调用 `novel_generator` 模块
- 进度更新通过回调返回
- 使用线程实现非阻塞操作

## 关键实现细节

### LLM 适配器模式
每个适配器扩展 `BaseLLMAdapter`，实现 `invoke()` 和 `invoke_stream()` 方法。工厂函数 `create_llm_adapter()` 根据 `interface_format` 选择合适的适配器。

### 章节生成工作流
1. 构建上下文（最近 N 章 + 向量库搜索 + 知识库）
2. 使用 `prompt_definitions.py` 中的提示词生成
3. 用户在 UI 中编辑
4. 定稿更新：全局摘要、角色状态、向量库

### 角色状态过滤
`chapter.py:get_relevant_character_state()` 根据涉及角色智能筛选角色状态，减少长篇小说的 token 使用量。

## 代码风格说明
- 所有 Python 文件指定 UTF-8 编码
- Python 3.9+ 语法
- 代码库中未设置正式的 linting
- 遵循现有的缩进和命名约定
