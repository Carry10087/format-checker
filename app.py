import sys
import os
import hashlib

# 只有本地直接运行 python app.py 时才自动启动（Streamlit Cloud 不需要）
if len(sys.argv) == 1 and not os.environ.get("STREAMLIT_RUNTIME") and not os.environ.get("STREAMLIT_SHARING"):
    os.environ["STREAMLIT_RUNTIME"] = "1"
    import subprocess
    subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", sys.argv[0],
        "--browser.gatherUsageStats", "false",
        "--server.headless", "false"
    ])
    sys.exit()

import streamlit as st
import streamlit.components.v1 as components

# from streamlit_option_menu import option_menu  # 已改用 st.tabs
import re
import json
import requests
import shutil
import base64
from io import BytesIO

# 粘贴按钮组件已移除（会导致弹窗问题）
HAS_PASTE_BUTTON = False

# 默认 API 配置
DEFAULT_API_URL = "https://nvewvip.preview.tencent-zeabur.cn/v1/chat/completions"
DEFAULT_API_KEY = "sk-mw0pY9ILORPwuDBab3CYIzgnJLZO4zgj0kYn7wJ8NVOZjpi"
DEFAULT_MODEL = "gemini-3-flash-preview-maxthinking-search"

# 用户数据目录
USERS_DIR = "users"
USERS_FILE = "users.json"
DEFAULT_RULES_FILE = "format_rules.md"

# ==================== 用户管理系统 ====================

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """加载用户列表"""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """保存用户列表"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def create_user_dir(username):
    """创建用户目录并初始化文件"""
    user_dir = os.path.join(USERS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    
    # 初始化用户的规则文件（从默认规则复制）
    user_rules = os.path.join(user_dir, "rules.md")
    if not os.path.exists(user_rules):
        if os.path.exists(DEFAULT_RULES_FILE):
            shutil.copy(DEFAULT_RULES_FILE, user_rules)
        else:
            with open(user_rules, "w", encoding="utf-8") as f:
                f.write("# 格式规范\n\n请在此添加您的格式规范...")
    
    # 初始化用户的历史记录
    user_history = os.path.join(user_dir, "history.json")
    if not os.path.exists(user_history):
        with open(user_history, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    return user_dir

def register_user(username, password):
    """注册新用户"""
    users = load_users()
    if username in users:
        return False, "用户名已存在"
    if len(username) < 2:
        return False, "用户名至少2个字符"
    if len(password) < 4:
        return False, "密码至少4个字符"
    
    import datetime as dt_module
    users[username] = {
        "password": hash_password(password),
        "created_at": dt_module.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    create_user_dir(username)
    return True, "注册成功"

def login_user(username, password):
    """用户登录"""
    users = load_users()
    if username not in users:
        return False, "用户不存在"
    if users[username]["password"] != hash_password(password):
        return False, "密码错误"
    return True, "登录成功"

def get_user_rules_file(username):
    """获取用户的规则文件路径"""
    return os.path.join(USERS_DIR, username, "rules.md")

def get_user_history_file(username):
    """获取用户的历史记录文件路径"""
    return os.path.join(USERS_DIR, username, "history.json")

def get_user_config_file(username):
    """获取用户的配置文件路径"""
    return os.path.join(USERS_DIR, username, "config.json")

# ==================== 文件操作（基于当前用户）====================

def load_user_config():
    """读取当前用户的 API 配置"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return {"api_url": DEFAULT_API_URL, "api_key": DEFAULT_API_KEY, "model": DEFAULT_MODEL}
    try:
        config_file = get_user_config_file(st.session_state.current_user)
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {
                "api_url": config.get("api_url", DEFAULT_API_URL),
                "api_key": config.get("api_key", DEFAULT_API_KEY),
                "model": config.get("model", DEFAULT_MODEL)
            }
    except:
        return {"api_url": DEFAULT_API_URL, "api_key": DEFAULT_API_KEY, "model": DEFAULT_MODEL}

def save_user_config(api_url, api_key, model):
    """保存当前用户的 API 配置"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return False
    try:
        config_file = get_user_config_file(st.session_state.current_user)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"api_url": api_url, "api_key": api_key, "model": model}, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def save_user_config_full(config):
    """保存当前用户的完整 API 配置（包含多个模型）"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return False
    try:
        config_file = get_user_config_file(st.session_state.current_user)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_history():
    """读取当前用户的历史记录"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return []
    try:
        history_file = get_user_history_file(st.session_state.current_user)
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    """保存当前用户的历史记录"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return
    try:
        history_file = get_user_history_file(st.session_state.current_user)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_rules():
    """读取当前用户的格式规范"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        # 未登录时读取默认规则
        try:
            with open(DEFAULT_RULES_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return ""
    try:
        rules_file = get_user_rules_file(st.session_state.current_user)
        with open(rules_file, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def save_rules(content):
    """保存当前用户的格式规范"""
    if "current_user" not in st.session_state or not st.session_state.current_user:
        return False
    try:
        rules_file = get_user_rules_file(st.session_state.current_user)
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except:
        return False

# 解析规则文件为章节
def parse_rules_sections(content):
    sections = {}
    if not content:
        return sections
    
    lines = content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        if line.startswith('## ') and not line.startswith('### '):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

# 将章节重新组合为完整内容
def rebuild_rules(title, sections, section_order):
    content = f"# {title}\n\n"
    for section_name in section_order:
        if section_name in sections:
            content += f"## {section_name}\n\n{sections[section_name]}\n\n---\n\n"
    return content.rstrip('\n---\n\n').rstrip('\n')

# 实际使用的 4 步 prompts
STEP_PROMPTS = [
    # Step 1: 前置检查与场景识别
    """## Step 1: 前置检查与场景识别

## 待检查的回答
{text}

## 相关规则
{rules_section}

## 参考笔记
{ref_notes}

---

### 任务一：前置检查
依次检查以下三项，**只有这三项不通过才终止**，其他格式/内容问题在后续步骤修改：

| 检查项 | 判断标准 |
|--------|----------|
| 安全红线 | 色情低俗（性器官代称、性暗示、擦边、物化性别）、政治敏感（分裂国家、恐怖主义、民族歧视、否定历史）、违法犯罪（暴力教唆、黑产诈骗、赌博、毒品暗号如"叶子""邮票""飞行"）、伪科学谣言 |
| 丢弃判断 | 非英语Query、多模态依赖（meme/壁纸/穿搭图等用户想"看到"而非"了解"）、纯营销、高度时效性（实时股价/汇率/天气） |
| 无答案终止 | 意图不明、参考材料无相关内容 |

### 任务二：场景识别
从以下场景中选择最匹配的一个，并说明该场景的核心检查重点：

| 场景类型 | 特征 | 核心检查重点 |
|----------|------|--------------|
| 短答案优先 | 明确问句，15-30词可答 | 首句直接给答案，避免冗余 |
| 实操类 | 菜谱/穿搭/妆教 | 步骤清晰，可操作性强 |
| YMYL | 医疗/法律/金融 | 免责声明，建议咨询专业人士 |
| 玄学命理 | 星座/塔罗/风水 | 娱乐性表述，避免绝对化 |
| 情感共鸣 | 情感倾诉/心理支持 | 共情优先，避免说教 |
| 一般信息类 | 其他知识问答 | 结构清晰，引用规范 |

---

### 输出格式（严格按此格式）

**【前置检查】**
- 安全红线：✅通过 / ❌拒绝：[原因]
- 丢弃判断：✅保留 / ❌丢弃：[原因]
- 无答案检查：✅继续 / ❌终止：[原因]

**【场景识别】**
- 场景类型：[选择一个]
- 核心检查重点：[该场景需要特别注意的规则]

**【结论】**
✅ 通过，继续处理 / ❌ 终止：[原因]""",

    # Step 2: 一次性修改并输出终稿
    """## Step 2: 按规则文件修改并输出终稿

## 待修改的回答
{text}

## Step 1 的场景识别结果
{scene_result}

## 参考笔记
{ref_notes}

## 完整规则文件
{rules}

---

### 任务
按【完整规则文件】全面检查并修改，需关注以下所有方面：

**结构与格式：**
- 首段格式（长度、`***`包裹完整性、引号规则）
- 引用位置（移至段末）
- 四级标题结构与内聚性
- 列表格式与层级

**细节与一致性：**
- 粗体使用规范（仅用于列表小标题）
- 短信息合并
- 术语一致性
- 标点符号（引号内标点）
- 反引号改双引号

**内容质量：**
- 禁止重复与冗余
- 标题层级对应
- 内容筛选（匹配优先级、无关内容、跨平台引流）
- 免责声明精准匹配

### 输出要求
1. 直接输出修改后的完整 Markdown 终稿
2. 禁止任何解释、注释、说明
3. 禁止用代码块包裹"""
]

# 翻译 prompt
TRANSLATE_PROMPT = """你是一个专业翻译。请将以下英文内容翻译成简体中文。

【重要】你必须输出中文翻译，不是英文原文！

翻译要求：
1. 将所有英文翻译成流畅的简体中文
2. 保持 Markdown 格式（标题、列表、粗体等）
3. [Note X](#) 引用标记保持原样，不翻译
4. 只输出中文翻译结果，不要任何解释

## 待翻译的英文内容
{text}

## 请输出中文翻译"""

# 2 步名称
STEP_NAMES = [
    "Step 1: 前置检查",
    "Step 2: 修改输出"
]

def call_single_step(prompt, api_url, api_key, model, image_base64=None, max_retries=3):
    """单次 API 调用，支持图片，带重连机制，返回 (content, success, token_usage)"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建消息内容
    if image_base64:
        # 带图片的消息
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
        ]
    else:
        content = prompt
    
    data = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.3
    }
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # 禁用代理直连
            response = requests.post(api_url, headers=headers, json=data, timeout=120, proxies={"http": None, "https": None})
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            if content is None:
                raise ValueError("API 返回内容为空")
            # 提取 token 用量
            usage = result.get("usage", {})
            token_info = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            return content, True, token_info
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # 等待后重试，每次等待时间递增
                import time
                time.sleep(2 * (attempt + 1))
    
    return f"API 调用失败 (重试{max_retries}次后): {str(last_error)}", False, {}

st.set_page_config(page_title="回答格式修改器", layout="wide")

# 隐藏 Streamlit 默认菜单和页脚 + 全局美化样式（暗色科技风）
custom_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

/* 强制 stMain 滚动条始终显示，防止切换 tab 时宽度跳动 */
section[data-testid="stMain"],
.stMain {
    overflow-y: scroll !important;
}

/* 视频背景容器 */
.video-bg {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: -1;
    overflow: hidden;
}
.video-bg video {
    min-width: 100%;
    min-height: 100%;
    width: auto;
    height: auto;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    object-fit: cover;
}
/* 视频上的暗色遮罩 */
.video-bg::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 15, 26, 0.7);
}

/* 暗色科技风背景（视频加载失败时的备用） */
.stApp {
    background: transparent;
}

/* 主容器 - 毛玻璃卡片 */
.main .block-container {
    background: rgba(22, 27, 45, 0.75);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 20px;
    padding: 2rem 3rem;
    margin-top: 1rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), 0 0 40px rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.15);
    transition: all 0.4s ease;
    /* 固定宽度，防止切换 tab 时宽度变化 */
    width: 100% !important;
    max-width: 1200px !important;
    min-width: 800px !important;
}
.main .block-container:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 60px rgba(0, 212, 255, 0.15);
    border-color: rgba(0, 212, 255, 0.25);
}

/* 文字颜色 */
.stApp, .stApp p, .stApp span, .stApp label, .stApp div {
    color: #e0e0e0 !important;
}

/* 标题 - 渐变发光 */
h1, h2, h3, .stSubheader {
    background: linear-gradient(135deg, #00d4ff 0%, #8b5cf6 50%, #00ff88 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: none;
    filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.4));
    animation: titleGlow 3s ease-in-out infinite alternate;
}
@keyframes titleGlow {
    from { filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.4)); }
    to { filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.6)); }
}

/* 渐变分隔线 */
hr, .stDivider {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #00d4ff, #8b5cf6, #00d4ff, transparent) !important;
    margin: 1.5rem 0 !important;
}



/* 按钮 - 霓虹效果 + 微交互 */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #8b5cf6 100%);
    color: #0f0f1a !important;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
    position: relative;
    overflow: hidden;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s;
}
.stButton > button:hover::before {
    left: 100%;
}
.stButton > button:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.5), 0 0 50px rgba(139, 92, 246, 0.3);
}
.stButton > button:active {
    transform: scale(0.97) translateY(0);
}

/* Primary 按钮特殊样式 */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
    box-shadow: 0 4px 20px rgba(0, 255, 136, 0.4);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 30px rgba(0, 255, 136, 0.6), 0 0 60px rgba(0, 212, 255, 0.3);
}

/* 按钮组样式 - 相邻按钮 */
[data-testid="column"] + [data-testid="column"] + [data-testid="column"] .stButton > button {
    border-radius: 10px;
}
/* 小按钮样式（新建/重改/删除等） */
.stButton > button:not([kind="primary"]) {
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.3);
    color: #00d4ff !important;
    box-shadow: none;
}
.stButton > button:not([kind="primary"]):hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: #00d4ff;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}

/* 输入框 - 深色风格 + 聚焦动画 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background-color: rgba(15, 15, 26, 0.6) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0, 212, 255, 0.2) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.4), inset 0 0 20px rgba(0, 212, 255, 0.05) !important;
    animation: inputGlow 1.5s ease-in-out infinite alternate;
}
@keyframes inputGlow {
    from { box-shadow: 0 0 15px rgba(0, 212, 255, 0.3), inset 0 0 15px rgba(0, 212, 255, 0.03); }
    to { box-shadow: 0 0 25px rgba(0, 212, 255, 0.5), inset 0 0 25px rgba(0, 212, 255, 0.05); }
}

/* 占位符文字 - 更亮 */
::placeholder {
    color: rgba(160, 160, 160, 0.7) !important;
    opacity: 1 !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: rgba(160, 160, 160, 0.7) !important;
}

/* 移除 stTextInput 外层白色边框 */
.stTextInput > div {
    border: none !important;
    box-shadow: none !important;
}
.stTextInput > div > div {
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    border-radius: 8px !important;
    background-color: rgba(15, 15, 26, 0.8) !important;
    overflow: hidden !important;
}

/* 强制隐藏输入框内部的滚动条 */
.stTextInput input::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
}
.stTextInput > div > div:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}
.stTextInput [data-baseweb="input"],
.stTextInput [data-baseweb="base-input"] {
    background-color: rgba(15, 15, 26, 0.8) !important;
    border-color: rgba(0, 212, 255, 0.3) !important;
}

/* textarea - 单层边框 */
.stTextArea textarea {
    color: #ffffff !important;
    caret-color: #00d4ff !important;
    border: none !important;
    background: transparent !important;
}
.stTextArea [data-baseweb="textarea"],
.stTextArea [data-baseweb="base-input"] {
    background-color: transparent !important;
    border: none !important;
}
.stTextArea > div,
.stTextArea > div > div > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
/* 强制所有 textarea 内部元素透明 */
.stTextArea * {
    background-color: transparent !important;
}
/* 只在最外层容器加边框和背景 */
.stTextArea > div > div {
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    border-radius: 8px !important;
    background-color: rgba(15, 15, 26, 0.8) !important;
    overflow: hidden !important;
}
.stTextArea > div > div:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}

/* ========== 下拉框样式 - 终极修复版 ========== */
/* 0. 下拉框外层容器 */
.stSelectbox {
    background: rgba(15, 15, 26, 0.6) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    transition: all 0.3s ease !important;
}
.stSelectbox:hover {
    border-color: rgba(0, 212, 255, 0.5) !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.2) !important;
}
.stSelectbox:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.3) !important;
}

/* 1. 输入框主体（未展开时） */
.stSelectbox [data-baseweb="select"] {
    background-color: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    color: white !important;
}
.stSelectbox > div,
.stSelectbox > div > div {
    background: transparent !important;
    border: none !important;
}

/* 移除输入框内部所有多余边框 */
.stSelectbox [data-baseweb="select"] * {
    border: none !important;
    outline: none !important;
    background: transparent !important;
}

/* 2. 核心修复：弹出菜单容器（杀死白色背景） */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[role="listbox"] {
    background-color: #161b2d !important;
    background: #161b2d !important;
    border-radius: 8px !important;
    border: 1px solid rgba(0, 212, 255, 0.2) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
}

/* 2.5 核弹级：强制所有弹出层子元素背景 */
[data-baseweb="popover"] *,
[data-baseweb="menu"] *,
[role="listbox"] *,
ul[role="listbox"],
ul[role="listbox"] > li {
    background-color: #161b2d !important;
    background: #161b2d !important;
}

/* 3. 选项列表基础样式 */
[data-baseweb="menu"] li,
[role="option"] {
    background-color: #161b2d !important;
    background: #161b2d !important;
    color: #a0a0a0 !important;
    padding: 10px 14px !important;
    margin: 2px 0 !important;
    border-left: 3px solid transparent !important;
    transition: all 0.2s ease !important;
    font-size: 14px !important;
}

/* 4. 选中项样式 */
[data-baseweb="menu"] li[aria-selected="true"],
[role="option"][aria-selected="true"] {
    background: linear-gradient(90deg, rgba(139, 92, 246, 0.2) 0%, #161b2d 100%) !important;
    background-color: #161b2d !important;
    color: #00d4ff !important;
    border-left-color: #8b5cf6 !important;
    font-weight: 600 !important;
}

/* 5. 鼠标悬停样式 */
[data-baseweb="menu"] li:hover,
[role="option"]:hover {
    background: linear-gradient(90deg, rgba(0, 212, 255, 0.1) 0%, #161b2d 100%) !important;
    color: #ffffff !important;
    border-left-color: #00d4ff !important;
    padding-left: 20px !important;
}

/* 6. 强制内部文字颜色继承 */
[data-baseweb="menu"] div,
[data-baseweb="menu"] span,
[role="option"] div,
[role="option"] span {
    color: inherit !important;
    background: transparent !important;
}

/* 7. 滚动条美化 */
[data-baseweb="menu"]::-webkit-scrollbar {
    width: 4px !important;
}
[data-baseweb="menu"]::-webkit-scrollbar-track {
    background: #161b2d !important;
}
[data-baseweb="menu"]::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.3) !important;
    border-radius: 2px !important;
}

/* 8. 箭头图标颜色 */
.stSelectbox svg {
    fill: #00d4ff !important;
}

/* 通用输入框边框 */
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="textarea"] {
    border-color: rgba(0, 212, 255, 0.3) !important;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="base-input"]:focus-within {
border-color: #00d4ff !important;
}

/* 密码输入框 - 完全扁平化，只保留最外层边框 */
.stTextInput [data-testid="stTextInputRootElement"] {
border: 1px solid rgba(0, 212, 255, 0.3) !important;
border-radius: 8px !important;
background-color: rgba(15, 15, 26, 0.8) !important;
overflow: hidden;
}
.stTextInput [data-testid="stTextInputRootElement"]:focus-within {
border-color: #00d4ff !important;
box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}
/* 核弹级清理：移除所有内层边框和背景 */
.stTextInput [data-testid="stTextInputRootElement"] *,
.stTextInput [data-testid="stTextInputRootElement"] > div,
.stTextInput [data-testid="stTextInputRootElement"] [data-baseweb="input"],
.stTextInput [data-testid="stTextInputRootElement"] [data-baseweb="base-input"] {
border: none !important;
background: transparent !important;
box-shadow: none !important;
outline: none !important;
}
.stTextInput [data-testid="stTextInputRootElement"] input {
border: none !important;
background: transparent !important;
padding-left: 12px !important;
}
/* 眼睛按钮 - 贴边 */
.stTextInput button,
[data-testid="stTextInputRootElement"] button {
background: transparent !important;
border: none !important;
box-shadow: none !important;
outline: none !important;
color: #a0a0a0 !important;
margin-right: 8px !important;
}
.stTextInput button:hover,
[data-testid="stTextInputRootElement"] button:hover {
background: rgba(0, 212, 255, 0.1) !important;
color: #00d4ff !important;
}

/* 展开器 - 毛玻璃卡片 */
.stExpander {
background: rgba(26, 26, 46, 0.6) !important;
backdrop-filter: blur(15px) !important;
-webkit-backdrop-filter: blur(15px) !important;
border: 1px solid rgba(0, 212, 255, 0.15) !important;
border-radius: 12px !important;
transition: all 0.3s ease;
}
.stExpander:hover {
    border-color: rgba(0, 212, 255, 0.3) !important;
    box-shadow: 0 8px 30px rgba(0, 212, 255, 0.15);
    transform: translateY(-2px);
}
/* 展开器内部内容区域 */
.stExpander > div,
.stExpander [data-testid="stExpanderDetails"],
.stExpander details,
.stExpander summary,
[data-testid="stExpander"] > div {
    background: transparent !important;
    border: none !important;
}
.stExpander details > div {
    background: rgba(15, 15, 26, 0.4) !important;
    border-radius: 8px;
    margin-top: 8px;
}

/* 下载按钮 - 改为科技风格 */
.stDownloadButton > button {
    background: linear-gradient(135deg, #00d4ff 0%, #8b5cf6 100%) !important;
    color: #0f0f1a !important;
    border: none !important;
}
.stDownloadButton > button:hover {
    box-shadow: 0 0 25px rgba(0, 212, 255, 0.5) !important;
}

/* 代码块 - 深色背景 */
.stMarkdown pre,
pre,
[data-testid="stMarkdownContainer"] pre {
    background-color: rgba(15, 15, 26, 0.9) !important;
    color: #e0e0e0 !important;
    border: 1px solid rgba(0, 212, 255, 0.2) !important;
    border-radius: 6px !important;
    padding: 12px !important;
}
/* 代码块内的 code 标签 - 无边框 */
.stMarkdown pre code,
pre code,
[data-testid="stMarkdownContainer"] pre code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: #e0e0e0 !important;
}
/* 行内 code - 轻微样式 */
.stMarkdown code:not(pre code),
[data-testid="stMarkdownContainer"] code:not(pre code) {
    background-color: rgba(0, 212, 255, 0.1) !important;
    color: #00d4ff !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
}
/* 代码块内的复制按钮 */
[data-testid="stMarkdownContainer"] pre button,
.stCodeBlock button {
    background: rgba(0, 212, 255, 0.1) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    color: #00d4ff !important;
}

/* 进度条 - 圆角 */
.stProgress > div {
    background: rgba(15, 15, 26, 0.8) !important;
    border-radius: 10px !important;
    overflow: hidden;
}
.stProgress > div > div {
    background: linear-gradient(90deg, #00d4ff, #8b5cf6, #00ff88) !important;
    box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    border-radius: 10px !important;
}

/* ========== 警告框/信息框 - 无边框 ========== */
.stAlert, [data-testid="stAlert"],
.stAlert > div, [data-testid="stAlert"] > div,
.stAlert *, [data-testid="stAlert"] * {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}

/* 标签页容器 - 清除默认背景 + 固定宽度 */
.stTabs {
    background: transparent !important;
    width: 100% !important;
    max-width: 100% !important;
}
.stTabs > div {
    background: transparent !important;
    width: 100% !important;
}
/* 内容面板固定宽度 - 强制所有 tab 内容区域一致 */
.stTabs [data-baseweb="tab-panel"] {
    width: 100% !important;
    min-width: 100% !important;
}
.stTabs [data-baseweb="tab-panel"] > div {
    width: 100% !important;
}
/* 强制 tab-list 容器内的空 div 固定宽度 */
.stTabs > div > div:not([class]),
.stTabs [class*="st-c"] > div:not([class]) {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
}
/* 强制 .st-cd 及其子元素固定宽度 */
[class*="st-cd"],
[class*="st-cd"] > div {
    width: 100% !important;
    min-width: 100% !important;
}

.stTabs::-webkit-scrollbar,
.stTabs > div::-webkit-scrollbar,
.stTabs [data-baseweb="tab-panel"]::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
}
/* 干掉 Streamlit 自带的白色渐变遮罩 */
.stTabs::before,
.stTabs::after,
.stTabs > div::before,
.stTabs > div::after,
.stTabs [class*="st-emotion-cache"]::before,
.stTabs [class*="st-emotion-cache"]::after {
    background-image: none !important;
    background: transparent !important;
    display: none !important;
}

/* 标签页 - 科技风 + 动态效果 */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(15, 15, 26, 0.6);
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
    border-radius: 16px;
    padding: 8px 12px;
    border: 1px solid rgba(0, 212, 255, 0.2);
    gap: 8px;
    justify-content: center;
    position: relative;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    /* 强制隐藏滚动条 */
    overflow: hidden !important;
}

/* 核弹级方案：彻底消灭滚动条 */
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
}

.stTabs [data-baseweb="tab-list"]::before {
    content: '';
    position: absolute;
    top: -2px;
    left: -2px;
    right: -2px;
    bottom: -2px;
    border-radius: 18px;
    background: linear-gradient(90deg, #00d4ff, #8b5cf6, #00ff88, #8b5cf6, #00d4ff);
    background-size: 400% 100%;
    z-index: -1;
    animation: borderFlow 6s linear infinite;
    opacity: 0.6;
}
.stTabs [data-baseweb="tab-list"]::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: 16px;
    background: rgba(15, 15, 26, 0.9);
    z-index: -1;
}
@keyframes borderFlow {
    0% { background-position: 0% 50%; }
    100% { background-position: 400% 50%; }
}
.stTabs [data-baseweb="tab"] {
    color: #a0a0a0 !important;
    font-size: 14px;
    padding: 12px 24px;
    border-radius: 10px;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
/* 未选中标签的下划线动画 */
.stTabs [data-baseweb="tab"]::after {
    content: '';
    position: absolute;
    bottom: 6px;
    left: 50%;
    width: 0;
    height: 2px;
    background: linear-gradient(90deg, #00d4ff, #8b5cf6);
    transition: all 0.3s ease;
    transform: translateX(-50%);
    border-radius: 2px;
}
.stTabs [data-baseweb="tab"]:hover::after {
    width: 60%;
}
/* 悬停效果 */
.stTabs [data-baseweb="tab"]:hover {
    color: #00d4ff !important;
    background: rgba(0, 212, 255, 0.08) !important;
    transform: translateY(-2px);
}
/* 选中状态 - 渐变 + 发光 */
.stTabs [aria-selected="true"] {
    color: #0f0f1a !important;
    background: linear-gradient(135deg, #00d4ff 0%, #8b5cf6 100%) !important;
    border-radius: 10px;
    font-weight: 600;
    box-shadow: 0 0 25px rgba(0, 212, 255, 0.6), 0 4px 15px rgba(139, 92, 246, 0.4);
    transform: scale(1.03);
    animation: tabGlow 0.4s ease-out, tabPulse 2s ease-in-out infinite;
    transition: all 0.3s ease;
}
/* 选中标签悬停效果 */
.stTabs [aria-selected="true"]:hover {
    transform: scale(1.08) !important;
    box-shadow: 0 0 40px rgba(0, 212, 255, 0.8), 0 8px 25px rgba(139, 92, 246, 0.6) !important;
    background: linear-gradient(135deg, #00ff88 0%, #00d4ff 50%, #8b5cf6 100%) !important;
}
.stTabs [aria-selected="true"]::after {
    display: none;
}
/* 选中时的发光动画 */
@keyframes tabGlow {
    0% {
        box-shadow: 0 0 0 rgba(0, 212, 255, 0);
        transform: scale(0.95);
        opacity: 0.8;
    }
    50% {
        box-shadow: 0 0 40px rgba(0, 212, 255, 0.8);
    }
    100% {
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.6), 0 4px 15px rgba(139, 92, 246, 0.4);
        transform: scale(1.03);
        opacity: 1;
    }
}
/* 选中标签持续脉冲 */
@keyframes tabPulse {
    0%, 100% {
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.5), 0 4px 15px rgba(139, 92, 246, 0.3);
    }
    50% {
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.7), 0 4px 20px rgba(139, 92, 246, 0.5);
    }
}
/* 内容区域淡入 */
.stTabs [data-baseweb="tab-panel"] {
    animation: tabFadeIn 0.3s ease-out;
}
@keyframes tabFadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* 登录页面动画 */
.main .block-container {
    animation: pageSlideIn 0.5s ease-out;
}
@keyframes pageSlideIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 内容区域变化过渡 */
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
.stTextArea,
.stTextInput,
.stSelectbox,
.stMarkdown,
.element-container {
    animation: contentFadeIn 0.4s ease-out;
}
@keyframes contentFadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* 按钮点击后内容刷新动画 */
[data-testid="stExpander"],
.stAlert {
    animation: elementPop 0.3s ease-out;
}
@keyframes elementPop {
    from {
        opacity: 0;
        transform: scale(0.95);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

/* 登录卡片发光效果 */
.stForm, [data-testid="stForm"] {
    animation: cardGlow 2s ease-in-out infinite alternate;
}
@keyframes cardGlow {
    from {
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
    }
    to {
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.2), 0 0 60px rgba(139, 92, 246, 0.1);
    }
}

/* 登录/注册按钮特效 */
.stButton > button[kind="primary"] {
    position: relative;
    overflow: hidden;
}
.stButton > button[kind="primary"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: btnShine 2s infinite;
}
@keyframes btnShine {
    0% { left: -100%; }
    50%, 100% { left: 100%; }
}

/* 成功提示动画 */
[data-testid="stAlert"] {
    animation: alertPop 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
@keyframes alertPop {
    from {
        opacity: 0;
        transform: scale(0.8);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

/* 用户名显示动画 */
.stMarkdown h1, .stMarkdown h2, .stTitle {
    animation: titleFadeIn 0.6s ease-out;
}
@keyframes titleFadeIn {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* 退出按钮悬停效果 */
.stButton > button:not([kind="primary"]) {
    transition: all 0.3s ease;
}
.stButton > button:not([kind="primary"]):hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
}

/* 滚动条 - 深色样式 */
::-webkit-scrollbar,
*::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track,
*::-webkit-scrollbar-track {
    background: rgba(15, 15, 26, 0.8);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb,
*::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.4);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover,
*::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 212, 255, 0.6);
}
/* 隐藏某些区域的滚动条 */
.stSelectbox ::-webkit-scrollbar,
[data-baseweb="popover"] ::-webkit-scrollbar {
    width: 4px;
}
[data-baseweb="popover"] ::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.3);
}

/* 隐藏侧边栏滚动条 */
section[data-testid="stSidebar"] {
    overflow: hidden !important;
}
section[data-testid="stSidebar"] > div {
    overflow-y: auto !important;
    scrollbar-width: none !important;  /* Firefox */
    -ms-overflow-style: none !important;  /* IE/Edge */
}
section[data-testid="stSidebar"] > div::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
}

/* 用户信息卡片 */
.user-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: rgba(15, 15, 26, 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 12px;
    transition: all 0.3s ease;
    cursor: default;
}
.user-card:hover {
    border-color: rgba(0, 212, 255, 0.5);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
    transform: translateY(-2px);
}
.user-avatar {
    font-size: 24px;
    animation: avatarPulse 2s ease-in-out infinite;
}
@keyframes avatarPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}
.user-name {
    color: #00d4ff;
    font-weight: 600;
    font-size: 14px;
    text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

/* 下拉框箭头旋转动画 */
.stSelectbox svg {
    transition: transform 0.3s ease;
    color: #00d4ff !important;
}
.stSelectbox:focus-within svg {
    transform: rotate(180deg);
}

/* 加载提示框 - 无边框 */
[data-testid="stSpinner"],
.stSpinner,
div[data-testid="stNotification"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
/* 加载文字 */
[data-testid="stSpinner"] > div,
.stSpinner > div {
    color: #00d4ff !important;
    font-weight: 600;
    font-size: 16px;
    text-shadow: 0 0 15px rgba(0, 212, 255, 0.8), 0 0 30px rgba(139, 92, 246, 0.5);
    animation: textGlow 1.5s ease-in-out infinite alternate;
}
@keyframes textGlow {
    from { 
        text-shadow: 0 0 15px rgba(0, 212, 255, 0.8), 0 0 30px rgba(139, 92, 246, 0.5);
        color: #00d4ff;
    }
    to { 
        text-shadow: 0 0 25px rgba(139, 92, 246, 1), 0 0 40px rgba(0, 212, 255, 0.6);
        color: #8b5cf6;
    }
}
/* 加载圆圈 */
.stSpinner > div > div,
[data-testid="stSpinner"] svg {
    border-color: transparent !important;
    border-top-color: #00d4ff !important;
    border-right-color: #8b5cf6 !important;
    filter: drop-shadow(0 0 10px rgba(0, 212, 255, 0.8));
}

/* Radio 按钮 */
.stRadio > div {
    background: rgba(15, 15, 26, 0.5);
    border-radius: 8px;
    padding: 5px 10px;
}
.stRadio label span {
    color: #a0a0a0 !important;
}
.stRadio [data-checked="true"] span {
    color: #00d4ff !important;
}

/* 容器高度限制区域 */
[data-testid="stVerticalBlock"] > div[style*="height"] {
    background: rgba(15, 15, 26, 0.5);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 8px;
}

/* 文件上传 */
/* 文件上传 - 深色样式 */
[data-testid="stFileUploader"],
[data-testid="stFileUploader"] > div,
[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    background: rgba(15, 15, 26, 0.8) !important;
    background-color: rgba(15, 15, 26, 0.8) !important;
    border-color: rgba(0, 212, 255, 0.3) !important;
}
[data-testid="stFileUploader"] {
    border: 1px dashed rgba(0, 212, 255, 0.3) !important;
    border-radius: 10px;
}
[data-testid="stFileUploaderDropzone"] {
    border: none !important;
}
/* 上传按钮 */
[data-testid="stFileUploader"] button,
[data-testid="stFileUploaderDropzone"] button {
    background: rgba(0, 212, 255, 0.1) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    color: #00d4ff !important;
}
[data-testid="stFileUploader"] button:hover {
    background: rgba(0, 212, 255, 0.2) !important;
}
/* 上传文字 */
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploaderDropzone"] span {
    color: #a0a0a0 !important;
}

/* Caption 文字 */
.stCaption, small {
    color: #666 !important;
}
</style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

# 用 JS 强制覆盖 Streamlit 的 scrollbar-width: thin
st.markdown("""
<script>
(function() {
    const style = document.createElement('style');
    style.textContent = '* { scrollbar-width: auto !important; }';
    document.head.appendChild(style);
    
    // 监听 DOM 变化，持续覆盖
    const observer = new MutationObserver(() => {
        if (!document.head.contains(style)) {
            document.head.appendChild(style);
        }
    });
    observer.observe(document.head, { childList: true });
})();
</script>
""", unsafe_allow_html=True)

# 添加视频背景（使用静态文件服务）
video_html = '''
<div class="video-bg">
    <video autoplay muted loop playsinline>
        <source src="app/static/bg.mp4" type="video/mp4">
    </video>
</div>
'''
st.markdown(video_html, unsafe_allow_html=True)

# 确保用户目录存在
os.makedirs(USERS_DIR, exist_ok=True)

# 初始化登录状态
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "login_mode" not in st.session_state:
    st.session_state.login_mode = "login"  # login 或 register

# ==================== 登录/注册界面 ====================
if not st.session_state.current_user:
    st.title("回答格式修改器")
    st.markdown("---")
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.subheader("用户登录" if st.session_state.login_mode == "login" else "用户注册")
        
        username = st.text_input("用户名", key="auth_username")
        password = st.text_input("密码", type="password", key="auth_password")
        
        col_btn1, col_btn2 = st.columns(2)
        
        if st.session_state.login_mode == "login":
            with col_btn1:
                if st.button("登录", type="primary", use_container_width=True):
                    if username and password:
                        success, msg = login_user(username, password)
                        if success:
                            st.session_state.current_user = username
                            create_user_dir(username)  # 确保用户目录存在
                            # 重置所有数据状态，强制重新加载用户数据
                            st.session_state.history = None
                            st.session_state.user_config = None  # 重新加载用户配置
                            st.session_state.ai_results = []
                            st.session_state.final_result = ""
                            st.session_state.translated_result = ""
                            st.session_state.current_input = ""
                            st.session_state.current_ref = ""
                            st.session_state.is_locked = False
                            st.session_state.current_history_idx = -1
                            st.session_state.detail_edits = []
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("请输入用户名和密码")
            with col_btn2:
                if st.button("去注册", use_container_width=True):
                    st.session_state.login_mode = "register"
                    st.rerun()
        else:
            with col_btn1:
                if st.button("注册", type="primary", use_container_width=True):
                    if username and password:
                        success, msg = register_user(username, password)
                        if success:
                            st.success(msg + "，请登录")
                            st.session_state.login_mode = "login"
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("请输入用户名和密码")
            with col_btn2:
                if st.button("去登录", use_container_width=True):
                    st.session_state.login_mode = "login"
                    st.rerun()
        
        st.markdown("---")
    st.stop()  # 未登录时停止执行后续代码

# ==================== 已登录界面 ====================

# UI布局
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("回答格式修改器")
with col_user:
    # 用户信息卡片
    user_card_html = f'''
    <div class="user-card">
        <div class="user-avatar">👤</div>
        <div class="user-name">{st.session_state.current_user}</div>
    </div>
    '''
    st.markdown(user_card_html, unsafe_allow_html=True)
    if st.button("退出登录", use_container_width=True, key="logout_btn"):
        # 清空所有 session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# 创建标签页（使用原生 st.tabs + CSS 美化）
tab1, tab2, tab3, tab4 = st.tabs(['AI 修改', '独立质检', '规则管理', 'API 配置'])

# 用 session_state 追踪当前 tab（st.tabs 不返回索引，需要在各 tab 内处理）

# 加载用户的 API 配置
if "user_config" not in st.session_state or st.session_state.user_config is None:
    st.session_state.user_config = load_user_config()

# API 配置
with tab4:
    st.subheader("API 配置")
    st.caption("配置会自动保存到您的账户")
    
    # 模型选项列表
    MODEL_OPTIONS = [
        "gemini-3-flash-preview-nothinking-search",
        "gemini-3-flash-preview-maxthinking-search",
        "gemini-3-flash-preview-search",
        "gemini-3-flash-preview-nothinking",
        "gemini-3-flash-preview-maxthinking",
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-3-pro-preview-maxthinking",
        "gemini-3-pro-preview-nothinking",
        "gemini-3-pro-preview-search",
        "claude-opus-4-5",
        "claude-opus-4-5-thinking",
    ]
    
    api_url = st.text_input("API URL", value=st.session_state.user_config.get("api_url", DEFAULT_API_URL), key="api_url_input")
    api_key = st.text_input("API Key", value=st.session_state.user_config.get("api_key", DEFAULT_API_KEY), type="password", key="api_key_input")
    
    st.markdown("---")
    st.markdown("**模型配置**")
    
    # 深度修改模型
    def get_model_index(key, default_model):
        current = st.session_state.user_config.get(key, default_model)
        return MODEL_OPTIONS.index(current) if current in MODEL_OPTIONS else 0
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        model_edit = st.selectbox("深度修改", options=MODEL_OPTIONS, 
                                   index=get_model_index("model_edit", "gemini-3-flash-preview-maxthinking-search"),
                                   key="model_edit_select", help="AI修改功能使用")
        model_translate = st.selectbox("翻译", options=MODEL_OPTIONS,
                                        index=get_model_index("model_translate", "gemini-3-flash-preview-nothinking"),
                                        key="model_translate_select", help="翻译功能使用")
    with col_m2:
        model_qc = st.selectbox("AI质检", options=MODEL_OPTIONS,
                                 index=get_model_index("model_qc", "gemini-3-pro-preview-search"),
                                 key="model_qc_select", help="AI质检功能使用")
    
    if st.button("保存配置", type="primary"):
        config = {
            "api_url": api_url,
            "api_key": api_key,
            "model_edit": model_edit,
            "model_translate": model_translate,
            "model_qc": model_qc,
            "model_qc_fast": model_qc,  # 兼容旧代码
            "model": model_edit  # 兼容旧代码
        }
        if save_user_config_full(config):
            st.session_state.user_config = config
            st.success("✅ 配置已保存")
        else:
            st.error("❌ 保存失败")
# 初始化 session state
if "ai_results" not in st.session_state:
    st.session_state.ai_results = []
if "final_result" not in st.session_state:
    st.session_state.final_result = ""
if "translated_result" not in st.session_state:
    st.session_state.translated_result = ""
if "history" not in st.session_state or st.session_state.history is None:
    st.session_state.history = load_history()
if "current_input" not in st.session_state:
    st.session_state.current_input = ""
if "current_ref" not in st.session_state:
    st.session_state.current_ref = ""
if "is_locked" not in st.session_state:
    st.session_state.is_locked = False
if "current_history_idx" not in st.session_state:
    st.session_state.current_history_idx = -1  # -1 表示新对话
if "detail_edits" not in st.session_state:
    st.session_state.detail_edits = []  # 细节修改历史记录

# ==================== AI 修改功能 ====================
with tab1:
    st.subheader("AI 自动修改")
    
    # 历史记录切换
    if st.session_state.history:
        # 添加"当前(新)"选项到历史列表
        if st.session_state.current_history_idx == -1:
            history_labels = ["当前(新)"] + [f"#{i+1}: {h['input'][:25]}..." for i, h in enumerate(st.session_state.history)]
            current_index = 0
        else:
            history_labels = [f"#{i+1}: {h['input'][:25]}..." for i, h in enumerate(st.session_state.history)]
            current_index = st.session_state.current_history_idx
        
        # 优化布局：左侧历史记录列表，右侧操作按钮组
        col_hist, col_actions = st.columns([6, 2])
        
        with col_hist:
            selected_idx = st.selectbox(
                "历史记录", 
                range(len(history_labels)), 
                format_func=lambda x: history_labels[x],
                index=current_index,
                key=f"history_select_{st.session_state.current_history_idx}",
                label_visibility="collapsed"
            )
            
        with col_actions:
            # 按钮组紧凑排列
            b_new, b_redo, b_del = st.columns(3, gap="small")
            with b_new:
                new_clicked = st.button("新建", key="new_chat_btn", use_container_width=True)
            with b_redo:
                # 只有选中历史记录时才能重新修改
                can_redo = st.session_state.current_history_idx >= 0
                redo_clicked = st.button("重改", key="redo_chat_btn", disabled=not can_redo, use_container_width=True)
            with b_del:
                # 只有选中历史记录时才能删除
                can_delete = st.session_state.current_history_idx >= 0
                del_clicked = st.button("删除", key="del_chat_btn", disabled=not can_delete, use_container_width=True)
        
        # 处理重新修改按钮
        if redo_clicked and can_redo:
            # 保留输入，清空结果，解锁编辑
            st.session_state.ai_results = []
            st.session_state.final_result = ""
            st.session_state.translated_result = ""
            st.session_state.detail_edits = []
            st.session_state.is_locked = False
            st.rerun()
        
        # 处理删除按钮
        if del_clicked and can_delete:
            del st.session_state.history[st.session_state.current_history_idx]
            save_history(st.session_state.history)
            st.session_state.current_input = ""
            st.session_state.current_ref = ""
            st.session_state.ai_results = []
            st.session_state.final_result = ""
            st.session_state.translated_result = ""
            st.session_state.detail_edits = []
            st.session_state.is_locked = False
            st.session_state.current_history_idx = -1
            st.rerun()
        
        # 处理新对话按钮
        if new_clicked:
            st.session_state.current_input = ""
            st.session_state.current_ref = ""
            st.session_state.ai_results = []
            st.session_state.final_result = ""
            st.session_state.translated_result = ""
            st.session_state.detail_edits = []
            st.session_state.is_locked = False
            st.session_state.current_history_idx = -1
            st.rerun()
        
        # 处理切换历史（只在非新对话模式下）
        if st.session_state.current_history_idx == -1:
            # 新对话模式，选择了历史记录
            if selected_idx > 0:
                real_idx = selected_idx - 1
                h = st.session_state.history[real_idx]
                st.session_state.current_input = h["input"]
                st.session_state.current_ref = h["ref"]
                st.session_state.ai_results = h["results"]
                st.session_state.final_result = h["final"]
                st.session_state.translated_result = h.get("translated", "")
                st.session_state.detail_edits = h.get("detail_edits", [])
                st.session_state.is_locked = True
                st.session_state.current_history_idx = real_idx
                st.rerun()
        else:
            # 历史模式，切换到其他历史
            if selected_idx != st.session_state.current_history_idx:
                h = st.session_state.history[selected_idx]
                st.session_state.current_input = h["input"]
                st.session_state.current_ref = h["ref"]
                st.session_state.ai_results = h["results"]
                st.session_state.final_result = h["final"]
                st.session_state.translated_result = h.get("translated", "")
                st.session_state.detail_edits = h.get("detail_edits", [])
                st.session_state.is_locked = True
                st.session_state.current_history_idx = selected_idx
                st.rerun()
    
    # 输入区域 - 使用动态 key 让内容随切换更新
    input_key = f"ai_input_{st.session_state.current_history_idx}"
    ref_key = f"ref_notes_{st.session_state.current_history_idx}"
    
    col_input, col_ref = st.columns(2)
    with col_input:
        ai_input = st.text_area("输入待修改的回答", height=250, 
                                value=st.session_state.current_input,
                                placeholder="粘贴需要 AI 修改的回答...", 
                                key=input_key,
                                disabled=st.session_state.is_locked)
    with col_ref:
        ref_notes = st.text_area("参考笔记（可选）", height=250, 
                                 value=st.session_state.current_ref,
                                 placeholder="粘贴参考笔记，AI 会根据笔记内容辅助修改...", 
                                 key=ref_key,
                                 disabled=st.session_state.is_locked)

    if st.button("🚀 开始修改", type="primary", use_container_width=True, disabled=st.session_state.is_locked):
        if ai_input.strip():
            # 从 session_state 获取 API 配置
            user_cfg = st.session_state.user_config
            api_url = user_cfg.get("api_url", DEFAULT_API_URL)
            api_key = user_cfg.get("api_key", DEFAULT_API_KEY)
            model = user_cfg.get("model_edit", user_cfg.get("model", DEFAULT_MODEL))
            
            if not api_key:
                st.error("请先在 API 配置中设置 API Key")
            else:
                rules = load_rules()
                if not rules:
                    st.error("无法读取 format_rules.md 文件")
                else:
                    st.session_state.ai_results = []
                    st.session_state.final_result = ""
                    st.session_state.total_tokens = {"prompt": 0, "completion": 0, "total": 0}
                    
                    # 显示处理中警告 - 美化版（使用 st.empty 动态更新）
                    progress_card = st.empty()
                    
                    def render_progress_card(current_step, step_text, progress_pct, is_done=False, is_warning=False):
                        """渲染进度卡片"""
                        # 生成步骤圆点的class（2步）
                        dot_classes = []
                        for j in range(2):
                            if j < current_step:
                                dot_classes.append('done')
                            elif j == current_step and not is_done:
                                dot_classes.append('active')
                            else:
                                dot_classes.append('')
                        
                        # 进度条宽度
                        fill_width = 100 if is_done else progress_pct
                        
                        # 状态文字和颜色
                        if is_done:
                            status_color = '#00ff88'
                            status_bg = 'linear-gradient(90deg,rgba(0,255,136,0.15),rgba(0,212,255,0.15))'
                            status_border = 'rgba(0,255,136,0.4)'
                            status_icon = '\u2705'
                        elif is_warning:
                            status_color = '#ffc107'
                            status_bg = 'rgba(255,193,7,0.15)'
                            status_border = 'rgba(255,193,7,0.4)'
                            status_icon = '\u26a0\ufe0f'
                        else:
                            status_color = '#00d4ff'
                            status_bg = 'rgba(0,212,255,0.1)'
                            status_border = 'rgba(0,212,255,0.3)'
                            status_icon = ''
                        
                        progress_card.markdown(f'''
                        <div class="processing-overlay">
                            <div class="processing-card">
                                <div class="warning-banner">
                                    <span class="warning-icon">⚙️</span>
                                    <span class="warning-text">正在处理中，请勿切换页面或点击其他按钮，否则会中断处理！</span>
                                </div>
                                <div class="step-info">{status_icon} {step_text}</div>
                                <div class="progress-container">
                                    <div class="progress-track">
                                        <div class="progress-fill" style="width:{fill_width}%;"></div>
                                    </div>
                                </div>
                                <div class="step-dots">
                                    <div class="step-dot {dot_classes[0]}"><span>1</span></div>
                                    <div class="step-dot {dot_classes[1]}"><span>2</span></div>
                                </div>
                                <div class="step-labels">
                                    <span>前置检查</span>
                                    <span>修改输出</span>
                                </div>
                            </div>
                        </div>
                        <style>
                        .processing-overlay {{ padding: 1rem 0; }}
                        .processing-card {{
                            background: linear-gradient(135deg, rgba(15, 15, 35, 0.95) 0%, rgba(25, 25, 55, 0.95) 100%);
                            border: 2px solid transparent;
                            border-radius: 16px;
                            padding: 1.5rem 2rem;
                            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 40px rgba(0, 212, 255, 0.1);
                            position: relative;
                            background-clip: padding-box;
                        }}
                        .processing-card::before {{
                            content: '';
                            position: absolute;
                            top: -2px; left: -2px; right: -2px; bottom: -2px;
                            background: linear-gradient(90deg, #00d4ff, #8b5cf6, #00ff88, #00d4ff);
                            background-size: 300% 100%;
                            border-radius: 18px;
                            z-index: -1;
                            animation: borderGlow 3s linear infinite;
                        }}
                        @keyframes borderGlow {{ 0% {{ background-position: 0% 50%; }} 100% {{ background-position: 300% 50%; }} }}
                        .warning-banner {{
                            background: linear-gradient(90deg, rgba(139, 92, 246, 0.15) 0%, rgba(0, 212, 255, 0.1) 100%);
                            border: 1px solid rgba(139, 92, 246, 0.3);
                            border-radius: 10px;
                            padding: 0.75rem 1rem;
                            display: flex;
                            align-items: center;
                            gap: 0.75rem;
                            margin-bottom: 1.5rem;
                        }}
                        .warning-icon {{ font-size: 1.25rem; animation: spin 2s linear infinite; }}
                        @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
                        .warning-text {{ color: #a78bfa !important; font-weight: 500; font-size: 0.95rem; }}
                        .step-info {{
                            text-align: center;
                            font-size: 1.1rem;
                            color: {status_color} !important;
                            font-weight: 600;
                            margin-bottom: 1.25rem;
                            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
                        }}
                        .progress-container {{ margin-bottom: 1.5rem; }}
                        .progress-track {{
                            height: 8px;
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 10px;
                            overflow: hidden;
                        }}
                        .progress-fill {{
                            height: 100%;
                            background: linear-gradient(90deg, #00d4ff 0%, #8b5cf6 50%, #00ff88 100%);
                            border-radius: 10px;
                        }}
                        .step-dots {{
                            display: flex;
                            justify-content: space-between;
                            padding: 0 10%;
                            margin-bottom: 0.5rem;
                        }}
                        .step-dot {{
                            width: 36px; height: 36px;
                            border-radius: 50%;
                            background: rgba(255, 255, 255, 0.1);
                            border: 2px solid rgba(255, 255, 255, 0.2);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }}
                        .step-dot span {{ color: rgba(255, 255, 255, 0.5) !important; font-weight: 600; font-size: 0.9rem; }}
                        .step-dot.active {{
                            background: linear-gradient(135deg, #00d4ff 0%, #8b5cf6 100%);
                            border-color: transparent;
                            box-shadow: 0 0 20px rgba(0, 212, 255, 0.6);
                            animation: dotPulse 1.5s ease-in-out infinite;
                        }}
                        .step-dot.active span {{ color: white !important; }}
                        .step-dot.done {{
                            background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
                            border-color: transparent;
                            box-shadow: 0 0 15px rgba(0, 255, 136, 0.4);
                        }}
                        .step-dot.done span {{ color: white !important; }}
                        @keyframes dotPulse {{ 0%, 100% {{ transform: scale(1); }} 50% {{ transform: scale(1.1); }} }}
                        .step-labels {{
                            display: flex;
                            justify-content: space-between;
                            padding: 0 5%;
                        }}
                        .step-labels span {{ color: rgba(255, 255, 255, 0.5) !important; font-size: 0.8rem; text-align: center; width: 80px; }}
                        </style>
                        ''', unsafe_allow_html=True)
                    
                    # 初始渲染
                    render_progress_card(0, '准备开始...', 0)
                    
                    # 提取规则章节用于前置检查和场景识别（兼容带括号和不带括号的章节名）
                    precheck_parts = []
                    for section_name in ["## 4. 内容安全红线 (0容忍)", "## 4. 内容安全红线"]:
                        if section_name in rules:
                            precheck_parts.append(rules.split(section_name)[1].split("## 5.")[0])
                            break
                    for section_name in ["## 5. 丢弃与过滤标准"]:
                        if section_name in rules:
                            precheck_parts.append(rules.split(section_name)[1].split("## 6.")[0])
                            break
                    for section_name in ["## 6. 无答案终止协议"]:
                        if section_name in rules:
                            precheck_parts.append(rules.split(section_name)[1].split("## 7.")[0])
                            break
                    
                    scene_content = ""
                    for section_name in ["## 3. 场景具体细则 (SOP)", "## 3. 场景具体细则"]:
                        if section_name in rules:
                            scene_content = rules.split(section_name)[1].split("## 4.")[0]
                            break
                    
                    rules_sections = {
                        "precheck": "\n\n".join(precheck_parts),
                        "scene": scene_content,
                    }
                    
                    scene_result = ""
                    for i, step_name in enumerate(STEP_NAMES):
                        # 更新进度卡片
                        progress_pct = int((i + 1) / len(STEP_NAMES) * 100)
                        render_progress_card(i, f'正在执行: {step_name}...', progress_pct)
                        
                        # Step 1: 前置检查与场景识别
                        if i == 0:
                            combined_rules = rules_sections.get("precheck", "") + "\n\n" + rules_sections.get("scene", "")
                            prompt = STEP_PROMPTS[i].format(text=ai_input, rules_section=combined_rules, ref_notes=ref_notes if ref_notes.strip() else "无")
                        # Step 2: 一次性修改并输出终稿
                        elif i == 1:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, scene_result=scene_result, rules=rules, ref_notes=ref_notes if ref_notes.strip() else "无")
                        
                        result, success, token_info = call_single_step(prompt, api_url, api_key, model)
                        st.session_state.ai_results.append({"step": step_name, "result": result, "success": success, "tokens": token_info})
                        # 累计 token 用量
                        if "total_tokens" not in st.session_state:
                            st.session_state.total_tokens = {"prompt": 0, "completion": 0, "total": 0}
                        st.session_state.total_tokens["prompt"] += token_info.get("prompt_tokens", 0)
                        st.session_state.total_tokens["completion"] += token_info.get("completion_tokens", 0)
                        st.session_state.total_tokens["total"] += token_info.get("total_tokens", 0)
                        
                        # 保存场景识别结果（Step 1）
                        if i == 0 and success:
                            scene_result = result
                        # 前置检查不通过则终止（Step 1）
                        if i == 0 and success and result and "❌" in result and ("终止" in result or "拒绝" in result or "丢弃" in result):
                            render_progress_card(i, f'在 {step_name} 提前终止', progress_pct, is_warning=True)
                            break
                        # API调用失败则终止后续步骤
                        if not success:
                            render_progress_card(i, f'{step_name} 失败，已终止', progress_pct, is_warning=True)
                            break
                        # 保存最终结果（Step 2）
                        if i == 1 and success:
                            # AI 处理完后，程序兜底修复格式
                            st.session_state.final_result = fix_all_format(result)
                    
                    render_progress_card(2, '处理完成！', 100, is_done=True)
                    
                    # 保存到历史记录
                    st.session_state.detail_edits = []  # 新修改时清空细节修改历史
                    st.session_state.history.append({
                        "input": ai_input,
                        "ref": ref_notes,
                        "results": st.session_state.ai_results.copy(),
                        "final": st.session_state.final_result,
                        "translated": "",
                        "detail_edits": []
                    })
                    save_history(st.session_state.history)
                    st.session_state.current_input = ai_input
                    st.session_state.current_ref = ref_notes
                    st.session_state.is_locked = True
                    st.session_state.current_history_idx = len(st.session_state.history) - 1
                    st.rerun()
        else:
            st.warning("请输入内容")

    # 显示各步骤结果
    if st.session_state.ai_results:
        st.divider()
        # 显示 Token 用量
        if "total_tokens" in st.session_state and st.session_state.total_tokens["total"] > 0:
            tokens = st.session_state.total_tokens
            st.markdown(f"""
            <div style="background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); border-radius: 8px; padding: 10px 15px; margin-bottom: 15px;">
                <span style="color: #00d4ff; font-weight: 500;">📊 Token 用量：</span>
                <span style="color: #fff; margin-left: 10px;">输入: {tokens['prompt']:,}</span>
                <span style="color: #fff; margin-left: 15px;">输出: {tokens['completion']:,}</span>
                <span style="color: #00ff88; margin-left: 15px; font-weight: 600;">总计: {tokens['total']:,}</span>
            </div>
            """, unsafe_allow_html=True)
        for i, item in enumerate(st.session_state.ai_results):
            with st.expander(f"{'✅' if item['success'] else '❌'} {item['step']}", expanded=False):
                st.markdown(item["result"])

    # 最终结果和复制按钮
    if st.session_state.final_result:
        st.divider()
        col_result, col_translate = st.columns(2)
        
        import base64
        
        # 统一按钮样式
        # 增加 body margin:0 防止 iframe 滚动条或截断
        html_style = "<style>body{margin:0;padding:0;overflow:hidden;}button{width:100%;height:40px;padding:0;margin:0;display:block;font-size:14px;color:white;border:none;border-radius:5px;cursor:pointer;line-height:40px;font-family:'Source Sans Pro',sans-serif;transition:0.3s;}button:hover{opacity:0.9;}button:active{transform:scale(0.98);}</style>"
        
        with col_result:
            # 标题栏 + 模式切换
            h_en1, h_en2 = st.columns([3, 1])
            with h_en1:
                st.subheader("修改结果（英文）")
            with h_en2:
                view_mode = st.radio("", ["预览", "编辑"], horizontal=True, key="en_view_mode", label_visibility="collapsed")
            
            # 检查是否有细节修改高亮
            display_content = st.session_state.final_result
            has_highlights = False
            if st.session_state.detail_edits:
                last_edit = st.session_state.detail_edits[-1]
                if "new_content" in last_edit and last_edit["new_content"]:
                    new_content = last_edit["new_content"]
                    if new_content in display_content:
                        display_content = display_content.replace(
                            new_content, 
                            f'<mark style="background-color: #fff3cd;">{new_content}</mark>'
                        )
                        has_highlights = True
            
            if view_mode == "预览":
                with st.container(height=300):
                    if has_highlights:
                        st.caption("💡 黄色高亮为最近修改")
                    st.markdown(display_content, unsafe_allow_html=True)
            else:
                edit_key = f"result_en_edit_{len(st.session_state.detail_edits)}"
                edited_en = st.text_area("英文结果", value=st.session_state.final_result, height=300, 
                                         key=edit_key, label_visibility="collapsed")
                if edited_en != st.session_state.final_result:
                    st.session_state.final_result = edited_en
                    if st.session_state.history and st.session_state.current_history_idx >= 0:
                        st.session_state.history[st.session_state.current_history_idx]["final"] = edited_en
                        save_history(st.session_state.history)
            
            encoded_en = base64.b64encode(st.session_state.final_result.encode('utf-8')).decode('utf-8')
            
            # 复制英文按钮
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            copy_js_en = f'''{html_style}<script>function copyEn(){{const b='{encoded_en}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnEn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnEn').innerText='📋 复制英文',1500);}});}}</script><button id="btnEn" onclick="copyEn()" style="background:linear-gradient(135deg,#00d4ff 0%,#8b5cf6 100%);box-shadow:0 0 15px rgba(0,212,255,0.3);">📋 复制英文</button>'''
            components.html(copy_js_en, height=60)
        
        with col_translate:
            # 标题栏放翻译按钮
            h_c1, h_c2 = st.columns([3, 1])
            with h_c1:
                st.subheader("中文翻译")
            with h_c2:
                translate_clicked = st.button("翻译", use_container_width=True, type="primary", key="trans_btn_header")
            
            cn_key = f"result_cn_{hash(st.session_state.translated_result)}"
            st.text_area("中文结果", value=st.session_state.translated_result, height=300, 
                        key=cn_key, disabled=True, label_visibility="collapsed")
            
            # 复制中文按钮
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            if st.session_state.translated_result:
                encoded_cn = base64.b64encode(st.session_state.translated_result.encode('utf-8')).decode('utf-8')
                copy_js_cn = f'''{html_style}<script>function copyCn(){{const b='{encoded_cn}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnCn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnCn').innerText='📋 复制中文',1500);}});}}</script><button id="btnCn" onclick="copyCn()" style="background:linear-gradient(135deg,#8b5cf6 0%,#00d4ff 100%);box-shadow:0 0 15px rgba(139,92,246,0.3);">📋 复制中文</button>'''
                components.html(copy_js_cn, height=60)
            else:
                st.empty()

            # 处理翻译逻辑
            if translate_clicked:
                # 从 session_state 获取 API 配置
                user_cfg = st.session_state.user_config
                api_url_t = user_cfg.get("api_url", DEFAULT_API_URL)
                api_key_t = user_cfg.get("api_key", DEFAULT_API_KEY)
                model_t = user_cfg.get("model_translate", user_cfg.get("model", DEFAULT_MODEL))
                
                with st.spinner("翻译中，请勿切换页面..."):
                    prompt = TRANSLATE_PROMPT.format(text=st.session_state.final_result)
                    result, success, _ = call_single_step(prompt, api_url_t, api_key_t, model_t)
                    if success:
                        st.session_state.translated_result = result
                        if st.session_state.history and st.session_state.current_history_idx >= 0:
                            st.session_state.history[st.session_state.current_history_idx]["translated"] = result
                            save_history(st.session_state.history)
                        st.rerun()
                    else:
                        st.error(result)
        
        # 细节修改功能
        st.divider()
        with st.expander("细节修改（选中文本后粘贴到下方）", expanded=False):
            col_sel, col_inst = st.columns([1, 1])
            with col_sel:
                selected_text = st.text_area("选中的文本", height=100, placeholder="粘贴你想修改的文本片段...", key="detail_selected")
            with col_inst:
                edit_instruction = st.text_area("修改指令", height=100, placeholder="描述你想如何修改，如：删除概括性段落、改为列表格式...", key="detail_instruction")
            
            if st.button("🔧 AI 细节修改", use_container_width=True, type="primary", key="detail_edit_btn"):
                if selected_text.strip() and edit_instruction.strip():
                    # 从 session_state 获取 API 配置
                    user_cfg = st.session_state.user_config
                    api_url_d = user_cfg.get("api_url", DEFAULT_API_URL)
                    api_key_d = user_cfg.get("api_key", DEFAULT_API_KEY)
                    model_d = user_cfg.get("model", DEFAULT_MODEL)
                    
                    with st.spinner("AI 正在修改，请勿切换页面..."):
                        rules_for_detail = load_rules()
                        detail_prompt = f"""你是一个格式修改助手。用户选中了一段文本，并给出了修改指令。

## 完整文档（上下文）
{st.session_state.final_result}

## 用户选中的文本
{selected_text}

## 用户的修改指令
{edit_instruction}

## 规则文件
{rules_for_detail}

请理解用户的意图：
- 如果用户说"不要这种话"或"删除"，则直接删除该文本，不留任何痕迹
- 如果用户说"改为列表"，则将段落改为列表格式
- 如果用户要求其他修改，按指令执行

输出格式要求：
请按以下格式输出，用分隔符分开两部分：

---NEW_CONTENT_START---
（如果是修改操作，这里写修改后的新内容片段；如果是删除操作，这里留空）
---NEW_CONTENT_END---

---FULL_DOC_START---
（这里输出修改后的完整文档）
---FULL_DOC_END---

注意：
1. 完整文档部分不要有任何标记，保持纯净的Markdown
2. 不要任何解释"""
                        result, success, _ = call_single_step(detail_prompt, api_url_d, api_key_d, model_d)
                        if success:
                            st.success("修改完成！")
                            # 解析返回结果
                            new_content = ""
                            full_doc = result
                            
                            if "---NEW_CONTENT_START---" in result and "---NEW_CONTENT_END---" in result:
                                try:
                                    new_content = result.split("---NEW_CONTENT_START---")[1].split("---NEW_CONTENT_END---")[0].strip()
                                except:
                                    new_content = ""
                            
                            if "---FULL_DOC_START---" in result and "---FULL_DOC_END---" in result:
                                try:
                                    full_doc = result.split("---FULL_DOC_START---")[1].split("---FULL_DOC_END---")[0].strip()
                                except:
                                    full_doc = result
                            
                            # 记录细节修改历史
                            edit_record = {
                                "selected": selected_text,
                                "instruction": edit_instruction,
                                "before": st.session_state.final_result,
                                "after": full_doc,
                                "new_content": new_content  # 记录修改后的新内容用于高亮
                            }
                            st.session_state.detail_edits.append(edit_record)
                            # 更新结果
                            st.session_state.final_result = full_doc
                            if st.session_state.history and st.session_state.current_history_idx >= 0:
                                st.session_state.history[st.session_state.current_history_idx]["final"] = full_doc
                                st.session_state.history[st.session_state.current_history_idx]["detail_edits"] = st.session_state.detail_edits.copy()
                                save_history(st.session_state.history)
                            st.rerun()
                        else:
                            st.error(result)
                else:
                    st.warning("请输入选中的文本和修改指令")
            
            # 显示细节修改历史和撤销按钮
            if st.session_state.detail_edits:
                st.markdown("---")
                col_hist_title, col_undo = st.columns([3, 1])
                with col_hist_title:
                    st.markdown(f"**细节修改历史 ({len(st.session_state.detail_edits)}条)**")
                with col_undo:
                    undo_clicked = st.button("↩️ 撤销上一步", key="undo_detail_btn", use_container_width=True)
                
                for i, edit in enumerate(st.session_state.detail_edits):
                    with st.expander(f"修改 #{i+1}: {edit['instruction'][:30]}...", expanded=False):
                        st.markdown(f"**选中文本**: {edit['selected'][:100]}...")
                        st.markdown(f"**修改指令**: {edit['instruction']}")
                
                # 处理撤销（放在最后执行）
                if undo_clicked and st.session_state.detail_edits:
                    # 获取上一步的修改前内容
                    last_edit = st.session_state.detail_edits.pop()
                    st.session_state.final_result = last_edit["before"]
                    # 更新历史记录
                    if st.session_state.history and st.session_state.current_history_idx >= 0:
                        st.session_state.history[st.session_state.current_history_idx]["final"] = last_edit["before"]
                        st.session_state.history[st.session_state.current_history_idx]["detail_edits"] = st.session_state.detail_edits.copy()
                        save_history(st.session_state.history)
                    st.rerun()

# ==================== 格式质检功能 ====================
# 导入格式修复工具
from format_fixer import fix_all_format, analyze_format_issues

with tab2:
    st.subheader("独立质检")
    
    # 模式选择（简化为两个）
    qc_mode = st.radio(
        "质检模式",
        ["程序自动修复", "AI 质检"],
        horizontal=True,
        key="qc_mode_radio",
        help="程序自动修复：秒级修复格式问题；AI质检：检查格式逻辑+内容准确性"
    )
    
    if qc_mode == "程序自动修复":
        st.caption("⚡ 秒级自动修复：引用格式、空格、句号位置、列表缩进等")
    else:
        st.caption("🤖 AI 检查格式逻辑，有参考笔记时同时检查内容准确性")
    
    # 输入区域
    qc_input = st.text_area("待检查的回答", height=300, 
                            placeholder="粘贴需要质检的回答...", 
                            key="qc_input_area")
    
    # AI质检时显示可选的参考笔记输入
    qc_notes = ""
    if qc_mode == "AI 质检":
        qc_notes = st.text_area("参考笔记（可选）", height=200,
                                placeholder="粘贴参考笔记，有笔记时会同时检查内容准确性...",
                                key="qc_notes_area")
    
    # 程序自动修复模式
    if qc_mode == "程序自动修复":
        col_fix, col_analyze = st.columns(2)
        with col_fix:
            fix_clicked = st.button("⚡ 一键修复格式", type="primary", use_container_width=True, key="auto_fix_btn")
        with col_analyze:
            analyze_clicked = st.button("🔍 分析问题（不修复）", use_container_width=True, key="analyze_btn")
        
        if fix_clicked:
            if qc_input.strip():
                # 自动修复
                fixed_text = fix_all_format(qc_input)
                issues = analyze_format_issues(qc_input)
                
                # 保存结果
                st.session_state.qc_result = fixed_text
                st.session_state.qc_issues = "\n".join([f"- {issue}" for issue in issues]) if issues else "✅ 未发现可自动修复的格式问题"
                st.session_state.qc_tokens = {}
                st.session_state.qc_auto_fixed = True
                st.rerun()
            else:
                st.warning("请输入待检查的回答")
        
        if analyze_clicked:
            if qc_input.strip():
                issues = analyze_format_issues(qc_input)
                if issues:
                    st.markdown("### 📋 发现的问题")
                    for issue in issues:
                        if "需AI判断" in issue:
                            st.warning(f"⚠️ {issue}")
                        else:
                            st.info(f"🔧 {issue}")
                else:
                    st.success("✅ 未发现格式问题")
            else:
                st.warning("请输入待检查的回答")
    
    # AI 质检模式
    elif st.button("🔍 开始AI质检", type="primary", use_container_width=True, key="qc_start_btn"):
        if qc_input.strip():
            # 从 session_state 获取 API 配置
            user_cfg = st.session_state.user_config
            api_url = user_cfg.get("api_url", DEFAULT_API_URL)
            api_key = user_cfg.get("api_key", DEFAULT_API_KEY)
            model = user_cfg.get("model_qc_fast", user_cfg.get("model", DEFAULT_MODEL))
            
            if not api_key:
                st.error("请先在 API 配置中设置 API Key")
            else:
                # 读取规则文件
                try:
                    with open("format_only_rules.md", "r", encoding="utf-8") as f:
                        format_rules = f.read()
                except:
                    format_rules = None
                
                if not format_rules:
                    st.error("无法读取格式规则文件 (format_only_rules.md)")
                else:
                    with st.spinner("正在质检，请勿切换页面..."):
                        # 根据是否有参考笔记构建不同的 prompt（使用程序修复后的文本）
                        if qc_notes.strip():
                            # 有参考笔记：同时检查格式和内容
                            qc_prompt = f"""## 任务：格式+内容质检

你是一个质检员。请**严格**按照规则检查格式问题，并对照参考笔记检查内容准确性。

**重要提醒**：
1. 只检查**真正违反规则**的问题，不要过度挑剔
2. 如果完全符合规范，问题清单写"✅ 未发现问题"，修改后内容**原样输出原文**
3. 不要为了找问题而找问题，没问题就是没问题
4. 以下问题已由程序自动修复，无需检查：引用格式[NoteX]、标点空格、列表缩进、Title Case、中文标点等

## 待检查的回答
{qc_input}

## 参考笔记
{qc_notes}

## 格式规则
{format_rules}

---

## 输出格式（严格按此格式）

---ISSUES_START---
（如果有问题，用表格列出；如果**没有问题**，只写一行：✅ 未发现问题）

| 序号 | 问题类型 | 问题描述 | 对应规则/依据 |
|------|----------|----------|---------------|
| 1 | 格式/内容 | ... | ... |

---ISSUES_END---

---FIXED_START---
（如果有问题：输出修改后的完整 Markdown）
（如果没有问题：**原样输出原文**，一字不改）
（不要任何解释，不要用代码块包裹）
---FIXED_END---
"""
                        else:
                            # 无参考笔记：只检查格式
                            qc_prompt = f"""## 任务：格式质检

你是一个格式规范质检员。请**严格**按照规则检查格式问题。

**重要提醒**：
1. 只检查**真正违反规则**的问题，不要过度挑剔
2. 如果内容完全符合规范，问题清单写"✅ 未发现格式问题"，修改后内容**原样输出原文**
3. 不要为了找问题而找问题，没问题就是没问题
4. 以下问题已由程序自动修复，无需检查：引用格式[NoteX]、标点空格、列表缩进、Title Case、中文标点等

## 待检查的回答
{qc_input}

## 格式规则
{format_rules}

---

## 输出格式（严格按此格式）

---ISSUES_START---
（如果有问题，用表格列出；如果**没有问题**，只写一行：✅ 未发现格式问题）

| 序号 | 问题描述 | 对应规则 |
|------|----------|----------|
| 1 | ... | ... |

---ISSUES_END---

---FIXED_START---
（如果有问题：输出修改后的完整 Markdown）
（如果没有问题：**原样输出原文**，一字不改）
（不要任何解释，不要用代码块包裹）
---FIXED_END---
"""
                        result, success, token_info = call_single_step(qc_prompt, api_url, api_key, model)
                        if success:
                            # 解析问题清单和修改后的内容
                            issues = ""
                            fixed = result
                            
                            if "---ISSUES_START---" in result and "---ISSUES_END---" in result:
                                try:
                                    issues = result.split("---ISSUES_START---")[1].split("---ISSUES_END---")[0].strip()
                                except:
                                    issues = ""
                            
                            if "---FIXED_START---" in result and "---FIXED_END---" in result:
                                try:
                                    fixed = result.split("---FIXED_START---")[1].split("---FIXED_END---")[0].strip()
                                except:
                                    fixed = result
                            
                            # AI 处理完后，程序再执行格式修复（兜底）
                            fixed = fix_all_format(fixed)
                            
                            st.session_state.qc_issues = issues
                            st.session_state.qc_result = fixed
                            st.session_state.qc_tokens = token_info
                            st.session_state.qc_auto_fixed = False
                            st.rerun()
                        else:
                            st.error(f"质检失败: {result}")
        else:
            st.warning("请输入待检查的回答")
    
    # 显示质检结果
    if "qc_result" in st.session_state and st.session_state.qc_result:
        st.divider()
        
        # 显示修复来源标识
        if st.session_state.get("qc_auto_fixed", False):
            st.success("⚡ 程序自动修复完成")
        
        # 显示 Token 用量（仅AI质检）
        if "qc_tokens" in st.session_state and st.session_state.qc_tokens.get("total_tokens", 0) > 0:
            tokens = st.session_state.qc_tokens
            st.markdown(f"""
            <div style="background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); border-radius: 8px; padding: 10px 15px; margin-bottom: 15px;">
                <span style="color: #00d4ff; font-weight: 500;">📊 Token 用量：</span>
                <span style="color: #fff; margin-left: 10px;">输入: {tokens.get('prompt_tokens', 0):,}</span>
                <span style="color: #fff; margin-left: 15px;">输出: {tokens.get('completion_tokens', 0):,}</span>
                <span style="color: #00ff88; margin-left: 15px; font-weight: 600;">总计: {tokens.get('total_tokens', 0):,}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # 显示问题清单
        if "qc_issues" in st.session_state and st.session_state.qc_issues:
            with st.expander("📋 发现的问题", expanded=True):
                st.markdown(st.session_state.qc_issues)
        
        # 英文结果和中文翻译并排显示
        col_en, col_cn = st.columns(2)
        
        with col_en:
            st.subheader("英文结果")
            # 预览/编辑模式切换
            qc_view_mode = st.radio("", ["预览", "编辑"], horizontal=True, key="qc_view_mode", label_visibility="collapsed")
            
            if qc_view_mode == "预览":
                with st.container(height=400):
                    st.markdown(st.session_state.qc_result)
                copy_content = st.session_state.qc_result
            else:
                edited_qc = st.text_area("编辑结果", value=st.session_state.qc_result, height=400, key="qc_edit_area", label_visibility="collapsed")
                if edited_qc != st.session_state.qc_result:
                    st.session_state.qc_result = edited_qc
                copy_content = edited_qc
            
            # 复制按钮 - 使用当前显示的内容
            import streamlit.components.v1 as components
            encoded_qc = base64.b64encode(copy_content.encode('utf-8')).decode('utf-8')
            html_style = "<style>body{margin:0;padding:0;overflow:hidden;}button{width:100%;height:40px;padding:0;margin:0;display:block;font-size:14px;color:white;border:none;border-radius:5px;cursor:pointer;line-height:40px;font-family:'Source Sans Pro',sans-serif;transition:0.3s;}button:hover{opacity:0.9;}button:active{transform:scale(0.98);}</style>"
            copy_js_qc = f'''{html_style}<script>function copyQc(){{const b='{encoded_qc}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnQc').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnQc').innerText='📋 复制英文',1500);}});}}</script><button id="btnQc" onclick="copyQc()" style="background:linear-gradient(135deg,#00d4ff 0%,#8b5cf6 100%);box-shadow:0 0 15px rgba(0,212,255,0.3);">📋 复制英文</button>'''
            components.html(copy_js_qc, height=60)
        
        with col_cn:
            st.subheader("中文翻译")
            
            # 初始化翻译结果
            if "qc_translated" not in st.session_state:
                st.session_state.qc_translated = ""
            
            # 翻译按钮
            if st.button("🌐 翻译成中文", key="qc_translate_btn", use_container_width=True):
                user_cfg = st.session_state.user_config
                api_url_t = user_cfg.get("api_url", DEFAULT_API_URL)
                api_key_t = user_cfg.get("api_key", DEFAULT_API_KEY)
                model_t = user_cfg.get("model_translate", "gemini-3-flash-preview-nothinking")
                
                if api_key_t:
                    with st.spinner("正在翻译..."):
                        prompt = f"请将以下英文内容翻译成中文，保持原有格式（Markdown），直接输出翻译结果，不要任何解释：\n\n{st.session_state.qc_result}"
                        result, success, _ = call_single_step(prompt, api_url_t, api_key_t, model_t)
                        if success:
                            st.session_state.qc_translated = result
                            st.rerun()
                        else:
                            st.error(f"翻译失败: {result}")
                else:
                    st.error("请先配置 API Key")
            
            # 显示翻译结果
            if st.session_state.qc_translated:
                with st.container(height=400):
                    st.markdown(st.session_state.qc_translated)
                
                # 复制中文按钮
                encoded_cn = base64.b64encode(st.session_state.qc_translated.encode('utf-8')).decode('utf-8')
                copy_js_cn = f'''{html_style}<script>function copyCn(){{const b='{encoded_cn}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnCn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnCn').innerText='📋 复制中文',1500);}});}}</script><button id="btnCn" onclick="copyCn()" style="background:linear-gradient(135deg,#10b981 0%,#059669 100%);box-shadow:0 0 15px rgba(16,185,129,0.3);">📋 复制中文</button>'''
                components.html(copy_js_cn, height=60)
            else:
                st.info("点击上方按钮翻译成中文")
        
        # 清空按钮
        if st.button("🗑️ 清空结果", key="qc_clear_btn", use_container_width=True):
            st.session_state.qc_result = ""
            st.session_state.qc_issues = ""
            st.session_state.qc_tokens = {}
            st.session_state.qc_translated = ""
            st.rerun()

# ==================== 规则管理功能 ====================
with tab3:
    st.subheader("规则管理")
    
    # 加载规则
    rules_content = load_rules()
    sections = parse_rules_sections(rules_content)
    
    # 获取标题
    title_match = re.match(r'^# (.+)$', rules_content, re.MULTILINE)
    rules_title = title_match.group(1) if title_match else "智能助手回答格式规范"
    
    # 章节顺序
    section_order = list(sections.keys())
    
    # 初始化规则历史（用于撤销）
    if "rules_history" not in st.session_state:
        st.session_state.rules_history = []
    
    # 撤销按钮（如果有历史）
    if st.session_state.rules_history:
        if st.button("↩️ 撤销上次修改", use_container_width=True):
            last_rules = st.session_state.rules_history.pop()
            save_rules(last_rules)
            st.success("✅ 已撤销")
            st.rerun()
    
    # 同步更新规则功能
    with st.expander("同步更新规则", expanded=False):
        st.markdown("从默认规则文件同步最新规则到您的个人规则中。")
        
        # 读取默认规则文件
        try:
            with open(DEFAULT_RULES_FILE, "r", encoding="utf-8") as f:
                default_rules_content = f.read()
            default_available = True
        except Exception as e:
            default_rules_content = ""
            default_available = False
            st.error(f"❌ 无法读取默认规则文件: {e}")
        
        if default_available:
            # 比较当前规则和默认规则
            if rules_content.strip() == default_rules_content.strip():
                st.success("✅ 您的规则已经与默认规则同步，无需更新。")
            else:
                st.warning("⚠️ 您的规则与默认规则存在差异。")
                
                # 显示差异统计
                user_lines = len(rules_content.strip().split('\n'))
                default_lines = len(default_rules_content.strip().split('\n'))
                st.info(f"📊 当前规则: {user_lines} 行 | 默认规则: {default_lines} 行")
                
                # 同步选项
                sync_mode = st.radio(
                    "选择同步方式",
                    ["完全替换（用默认规则覆盖您的规则）", "仅预览（查看默认规则内容）"],
                    key="sync_mode_radio"
                )
                
                if sync_mode == "仅预览（查看默认规则内容）":
                    st.markdown("**默认规则预览：**")
                    with st.container(height=300):
                        st.markdown(default_rules_content)
                
                elif sync_mode == "完全替换（用默认规则覆盖您的规则）":
                    st.markdown("**即将应用的默认规则：**")
                    with st.container(height=200):
                        st.markdown(default_rules_content)
                    
                    # 二次确认
                    st.warning("⚠️ **注意：** 此操作将用默认规则完全替换您当前的规则。您的自定义修改将会丢失（但可以通过撤销恢复）。")
                    
                    confirm_sync = st.checkbox("我理解并确认要同步更新规则", key="confirm_sync_checkbox")
                    
                    if confirm_sync:
                        if st.button("🔄 确认同步", type="primary", use_container_width=True, key="confirm_sync_btn"):
                            # 保存当前规则到历史（用于撤销）
                            st.session_state.rules_history.append(rules_content)
                            st.session_state.rules_history = st.session_state.rules_history[-10:]
                            
                            if save_rules(default_rules_content):
                                st.success('✅ 规则已成功同步更新！可点击顶部"撤销上次修改"恢复。')
                                st.rerun()
                            else:
                                st.error("❌ 同步失败，请稍后重试。")
    
    # AI 辅助修改规则
    with st.expander("AI 辅助修改规则", expanded=False):
        # 初始化图片列表
        if "rule_imgs" not in st.session_state:
            st.session_state.rule_imgs = []
        
        # 显示已有图片（紧凑排列）
        if st.session_state.rule_imgs:
            num = len(st.session_state.rule_imgs)
            # 图片列比例1，空白列比例大，让图片紧凑靠左
            cols = st.columns([1]*num + [12])
            for i, img in enumerate(st.session_state.rule_imgs):
                with cols[i]:
                    st.image(f"data:image/png;base64,{img}", width=80)
                    if st.button("✕", key=f"rm_img_{i}"):
                        st.session_state.rule_imgs.pop(i)
                        st.rerun()
        
        # 输入指令
        ai_instruction = st.text_area("修改指令", height=80, placeholder="输入修改指令...", key="ai_rule_instruction")
        
        # 粘贴图片区域
        if HAS_PASTE_BUTTON:
            paste_result = paste_image_button("📋 粘贴图片", key="paste_rule_img")
            if paste_result.image_data is not None:
                buf = BytesIO()
                paste_result.image_data.save(buf, format='PNG')
                new_img = base64.b64encode(buf.getvalue()).decode('utf-8')
                # 避免重复添加同一张图片
                if new_img not in st.session_state.rule_imgs:
                    st.session_state.rule_imgs.append(new_img)
                    st.rerun()
        else:
            uploaded = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], key="rule_img_upload")
            if uploaded:
                new_img = base64.b64encode(uploaded.read()).decode('utf-8')
                if new_img not in st.session_state.rule_imgs:
                    st.session_state.rule_imgs.append(new_img)
                    st.rerun()
        
        image_base64_list = st.session_state.rule_imgs
        
        if st.button("🚀 AI 执行修改", type="primary", use_container_width=True):
            if ai_instruction.strip():
                # 从用户配置获取 API 参数
                user_cfg = st.session_state.user_config
                api_url = user_cfg.get("api_url", DEFAULT_API_URL)
                api_key = user_cfg.get("api_key", DEFAULT_API_KEY)
                model = user_cfg.get("model", DEFAULT_MODEL)
                
                with st.spinner("AI 正在分析并修改规则，请勿切换页面..."):
                    full_rules = rules_content
                    img_count = len(image_base64_list)
                    image_hint = f"\n\n## 参考图片\n用户上传了{img_count}张参考图片，请结合图片内容理解用户的修改意图。" if img_count > 0 else ""
                    ai_prompt = f"""你是一个规则编辑助手。用户想要修改格式规范文件。

## 当前完整规则文件
{full_rules}

## 用户的修改指令
{ai_instruction}{image_hint}

## 输出格式要求
请按以下格式输出：

---CHANGES_START---
（简要说明你做了哪些修改，用列表形式）
---CHANGES_END---

---RULES_START---
（修改后的完整规则文件）
---RULES_END---"""
                    
                    # 只传第一张图片（API 限制）
                    first_img = image_base64_list[0] if image_base64_list else None
                    result, success, _ = call_single_step(ai_prompt, api_url, api_key, model, image_base64=first_img)
                    if success:
                        # 解析修改说明和规则内容
                        changes = ""
                        new_rules = result
                        if "---CHANGES_START---" in result and "---CHANGES_END---" in result:
                            try:
                                changes = result.split("---CHANGES_START---")[1].split("---CHANGES_END---")[0].strip()
                            except:
                                changes = ""
                        if "---RULES_START---" in result and "---RULES_END---" in result:
                            try:
                                new_rules = result.split("---RULES_START---")[1].split("---RULES_END---")[0].strip()
                            except:
                                new_rules = result
                        
                        st.session_state.ai_full_rule_result = new_rules
                        st.session_state.ai_rule_changes = changes
                    else:
                        st.error(result)
            else:
                st.warning("请输入修改指令")
        
        # 显示 AI 结果
        if "ai_full_rule_result" in st.session_state and st.session_state.ai_full_rule_result:
            st.markdown("---")
            
            # 显示修改说明
            if "ai_rule_changes" in st.session_state and st.session_state.ai_rule_changes:
                st.markdown("**修改内容：**")
                st.info(st.session_state.ai_rule_changes)
            
            st.markdown("** 修改后规则预览：**")
            with st.container(height=200):
                st.markdown(st.session_state.ai_full_rule_result)
            
            col_apply, col_clear = st.columns(2)
            with col_apply:
                if st.button("✅ 应用修改", use_container_width=True, type="primary"):
                    # 保存当前规则到历史（用于撤销，最多保留10条）
                    st.session_state.rules_history.append(rules_content)
                    st.session_state.rules_history = st.session_state.rules_history[-10:]
                    if save_rules(st.session_state.ai_full_rule_result):
                        st.session_state.ai_full_rule_result = ""
                        st.session_state.ai_rule_changes = ""
                        st.session_state.rule_imgs = []  # 清空已上传图片
                        st.success("✅ 规则已更新（可点击撤销恢复）")
                        st.rerun()
                    else:
                        st.error("❌ 保存失败")
            with col_clear:
                if st.button("❌ 放弃", use_container_width=True):
                    st.session_state.ai_full_rule_result = ""
                    st.session_state.ai_rule_changes = ""
                    st.rerun()
    
    st.divider()
    
    operation = st.radio("选择操作", ["查看/编辑章节", "添加新章节", "删除章节"], horizontal=True)
    
    if operation == "查看/编辑章节":
        if sections:
            selected_section = st.selectbox("选择章节", section_order, key="select_section")
            if selected_section:
                st.markdown(f"**当前章节: {selected_section}**")
                edited_content = st.text_area("编辑内容", value=sections[selected_section], height=300, key=f"edit_{selected_section}")
                
                if st.button("保存修改", type="primary"):
                    # 保存当前规则到历史（用于撤销）
                    st.session_state.rules_history.append(rules_content)
                    st.session_state.rules_history = st.session_state.rules_history[-10:]
                    
                    sections[selected_section] = edited_content
                    new_content = rebuild_rules(rules_title, sections, section_order)
                    if save_rules(new_content):
                        st.success(f"✅ 章节 '{selected_section}' 已保存")
                        st.rerun()
                    else:
                        st.error("❌ 保存失败")
        else:
            st.warning("没有找到任何章节")
    
    elif operation == "添加新章节":
        st.markdown("**添加新章节**")
        new_section_name = st.text_input("章节名称（例如: 8. 新增规则）")
        new_section_content = st.text_area("章节内容", height=300, key="new_section")
        
        # 选择插入位置
        insert_positions = ["末尾"] + [f"在 '{s}' 之后" for s in section_order]
        insert_pos = st.selectbox("插入位置", insert_positions)
        
        if st.button("➕ 添加章节", type="primary"):
            if new_section_name and new_section_content:
                # 保存当前规则到历史（用于撤销）
                st.session_state.rules_history.append(rules_content)
                st.session_state.rules_history = st.session_state.rules_history[-10:]
                
                sections[new_section_name] = new_section_content
                if insert_pos == "末尾":
                    section_order.append(new_section_name)
                else:
                    after_section = insert_pos.replace("在 '", "").replace("' 之后", "")
                    idx = section_order.index(after_section) + 1
                    section_order.insert(idx, new_section_name)
                
                new_content = rebuild_rules(rules_title, sections, section_order)
                if save_rules(new_content):
                    st.success(f"✅ 章节 '{new_section_name}' 已添加")
                    st.rerun()
                else:
                    st.error("❌ 保存失败")
            else:
                st.warning("请填写章节名称和内容")
    
    elif operation == "删除章节":
        if sections:
            st.markdown("**删除章节**")
            st.warning("⚠️ 删除后可通过顶部“撤销上次修改”恢复")
            delete_section = st.selectbox("选择要删除的章节", section_order, key="delete_select")
            
            if st.button("🗑️ 删除章节", type="primary"):
                if delete_section in sections:
                    # 保存当前规则到历史（用于撤销）
                    st.session_state.rules_history.append(rules_content)
                    st.session_state.rules_history = st.session_state.rules_history[-10:]
                    
                    del sections[delete_section]
                    section_order.remove(delete_section)
                    new_content = rebuild_rules(rules_title, sections, section_order)
                    if save_rules(new_content):
                        st.success(f"✅ 章节 '{delete_section}' 已删除")
                        st.rerun()
                    else:
                        st.error("❌ 保存失败")
        else:
            st.warning("没有可删除的章节")
    
    # 显示所有章节预览
    st.divider()
    st.markdown("### 所有章节")
    for section_name in section_order:
        with st.expander(f"{section_name}"):
            st.markdown(sections.get(section_name, ""))
    