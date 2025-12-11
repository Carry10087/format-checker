import sys
import os
import hashlib

# 只有本地直接运行 python app.py 时才自动启动（Streamlit Cloud 不需要）
if len(sys.argv) == 1 and not os.environ.get("STREAMLIT_RUNTIME") and not os.environ.get("STREAMLIT_SHARING"):
    os.environ["STREAMLIT_RUNTIME"] = "1"
    import subprocess
    subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", sys.argv[0],
        "--browser.gatherUsageStats", "false"
    ])
    sys.exit()

import streamlit as st
import streamlit.components.v1 as components
import re
import json
import requests
import shutil

# 默认 API 配置
DEFAULT_API_URL = "https://apic1.ohmycdn.com/api/v1/ai/openai/cc-omg/v1/chat/completions"
DEFAULT_API_KEY = "sk-qL3MXCaP4e59D683eD3dT3BLbkFJ2Ad098474090476490b1"
DEFAULT_MODEL = "claude-opus-4-5-20251101"

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
    
    users[username] = {
        "password": hash_password(password),
        "created_at": str(os.popen("date /t").read().strip() if os.name == "nt" else os.popen("date").read().strip())
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

# 13个步骤的 prompt 模板（规则从文件读取）
# 合并后的 7 步 prompts
STEP_PROMPTS = [
    # Step 1: 前置检查（安全红线 + 丢弃判断 + 无答案终止）
    """## Step 1: 前置检查
对回答进行三项前置检查，任一不通过则终止。

## 回答
{text}

## 检查规则
{rules_section}

### 检查项
1. **安全红线检查**：是否命中色情低俗、政治敏感、违法犯罪、伪科学谣言等红线？
2. **丢弃判断**：是否属于非英语Query、多模态依赖、纯营销、高度时效性等需丢弃的内容？
3. **无答案终止**：是否意图不明或参考材料无相关内容？

### 输出格式
- 安全红线：✅通过 或 ❌拒绝：[原因]
- 丢弃判断：✅保留 或 ❌丢弃：[原因]
- 无答案检查：✅继续 或 ❌终止：[原因]

**最终结论**：✅全部通过，继续处理 或 ❌终止：[原因]""",

    # Step 2: 场景识别
    """## Step 2: 场景识别
识别回答属于哪种场景，以便后续应用对应规则。

## 回答
{text}

## 场景类型
{rules_section}

### 常见场景
- 短答案优先（明确问句，15-30词可答）
- 实操类（菜谱/穿搭/妆教）
- 医疗/法律/金融（YMYL）
- 玄学与星座命理
- 情感共鸣
- 一般信息类

### 输出格式
**识别场景**：[场景类型]
**适用规则**：[对应的规则要点]""",

    # Step 3: 核心原则检查
    """## Step 3: 核心原则检查
检查回答是否符合核心原则。

## 回答
{text}

## 规则文件
{rules}

### 检查要点（规则1.角色定义与核心原则）
1. 语言一致性：是否全英文回答？有无中文夹杂？
2. 政治正确：提及Taiwan时是否加上China？
3. 用户决策导向：是否给出重点而非简单罗列？
4. 去人机感：是否避免了"Based on the search results"等开场白？是否避免了空洞形容词？

【强制】列出检查的规则条款和结果。
输出格式：
- 规则条款：[引用规则原文] → ✅符合 或 ❌违反：[问题] → [修改为]""",

    # Step 4: 结构格式检查（首段 + 正文 + 列表）
    """## Step 4: 结构格式检查
检查文档的整体结构和格式。

## 回答
{text}

## 规则文件
{rules}

### 检查要点

#### 4.1 首段格式（规则2.1首段）
- 第一段是否概括核心结论、重点前置？
- 核心答案句是否使用 `***text***` 格式？
- 冠词是否在 `***` 内部？句号是否在 `***` 外部？

#### 4.2 正文结构（规则2.1正文分段）
- 是否使用四级标题 `####` 区分板块？
- 【最重要】四级标题后是否直接跟列表？绝对禁止插入概括性段落！
  - 错误：`#### Title` 后跟段落再跟列表
  - 正确：`#### Title` 后直接跟 `- **Point**: content`

#### 4.3 列表规范（规则2.2）
- 并列内容是否使用列表？
- 无序列表是否用 `-` 开头？
- 有序列表是否仅用于有先后顺序的步骤？
- 是否使用 `- **Title**: Content` 格式？

【强制】逐条检查并列出结果。
输出格式：
- 规则条款：[引用规则原文] → ✅符合 或 ❌违反：[问题] → [修改为]""",

    # Step 5: 引用与标点检查
    """## Step 5: 引用与标点检查
检查引用格式和标点符号。

## 回答
{text}

## 规则文件
{rules}

### 检查要点

#### 5.1 引用规范（规则2.3）
1. 格式是否为 `[Note X](#)`？
2. 引用是否紧跟标点后无空格？
3. 【重点】是否有段中引用？引用只能在段落末尾！
   - 错误：`句子1.[Note 1](#) 句子2.`（段中引用）
   - 正确：`句子1. 句子2.[Note 1](#)`（统一放末尾）
4. 同一位置是否超过2个引用堆砌？

#### 5.2 标点规范（规则2.4）
- 四级标题后是否正确使用冒号？（跟列表不加，跟描述加）
- 引号内标点是否正确？

【强制】逐条检查并列出结果。
输出格式：
- 规则条款：[引用规则原文] → ✅符合 或 ❌违反：[问题] → [修改为]""",

    # Step 6: 场景细则与表达检查
    """## Step 6: 场景细则与表达检查
根据场景识别结果检查特殊规则，并检查称呼表达。

## 回答
{text}

## 场景识别结果
{prev_result}

## 规则文件
{rules}

### 检查要点

#### 6.1 场景细则（规则3）
根据识别的场景，检查对应规则：
- 短答案：是否≤30字符？是否独立成立？
- 实操类：是否有可操作步骤？是否用有序列表？
- YMYL：是否有免责声明？
- 玄学类：是否有"仅供娱乐"提示？

#### 6.2 称呼与表达（规则3.8-3.9）
- 是否避免了平台关联称呼（薯宝、家人们等）？
- 是否避免了歧义话术？
- 事实类是否明确说明是事实或观点？

【强制】逐条检查并列出结果。
输出格式：
- 规则条款：[引用规则原文] → ✅符合 或 ❌违反：[问题] → [修改为]""",

    # Step 7: 最终输出
    """## Step 7: 最终输出
执行所有修改建议，并进行最终整体检查。

## 原文
{text}

## 参考笔记
{ref_notes}

## 修改建议（必须全部执行）
{prev_result}

## 完整规则
{rules}

### 任务一：执行所有修改建议
逐条执行上述修改建议，生成初步修改后的文档。

### 任务二：最终整体检查
对修改后的文档进行最终检查，确保以下关键规则无遗漏：

1. **首段格式**：主语在 `***` 外，核心定义在 `***` 内，冠词包含在 `***` 内
2. **引用格式**：必须是 `[Note X](#)` 格式，紧跟标点后无空格
3. **引用位置**：引用只能在段落末尾，不能在段落中间
4. **四级标题**：四级标题后必须直接跟列表（`-` 开头），绝对禁止插入概括性段落
5. **列表格式**：推荐 `- **Title**: Content` 格式
6. **无中文**：确保没有中文字符混入

如果发现任何遗漏问题，直接修正。

### 输出要求
1. 只输出最终修改后的完整内容
2. 不要任何解释、不用代码块包裹
3. 保留 [Note X](#) 格式"""
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

# 合并后的 7 步名称
STEP_NAMES = [
    "Step 1: 前置检查",
    "Step 2: 场景识别",
    "Step 3: 核心原则检查",
    "Step 4: 结构格式检查",
    "Step 5: 引用与标点检查",
    "Step 6: 场景细则与表达检查",
    "Step 7: 最终输出"
]

def call_single_step(prompt, api_url, api_key, model):
    """单次 API 调用"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"], True
    except Exception as e:
        return f"API 调用失败: {str(e)}", False

def call_ai_api_steps(text, rules, api_url, api_key, model, progress_callback=None):
    """分13步调用 API"""
    results = []
    
    # 规则分段（用于前几步的简化检查）
    rules_sections = {
        "safety": "## 4. 内容安全红线 (0容忍)" + rules.split("## 4. 内容安全红线 (0容忍)")[1].split("## 5.")[0] if "## 4. 内容安全红线 (0容忍)" in rules else "",
        "discard": "## 5. 丢弃与过滤标准" + rules.split("## 5. 丢弃与过滤标准")[1].split("## 6.")[0] if "## 5. 丢弃与过滤标准" in rules else "",
        "terminate": "## 6. 无答案终止协议" + rules.split("## 6. 无答案终止协议")[1].split("## 7.")[0] if "## 6. 无答案终止协议" in rules else "",
        "scene": "## 3. 场景具体细则 (SOP)" + rules.split("## 3. 场景具体细则 (SOP)")[1].split("## 4.")[0] if "## 3. 场景具体细则 (SOP)" in rules else "",
    }
    
    scene_result = ""  # 保存场景识别结果
    all_suggestions = []  # 保存所有修改建议
    
    for i, prompt_template in enumerate(STEP_PROMPTS):
        if progress_callback:
            progress_callback(i, STEP_NAMES[i])
        
        # 构建 prompt
        if i == 0:  # 安全红线
            prompt = prompt_template.format(text=text, rules_section=rules_sections.get("safety", ""))
        elif i == 1:  # 丢弃判断
            prompt = prompt_template.format(text=text, rules_section=rules_sections.get("discard", ""))
        elif i == 2:  # 无答案终止
            prompt = prompt_template.format(text=text, rules_section=rules_sections.get("terminate", ""))
        elif i == 3:  # 场景识别
            prompt = prompt_template.format(text=text, rules_section=rules_sections.get("scene", ""))
        elif i == 10:  # 特殊场景检查，需要场景信息
            prompt = prompt_template.format(text=text, prev_result=scene_result)
        elif i == 12:  # 最终输出，需要所有修改建议
            prompt = prompt_template.format(text=text, prev_result="\n\n".join(all_suggestions))
        else:  # Step 5-9, 11-12: 只需要 text
            prompt = prompt_template.format(text=text)
        
        result, success = call_single_step(prompt, api_url, api_key, model)
        results.append({"step": STEP_NAMES[i], "result": result, "success": success})
        
        # 保存场景识别结果
        if i == 3 and success:
            scene_result = result
        
        # 保存修改建议 (Step 5-12)
        if 4 <= i <= 11 and success and "✅" not in result:
            all_suggestions.append(f"### {STEP_NAMES[i]}\n{result}")
        
        # 检查是否需要提前终止 (只在前3步检查)
        if i <= 2 and success and ("❌" in result and ("结束" in result or "拒绝" in result or "丢弃" in result)):
            break
    
    return results

st.set_page_config(page_title="回答格式检查器", layout="wide")

# 隐藏 Streamlit 默认菜单和页脚
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 确保用户目录存在
os.makedirs(USERS_DIR, exist_ok=True)

# 初始化登录状态
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "login_mode" not in st.session_state:
    st.session_state.login_mode = "login"  # login 或 register

# ==================== 登录/注册界面 ====================
if not st.session_state.current_user:
    st.title("📝 回答格式检查器")
    st.markdown("---")
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.subheader("🔐 用户登录" if st.session_state.login_mode == "login" else "📝 用户注册")
        
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
        st.caption("每个用户拥有独立的规则文件和历史记录")
    
    st.stop()  # 未登录时停止执行后续代码

# ==================== 已登录界面 ====================

# UI布局
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("📝 回答格式检查器")
with col_user:
    st.markdown(f"👤 **{st.session_state.current_user}**")
    if st.button("退出登录", use_container_width=True):
        # 清空所有 session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# 创建标签页
tab1, tab2, tab3 = st.tabs(["🤖 AI 修改", "📋 规则管理", "⚙️ API 配置"])

# 加载用户的 API 配置
if "user_config" not in st.session_state or st.session_state.user_config is None:
    st.session_state.user_config = load_user_config()

# API 配置放在第三个标签页
with tab3:
    st.subheader("API 配置")
    st.caption("配置会自动保存到您的账户")
    
    col1, col2 = st.columns(2)
    with col1:
        api_url = st.text_input("API URL", value=st.session_state.user_config.get("api_url", DEFAULT_API_URL), key="api_url_input")
        api_key = st.text_input("API Key", value=st.session_state.user_config.get("api_key", DEFAULT_API_KEY), type="password", key="api_key_input")
    with col2:
        model = st.text_input("模型名称", value=st.session_state.user_config.get("model", DEFAULT_MODEL), key="model_input")
    
    if st.button("💾 保存配置", type="primary"):
        if save_user_config(api_url, api_key, model):
            st.session_state.user_config = {"api_url": api_url, "api_key": api_key, "model": model}
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
            history_labels = ["📝 当前(新)"] + [f"#{i+1}: {h['input'][:25]}..." for i, h in enumerate(st.session_state.history)]
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
                new_clicked = st.button("🆕 新建", key="new_chat_btn", use_container_width=True)
            with b_redo:
                # 只有选中历史记录时才能重新修改
                can_redo = st.session_state.current_history_idx >= 0
                redo_clicked = st.button("🔄 重改", key="redo_chat_btn", disabled=not can_redo, use_container_width=True)
            with b_del:
                # 只有选中历史记录时才能删除
                can_delete = st.session_state.current_history_idx >= 0
                del_clicked = st.button("🗑️ 删除", key="del_chat_btn", disabled=not can_delete, use_container_width=True)
        
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
            if not api_key:
                st.error("请先在侧边栏配置 API Key")
            else:
                rules = load_rules()
                if not rules:
                    st.error("无法读取 format_rules.md 文件")
                else:
                    st.session_state.ai_results = []
                    st.session_state.final_result = ""
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # 提取规则章节用于前置检查和场景识别
                    rules_sections = {
                        "precheck": (
                            (rules.split("## 4. 内容安全红线 (0容忍)")[1].split("## 5.")[0] if "## 4. 内容安全红线 (0容忍)" in rules else "") +
                            (rules.split("## 5. 丢弃与过滤标准")[1].split("## 6.")[0] if "## 5. 丢弃与过滤标准" in rules else "") +
                            (rules.split("## 6. 无答案终止协议")[1].split("## 7.")[0] if "## 6. 无答案终止协议" in rules else "")
                        ),
                        "scene": rules.split("## 3. 场景具体细则 (SOP)")[1].split("## 4.")[0] if "## 3. 场景具体细则 (SOP)" in rules else "",
                    }
                    
                    scene_result = ""
                    all_suggestions = []
                    
                    for i, step_name in enumerate(STEP_NAMES):
                        status_text.info(f"🔄 正在执行: {step_name}...")
                        progress_bar.progress((i) / len(STEP_NAMES))
                        
                        # Step 1: 前置检查（安全+丢弃+终止）
                        if i == 0:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, rules_section=rules_sections.get("precheck", ""))
                        # Step 2: 场景识别
                        elif i == 1:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, rules_section=rules_sections.get("scene", ""))
                        # Step 3-5: 核心原则、结构格式、引用标点检查
                        elif i in [2, 3, 4]:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, rules=rules)
                        # Step 6: 场景细则与表达检查（需要场景识别结果）
                        elif i == 5:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, prev_result=scene_result, rules=rules)
                        # Step 7: 最终输出
                        elif i == 6:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, ref_notes=ref_notes if ref_notes.strip() else "无", prev_result="\n\n".join(all_suggestions), rules=rules)
                        else:
                            prompt = STEP_PROMPTS[i].format(text=ai_input, rules=rules)
                        
                        result, success = call_single_step(prompt, api_url, api_key, model)
                        st.session_state.ai_results.append({"step": step_name, "result": result, "success": success})
                        
                        # 保存场景识别结果（Step 2）
                        if i == 1 and success:
                            scene_result = result
                        # 收集修改建议（Step 3-6）
                        if 2 <= i <= 5 and success and ("❌" in result or "修改为" in result or "→" in result):
                            all_suggestions.append(f"### {step_name}\n{result}")
                        # 前置检查不通过则终止（Step 1）
                        if i == 0 and success and "❌" in result and ("终止" in result or "拒绝" in result or "丢弃" in result):
                            status_text.warning(f"⚠️ 在 {step_name} 提前终止")
                            break
                        # 保存最终结果（Step 7）
                        if i == 6:
                            st.session_state.final_result = result
                    
                    progress_bar.progress(1.0)
                    status_text.success("✅ 处理完成！")
                    
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
                st.subheader("📄 修改结果（英文）")
            with h_en2:
                view_mode = st.radio("", ["📖 预览", "✏️ 编辑"], horizontal=True, key="en_view_mode", label_visibility="collapsed")
            
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
            
            if view_mode == "📖 预览":
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
            copy_js_en = f'''{html_style}<script>function copyEn(){{const b='{encoded_en}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnEn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnEn').innerText='📋 复制英文',1500);}});}}</script><button id="btnEn" onclick="copyEn()" style="background:#4CAF50;">📋 复制英文</button>'''
            components.html(copy_js_en, height=60)
        
        with col_translate:
            # 标题栏放翻译按钮
            h_c1, h_c2 = st.columns([3, 1])
            with h_c1:
                st.subheader("🌐 中文翻译")
            with h_c2:
                translate_clicked = st.button("🔄 翻译", use_container_width=True, type="primary", key="trans_btn_header")
            
            cn_key = f"result_cn_{hash(st.session_state.translated_result)}"
            st.text_area("中文结果", value=st.session_state.translated_result, height=300, 
                        key=cn_key, disabled=True, label_visibility="collapsed")
            
            # 复制中文按钮
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            if st.session_state.translated_result:
                encoded_cn = base64.b64encode(st.session_state.translated_result.encode('utf-8')).decode('utf-8')
                copy_js_cn = f'''{html_style}<script>function copyCn(){{const b='{encoded_cn}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnCn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnCn').innerText='📋 复制中文',1500);}});}}</script><button id="btnCn" onclick="copyCn()" style="background:#2196F3;">📋 复制中文</button>'''
                components.html(copy_js_cn, height=60)
            else:
                st.empty()

            # 处理翻译逻辑
            if translate_clicked:
                with st.spinner("翻译中..."):
                    prompt = TRANSLATE_PROMPT.format(text=st.session_state.final_result)
                    result, success = call_single_step(prompt, api_url, api_key, model)
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
        with st.expander("✏️ 细节修改（选中文本后粘贴到下方）", expanded=False):
            col_sel, col_inst = st.columns([1, 1])
            with col_sel:
                selected_text = st.text_area("选中的文本", height=100, placeholder="粘贴你想修改的文本片段...", key="detail_selected")
            with col_inst:
                edit_instruction = st.text_area("修改指令", height=100, placeholder="描述你想如何修改，如：删除概括性段落、改为列表格式...", key="detail_instruction")
            
            if st.button("🔧 AI 细节修改", use_container_width=True, type="primary", key="detail_edit_btn"):
                if selected_text.strip() and edit_instruction.strip():
                    with st.spinner("AI 正在修改..."):
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
                        result, success = call_single_step(detail_prompt, api_url, api_key, model)
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
                    st.markdown(f"**📝 细节修改历史 ({len(st.session_state.detail_edits)}条)**")
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

# ==================== 规则管理功能 ====================
with tab2:
    st.subheader("规则管理")
    
    # 加载规则
    rules_content = load_rules()
    sections = parse_rules_sections(rules_content)
    
    # 获取标题
    title_match = re.match(r'^# (.+)$', rules_content, re.MULTILINE)
    rules_title = title_match.group(1) if title_match else "智能助手回答格式规范"
    
    # 章节顺序
    section_order = list(sections.keys())
    
    # 选择操作
    operation = st.radio("选择操作", ["查看/编辑章节", "添加新章节", "删除章节"], horizontal=True)
    
    if operation == "查看/编辑章节":
        if sections:
            selected_section = st.selectbox("选择章节", section_order, key="select_section")
            if selected_section:
                st.markdown(f"**当前章节: {selected_section}**")
                edited_content = st.text_area("编辑内容", value=sections[selected_section], height=400, key=f"edit_{selected_section}")
                
                if st.button("💾 保存修改", type="primary"):
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
            st.warning("⚠️ 删除操作不可撤销，请谨慎操作")
            delete_section = st.selectbox("选择要删除的章节", section_order, key="delete_select")
            
            if st.button("🗑️ 删除章节", type="primary"):
                if delete_section in sections:
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
    st.markdown("### 📖 所有章节")
    for section_name in section_order:
        with st.expander(f"📑 {section_name}"):
            st.markdown(sections.get(section_name, ""))

