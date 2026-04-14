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
import html
import requests
import shutil
import base64
from io import BytesIO

# 从 api.py 导入 API 配置和函数
from api import (
    DEFAULT_API_URL, DEFAULT_API_KEY, DEFAULT_MODEL,
    DEFAULT_MODEL_EDIT, DEFAULT_MODEL_TRANSLATE, DEFAULT_MODEL_QC, DEFAULT_MODEL_CHAT,
    call_single_step
)

# 粘贴按钮组件已移除（会导致弹窗问题）
HAS_PASTE_BUTTON = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 用户数据目录
USERS_DIR = "users"
USERS_FILE = "users.json"
DEFAULT_RULES_FILE = "format_rules.md"
FORMAT_ONLY_RULES_FILE = os.path.join(BASE_DIR, "format_only_rules.md")
FORMAT_WITH_NOTES_RULES_FILE = os.path.join(BASE_DIR, "format_with_notes_rules.md")
GENERATE_WITH_NOTES_RULES_FILE = os.path.join(BASE_DIR, "generate_with_notes_rules.md")

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


def read_utf8_file(path, default=None):
    """读取 UTF-8 文本文件，失败时返回默认值。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return default


def normalize_note_citations(text):
    """统一 Note 引用格式，修复逗号合并、缺少空格和缺少 (#) 的情况。"""
    if not text:
        return text

    text = text.replace("\r\n", "\n")

    def expand_comma_notes(match):
        content = match.group(1)
        notes = re.findall(r'\d+', content)
        return ''.join(f'[Note {n}](#)' for n in notes)

    # [Note 4, Note 8] / [Note 4, 8] / [Note4,8](#) -> [Note 4](#)[Note 8](#)
    text = re.sub(
        r'\[(Note\s*\d+(?:\s*,\s*(?:Note\s*)?\d+)+)\](?:\(#\))?',
        expand_comma_notes,
        text
    )

    # [Note4] / [Note 4] -> [Note 4](#)
    text = re.sub(r'\[Note\s*(\d+)\](?!\(#\))', r'[Note \1](#)', text)

    # [Note4](#) -> [Note 4](#)
    text = re.sub(r'\[Note(\d+)\]\(#\)', r'[Note \1](#)', text)

    # [Note 12](#)(#) / [Note 12](#) (#) -> [Note 12](#)
    text = re.sub(r'(\[Note\s*\d+\]\(#\))(?:\s*\(#\))+', r'\1', text)

    # [Note 12](#)# 或其他尾随重复片段的保守清理
    text = re.sub(r'(\[Note\s*\d+\]\(#\))(?:(?:\s*\(#\))|(?:\s*#\))|(?:\s*\(#))+', r'\1', text)

    # 连续引用之间不保留空格
    text = re.sub(r'(\[Note\s*\d+\]\(#\))\s+(?=\[Note\s*\d+\]\(#\))', r'\1', text)

    return text


def normalize_quoted_commas(text):
    """将英文内容中紧跟在双引号后的逗号移到引号内。"""
    if not text:
        return text

    return re.sub(r'"([^"\n]+)"\s*,', r'"\1,"', text)


def normalize_notes_generation_output(text):
    """对参考笔记生成结果做轻量格式兜底，避免常见的结构性错误。"""
    if not text:
        return text

    text = text.replace("\r\n", "\n")
    text = normalize_note_citations(text)
    text = normalize_quoted_commas(text)

    def fix_hyphenated_compounds(value):
        def repl(match):
            left, right = match.group(1), match.group(2)

            def normalize_part(part):
                if part.isupper():
                    return part
                return part[:1].upper() + part[1:].lower()

            return f"{normalize_part(left)}-{normalize_part(right)}"

        return re.sub(r'\b([A-Za-z]+)-([A-Za-z]+)\b', repl, value)

    normalized_lines = []
    for line in text.split("\n"):
        if line.startswith("#### "):
            normalized_lines.append("#### " + fix_hyphenated_compounds(line[5:]))
            continue

        list_title_match = re.match(r'^(\s*-\s+\*\*)([^*]+)(\*\*)(:?.*)$', line)
        if list_title_match:
            prefix, title, suffix, rest = list_title_match.groups()
            normalized_lines.append(f"{prefix}{fix_hyphenated_compounds(title)}{suffix}{rest}")
            continue

        normalized_lines.append(line)

    text = "\n".join(normalized_lines)

    text = normalize_markdown_spacing(text)

    return text.strip()


def normalize_markdown_spacing(text):
    """统一 Markdown 间距，按空白行语义规范主要板块的间距。"""
    if not text:
        return text

    text = text.replace("\r\n", "\n")
    text = normalize_note_citations(text)
    raw_lines = text.split("\n")
    normalized = []
    i = 0

    def is_heading(line):
        return bool(re.match(r'^#{1,6} ', line))

    def is_list_item(line):
        return bool(re.match(r'^\s*(?:- |\d+\. )', line))

    while i < len(raw_lines):
        line = raw_lines[i].rstrip()

        if line.strip() == "":
            j = i
            while j < len(raw_lines) and raw_lines[j].strip() == "":
                j += 1

            prev_line = normalized[-1] if normalized else None
            next_line = raw_lines[j].rstrip() if j < len(raw_lines) else None

            if prev_line is not None and next_line is not None:
                # 标题与其下正文/列表之间不留空行
                if is_heading(prev_line):
                    pass
                # 列表与同级下一标题之间、首段与正文之间统一保留两个空白行
                else:
                    normalized.extend(["", ""])

            i = j
            continue

        normalized.append(line)
        i += 1

    # 去掉首尾空白行
    while normalized and normalized[0] == "":
        normalized.pop(0)
    while normalized and normalized[-1] == "":
        normalized.pop()

    return "\n".join(normalized)


COPY_BUTTON_HTML_STYLE = "<style>body{margin:0;padding:4px 0 2px;overflow:hidden;box-sizing:border-box;}button{width:100%;height:40px;padding:0 14px;margin:0;display:block;font-size:14px;font-weight:600;color:#00d4ff;border:1px solid rgba(0,212,255,0.3);border-radius:10px;cursor:pointer;line-height:40px;font-family:'Source Sans Pro',sans-serif;transition:background-color .25s ease,border-color .25s ease,box-shadow .25s ease,transform .25s ease;box-sizing:border-box;}button:hover{background:rgba(0,212,255,0.2)!important;border-color:#00d4ff!important;box-shadow:0 0 20px rgba(0,212,255,0.3)!important;transform:translateY(-2px)!important;}button:active{transform:scale(.97) translateY(-1px)!important;}button:focus{outline:none;}</style>"
EN_COPY_BUTTON_STYLE = "background:rgba(0,212,255,0.1);"
CN_COPY_BUTTON_STYLE = "background:rgba(0,212,255,0.1);"
RESULT_PANEL_HEIGHT = 360
COPY_JS_HELPERS = """
<script>
function copyWithFallback(text, onSuccess, onFail) {
    const fallback = () => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        try {
            const ok = document.execCommand('copy');
            if (ok) {
                onSuccess();
            } else if (onFail) {
                onFail();
            }
        } catch (e) {
            if (onFail) {
                onFail();
            }
        } finally {
            document.body.removeChild(ta);
        }
    };

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(onSuccess).catch(fallback);
    } else {
        fallback();
    }
}
</script>
"""


def render_section_title(title, style="subheader"):
    if style == "markdown":
        st.markdown(f"**{title}**")
    else:
        st.subheader(title)


def render_soft_notice(message, tone="neutral"):
    palettes = {
        "neutral": ("rgba(255,255,255,0.05)", "rgba(255,255,255,0.10)", "#dce4f2"),
        "info": ("rgba(0,212,255,0.08)", "rgba(0,212,255,0.22)", "#d9f8ff"),
        "success": ("rgba(0,255,136,0.08)", "rgba(0,255,136,0.22)", "#dcfff0"),
    }
    background, border, color = palettes.get(tone, palettes["neutral"])
    content = html.escape(message).replace("\n", "<br>")
    st.markdown(
        f"""
        <div style="
            margin: 0.35rem 0 1rem 0;
            padding: 0.75rem 0.95rem;
            border-radius: 12px;
            background: {background};
            border: 1px solid {border};
            color: {color};
            font-size: 0.95rem;
            line-height: 1.65;
        ">{content}</div>
        """,
        unsafe_allow_html=True,
    )


def render_loading_banner(title, detail=""):
    safe_title = html.escape(title)
    safe_detail = html.escape(detail).replace("\n", "<br>") if detail else ""
    detail_html = f'<div class="processing-card__detail">{safe_detail}</div>' if safe_detail else ""
    st.markdown(
        f"""
        <div class="processing-card">
            <div class="processing-card__sheen"></div>
            <div class="processing-card__header">
                <span class="processing-card__pulse"></span>
                <span class="processing-card__title">{safe_title}</span>
            </div>
            {detail_html}
            <div class="processing-card__bar"><span></span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_motion_anchor(anchor_id, delay_ms=0):
    safe_anchor = re.sub(r"\W+", "_", anchor_id)
    components.html(
        f"""
        <script>
        (() => {{
            const iframe = Array.from(window.parent.document.querySelectorAll('iframe'))
                .find((node) => node.contentWindow === window);
            if (!iframe) return;
            const host =
                iframe.closest('[data-testid="column"]') ||
                iframe.parentElement?.closest('[data-testid="stVerticalBlock"]');
            if (!host) return;

            const marker = 'result_motion_{safe_anchor}';
            host.classList.add('result-panel-shell');
            host.style.setProperty('--result-enter-delay', '{delay_ms}ms');
            host.dataset.resultMotion = marker;
            host.classList.remove('result-panel-enter');
            void host.offsetWidth;
            host.classList.add('result-panel-enter');
            window.setTimeout(() => {{
                if (host.dataset.resultMotion === marker) {{
                    host.classList.remove('result-panel-enter');
                }}
            }}, {delay_ms + 900});
        }})();
        </script>
        """,
        height=0,
    )


def should_play_result_motion(state_key, content):
    motion_key = f"{state_key}__motion_signature"
    if not content:
        st.session_state.pop(motion_key, None)
        return False

    signature = hashlib.sha256(content.encode("utf-8")).hexdigest()
    previous_signature = st.session_state.get(motion_key)
    st.session_state[motion_key] = signature
    return previous_signature != signature


def render_copy_button(text, button_id, label, copied_label="已复制", button_style=EN_COPY_BUTTON_STYLE):
    if not text:
        return

    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    js_name = re.sub(r"\W+", "_", button_id)
    copy_js = f"""{COPY_BUTTON_HTML_STYLE}{COPY_JS_HELPERS}<script>function copy_{js_name}(){{const b='{encoded}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);copyWithFallback(t, ()=>{{const btn=document.getElementById('{button_id}');if(btn){{btn.innerText='{copied_label}';setTimeout(()=>btn.innerText='{label}',1500);}}}}, ()=>alert('复制失败'));}}</script><button id="{button_id}" onclick="copy_{js_name}()" style="{button_style}">{label}</button>"""
    components.html(copy_js, height=70)


def render_copy_nearest_textarea_button(button_id, label, copied_label="已复制", button_style=EN_COPY_BUTTON_STYLE):
    js_name = re.sub(r"\W+", "_", button_id)
    copy_js = f"""{COPY_BUTTON_HTML_STYLE}{COPY_JS_HELPERS}<script>function copy_{js_name}(){{const iframes=window.parent.document.querySelectorAll('iframe');let thisIframe=null;for(const f of iframes){{if(f.contentWindow===window){{thisIframe=f;break;}}}}let closest=null;if(thisIframe){{const iRect=thisIframe.getBoundingClientRect();const tas=window.parent.document.querySelectorAll('textarea');let minDist=Infinity;for(const ta of tas){{const tRect=ta.getBoundingClientRect();const dist=Math.abs(tRect.bottom-iRect.top)+Math.abs(tRect.left-iRect.left);if(dist<minDist){{minDist=dist;closest=ta;}}}}}}if(closest&&closest.value!=null){{copyWithFallback(closest.value, ()=>{{const btn=document.getElementById('{button_id}');if(btn){{btn.innerText='{copied_label}';setTimeout(()=>btn.innerText='{label}',1500);}}}}, ()=>alert('复制失败'));return;}}alert('找不到编辑框');}}</script><button id="{button_id}" onclick="copy_{js_name}()" style="{button_style}">{label}</button>"""
    components.html(copy_js, height=70)


def render_markdown_result_column(
    *,
    title,
    content_key,
    view_key,
    edit_key,
    copy_prefix,
    height=320,
    title_style="subheader",
    textarea_label="英文结果",
    copy_label="复制英文",
    on_save=None,
):
    content = st.session_state.get(content_key, "")
    h1, h2 = st.columns([3, 1])
    with h1:
        render_section_title(title, title_style)
    with h2:
        view_mode = st.toggle("预览模式", value=st.session_state.get(view_key, True), key=view_key)

    motion_slot = st.empty()
    content_slot = st.empty()
    copy_slot = st.empty()

    if should_play_result_motion(content_key, content):
        with motion_slot.container():
            render_result_motion_anchor(f"{copy_prefix}_result", delay_ms=0)
    else:
        motion_slot.empty()

    edit_source_key = f"{edit_key}__source"
    edit_widget_key = f"{edit_key}__widget"
    last_view_mode_key = f"{view_key}__last"
    previous_view_mode = st.session_state.get(last_view_mode_key, True)

    if st.session_state.get(edit_source_key) != content:
        st.session_state[edit_widget_key] = content
        st.session_state[edit_source_key] = content

    if previous_view_mode is False and view_mode is True and edit_widget_key in st.session_state:
        latest_value = st.session_state.get(edit_widget_key, "")
        st.session_state[content_key] = latest_value
        st.session_state[edit_source_key] = latest_value
        content = latest_value
        if on_save:
            on_save(latest_value)

    if previous_view_mode is True and view_mode is False:
        st.session_state[edit_widget_key] = content

    if view_mode:
        content_slot.empty()
        copy_slot.empty()
        with content_slot.container():
            with st.container(height=height):
                st.markdown(content)
        with copy_slot.container():
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            render_copy_button(content, f"{copy_prefix}_preview", copy_label, button_style=EN_COPY_BUTTON_STYLE)
    else:
        if edit_widget_key not in st.session_state:
            st.session_state[edit_widget_key] = content

        def handle_edit_save():
            new_value = st.session_state.get(edit_widget_key, "")
            st.session_state[content_key] = new_value
            st.session_state[edit_source_key] = new_value
            if on_save:
                on_save(new_value)

        content_slot.empty()
        copy_slot.empty()
        with content_slot.container():
            st.text_area(
                textarea_label,
                height=height,
                key=edit_widget_key,
                label_visibility="collapsed",
                on_change=handle_edit_save
            )
        with copy_slot.container():
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            render_copy_nearest_textarea_button(f"{copy_prefix}_edit", copy_label, button_style=EN_COPY_BUTTON_STYLE)

    st.session_state[last_view_mode_key] = view_mode


def render_translation_column(
    *,
    source_text,
    translated_key,
    button_key,
    copy_prefix,
    height=320,
    title="中文翻译",
    title_style="subheader",
    empty_caption="点击「翻译」按钮生成中文翻译...",
    copy_label="复制中文",
    on_save=None,
):
    translated_text = st.session_state.get(translated_key, "")
    h1, h2 = st.columns([3, 1])
    with h1:
        render_section_title(title, title_style)
    with h2:
        translate_clicked = st.button("翻译", use_container_width=True, type="primary", key=button_key)

    content_slot = st.empty()
    copy_slot = st.empty()
    translation_updated = False

    if translate_clicked:
        user_cfg = st.session_state.user_config
        api_url_t = user_cfg.get("api_url", DEFAULT_API_URL)
        api_key_t = user_cfg.get("api_key", DEFAULT_API_KEY)
        model_t = user_cfg.get("model_translate", user_cfg.get("model", DEFAULT_MODEL_TRANSLATE))

        if not api_key_t:
            st.error("请先在 API 配置中设置 API Key")
        else:
            previous_translated_text = translated_text
            translated_text = ""
            content_slot.empty()
            with content_slot.container():
                with st.container(height=height):
                    render_loading_banner("正在翻译中文", "请保持当前页面不变，完成后会直接显示结果。")
            copy_slot.empty()

            call_error = ""
            result = ""
            success = False
            try:
                prompt = TRANSLATE_PROMPT.format(text=source_text)
                result, success, _ = call_single_step(prompt, api_url_t, api_key_t, model_t)
            except Exception as exc:
                call_error = str(exc)

            if call_error:
                translated_text = previous_translated_text
                st.error(call_error)
            elif success:
                translated = normalize_markdown_spacing(result)
                st.session_state[translated_key] = translated
                translated_text = translated
                translation_updated = True
                if on_save:
                    on_save(translated)
                play_notification_sound()
            else:
                translated_text = previous_translated_text
                st.error(result)

    if should_play_result_motion(translated_key, translated_text):
        render_result_motion_anchor(f"{copy_prefix}_translation", delay_ms=80 if not translation_updated else 20)

    content_slot.empty()
    with content_slot.container():
        with st.container(height=height):
            if translated_text:
                st.markdown(translated_text)
            else:
                st.caption(empty_caption)

    copy_slot.empty()
    with copy_slot.container():
        st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
        if translated_text:
            render_copy_button(translated_text, f"{copy_prefix}_copy", copy_label, button_style=CN_COPY_BUTTON_STYLE)


def render_dual_result_panels(
    *,
    result_key,
    translated_key,
    result_title,
    result_title_style="subheader",
    result_view_key,
    result_edit_key,
    result_copy_prefix,
    translate_button_key,
    translate_copy_prefix,
    height=320,
    result_textarea_label="英文结果",
    result_copy_label="复制英文",
    translation_title="中文翻译",
    translation_title_style="subheader",
    translation_empty_caption="点击「翻译」按钮生成中文翻译...",
    translation_copy_label="复制中文",
    on_result_save=None,
    on_translation_save=None,
):
    col_result, col_translate = st.columns(2)

    with col_result:
        render_markdown_result_column(
            title=result_title,
            title_style=result_title_style,
            content_key=result_key,
            view_key=result_view_key,
            edit_key=result_edit_key,
            copy_prefix=result_copy_prefix,
            height=height,
            textarea_label=result_textarea_label,
            copy_label=result_copy_label,
            on_save=on_result_save,
        )

    with col_translate:
        render_translation_column(
            source_text=st.session_state.get(result_key, ""),
            translated_key=translated_key,
            button_key=translate_button_key,
            copy_prefix=translate_copy_prefix,
            height=height,
            title=translation_title,
            title_style=translation_title_style,
            empty_caption=translation_empty_caption,
            copy_label=translation_copy_label,
            on_save=on_translation_save,
        )

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
        return {
            "api_url": DEFAULT_API_URL,
            "api_key": DEFAULT_API_KEY,
            "model": DEFAULT_MODEL,
            "model_edit": DEFAULT_MODEL_EDIT,
            "model_translate": DEFAULT_MODEL_TRANSLATE,
            "model_qc": DEFAULT_MODEL_QC,
            "model_chat": DEFAULT_MODEL_CHAT,
            "model_qc_fast": DEFAULT_MODEL_QC,
        }
    try:
        config_file = get_user_config_file(st.session_state.current_user)
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            return {
                "api_url": config.get("api_url", DEFAULT_API_URL),
                "api_key": config.get("api_key", DEFAULT_API_KEY),
                "model": config.get("model", DEFAULT_MODEL),
                "model_edit": config.get("model_edit", config.get("model", DEFAULT_MODEL_EDIT)),
                "model_translate": config.get("model_translate", DEFAULT_MODEL_TRANSLATE),
                "model_qc": config.get("model_qc", DEFAULT_MODEL_QC),
                "model_chat": config.get("model_chat", DEFAULT_MODEL_CHAT),
                "model_qc_fast": config.get("model_qc_fast", config.get("model_qc", DEFAULT_MODEL_QC)),
            }
    except:
        return {
            "api_url": DEFAULT_API_URL,
            "api_key": DEFAULT_API_KEY,
            "model": DEFAULT_MODEL,
            "model_edit": DEFAULT_MODEL_EDIT,
            "model_translate": DEFAULT_MODEL_TRANSLATE,
            "model_qc": DEFAULT_MODEL_QC,
            "model_chat": DEFAULT_MODEL_CHAT,
            "model_qc_fast": DEFAULT_MODEL_QC,
        }

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

# ==================== 操作日志系统 ====================
LOGS_FILE = "operation_logs.json"

def log_operation(action, details="", extra=None):
    """记录用户操作日志
    
    Args:
        action: 操作类型（登录、笔记生成、自动修复、AI质检、AI对话等）
        details: 操作详情描述
        extra: 额外信息字典，可包含 input_preview, output_length, model, tokens 等
    """
    import datetime
    try:
        # 加载现有日志
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []
        
        # 获取当前用户
        username = st.session_state.get("current_user", "未登录")
        
        # 使用北京时间 (UTC+8)
        from datetime import timezone, timedelta
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.datetime.now(beijing_tz)
        
        # 构建日志条目
        log_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "user": username,
            "action": action,
            "details": details[:200] if details else ""
        }
        
        # 添加额外信息
        if extra:
            if "input_preview" in extra:
                log_entry["input_preview"] = extra["input_preview"][:100]  # 输入内容摘要
            if "output_length" in extra:
                log_entry["output_length"] = extra["output_length"]  # 输出长度
            if "model" in extra:
                log_entry["model"] = extra["model"]  # 使用的模型
            if "tokens" in extra:
                log_entry["tokens"] = extra["tokens"]  # Token 用量
            if "input_length" in extra:
                log_entry["input_length"] = extra["input_length"]  # 输入长度
        
        logs.append(log_entry)
        
        # 只保留最近 500 条日志
        logs = logs[-500:]
        
        # 保存日志
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass  # 日志失败不影响主流程

def load_logs(limit=100):
    """加载操作日志"""
    try:
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:][::-1]  # 返回最近的，倒序显示（最新在前）
    except:
        return []

def load_rules():
    """读取格式规范（所有用户使用统一规则）"""
    try:
        with open(DEFAULT_RULES_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

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

NOTES_ONLY_GENERATE_PROMPT = """## 任务：仅根据参考笔记生成全新答案

这是一个“只看参考笔记”的测试任务。
当前**没有**待修改答案，你必须从零开始生成，不要假设、复用或模仿任何未提供的旧答案。
参考笔记中已经包含用户问题或搜索词，你需要先从参考笔记中识别用户真正的问题与意图，再生成答案。

## 英文参考笔记
{ref_notes}

## 独立生成规则
{rules}

---

## 要求
1. 只根据参考笔记直接生成一份**全新的英文 Markdown 答案**
2. 所有事实点都必须能在参考笔记中找到直接依据
3. 禁止补充参考笔记之外的新事实、新数字、新实体、新日期或主观猜测
4. 用户问题或搜索词已包含在参考笔记中，不依赖任何额外输入框
5. 如果参考笔记存在多个义项，只保留与用户真实意图最匹配的内容；只有在搜索词本身就是明显多义词时，才按规则生成多义项答案
6. 严格遵守上方规则中的结构、引用、无答案终止、安全、过滤、措辞和内容筛选要求
7. 禁止出现 “according to the notes / based on the documents / the references show” 等暴露来源的表述
8. 所有引用必须保持为精确的 `[Note X](#)` 格式，并放在正确位置
9. 除作品名外，禁止对任何单词示例、风格词、概念词、学习词汇、普通名词使用双引号
10. 本页面只输出英文终稿；忽略规则中的默认双语输出要求，中文由页面上的“翻译”按钮单独生成
10.5 如果参考笔记里出现中文作品名、人名、地点名或其他专有名词，而英文答案又需要提到它，不要直接保留中文字符；必须改写成拼音或其他常见拉丁字母转写形式
11. 首段必须尽量压缩，只回答“它是什么”，不要塞入冗余修饰语、长定语从句、举例、购买方式或制作方式
11.5 如果用户问题或搜索词原本是小写，但被放在句首，首字母仍必须大写，例如 `dese refers to ...` 必须改为 `Dese refers to ...`
12. 只要写到食材、配料、制作动作或 recipe / preparation 内容，必须至少给出一组有序步骤；步骤优先写成 `1. **Preparation**: ... [Note X](#).` 这类格式；如果某个一级列表项下面接步骤或二级列表，父级这一行只能保留列表标题，不得再写冒号、句号和额外正文；如果某个四级标题下只有一个一级列表项，而这个一级列表项只是包装二级步骤，则不要保留这层一级列表项包装
13. 引用必须统一放在句子、段落或整个列表项的末尾；不要在一句话中间先放 `[Note X](#)` 再继续写后文
14. 任何 `####` 四级标题下如果最终只有 1 个信息点，必须写成单段正文，禁止保留成只有 1 个 bullet 的列表
14.5 如果正文最终只有一个 `####` 四级标题，必须删除这个四级标题，首段后直接进入列表或正文
15. 如果参考笔记不足以支持答案，按规则执行无答案终止或信息不足处理
16. 只输出最终英文 Markdown，不要解释、分析、检查过程，也不要用代码块包裹
"""

# 2 步名称
STEP_NAMES = [
    "Step 1: 前置检查",
    "Step 2: 修改输出"
]

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
    scrollbar-gutter: stable both-edges !important;
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

/* 页面样式就绪前先隐藏主内容，避免默认样式切到自定义样式时出现“变大一下” */
body:not(.style-ready) .main .block-container,
body:not(.style-ready) section[data-testid="stMain"] .block-container {
    opacity: 0 !important;
    pointer-events: none !important;
}
body.style-ready .main .block-container,
body.style-ready section[data-testid="stMain"] .block-container {
    opacity: 1 !important;
    transition: opacity 0.12s ease !important;
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
    transition: border-color 0.4s ease, box-shadow 0.4s ease, transform 0.4s ease;
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
}

/* 渐变分隔线 */
hr, .stDivider {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #00d4ff, #8b5cf6, #00d4ff, transparent) !important;
    margin: 1.5rem 0 !important;
}

/* 结果容器内的文字 - 更清晰的显示 */
[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p,
[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown li,
[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown h4,
.stMarkdownContainer p,
.stMarkdownContainer li {
    color: #ffffff !important;
    font-size: inherit !important;
    line-height: 1.6 !important;
    font-weight: 400 !important;
}

/* 翻译/结果区域的滚动容器 - 更好的对比度 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(10, 12, 20, 0.85) !important;
    border: 1px solid rgba(0, 212, 255, 0.25) !important;
    border-radius: 10px !important;
}

/* 结果区入场动效 */
[data-testid="column"].result-panel-shell,
[data-testid="stVerticalBlock"].result-panel-shell {
    transform-origin: top center;
    will-change: transform, opacity;
}
[data-testid="column"].result-panel-shell [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlock"].result-panel-shell [data-testid="stVerticalBlockBorderWrapper"] {
    box-shadow: 0 10px 28px rgba(7, 14, 30, 0.22), 0 0 0 1px rgba(0, 212, 255, 0.06) !important;
}
[data-testid="column"].result-panel-enter,
[data-testid="stVerticalBlock"].result-panel-enter {
    animation: resultPanelLift 0.48s cubic-bezier(0.22, 1, 0.36, 1);
    animation-delay: var(--result-enter-delay, 0ms);
    animation-fill-mode: both;
}
@keyframes resultPanelLift {
    from {
        opacity: 0;
        transform: translateY(14px) scale(0.985);
        filter: saturate(0.9);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: saturate(1);
    }
}

/* 加载态卡片 */
.processing-card {
    position: relative;
    overflow: hidden;
    margin: 0.25rem 0 1rem 0;
    padding: 0.9rem 1rem 1rem;
    border-radius: 14px;
    background:
        linear-gradient(180deg, rgba(18, 28, 48, 0.94) 0%, rgba(12, 18, 32, 0.92) 100%);
    border: 1px solid rgba(74, 190, 220, 0.22);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22), 0 0 24px rgba(52, 120, 198, 0.08);
}
.processing-card__sheen {
    position: absolute;
    inset: 0;
    background: linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.08) 22%, transparent 46%);
    transform: translateX(-140%);
    animation: processingSheen 2.6s ease-in-out infinite;
    pointer-events: none;
}
.processing-card__header {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.45rem;
}
.processing-card__pulse {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: #4acfe1;
    box-shadow: 0 0 0 rgba(74, 207, 225, 0.4);
    animation: processingPulse 1.8s ease-out infinite;
    flex-shrink: 0;
}
.processing-card__title {
    color: #effbff;
    font-size: 0.98rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.processing-card__detail {
    color: rgba(230, 242, 255, 0.78);
    font-size: 0.9rem;
    line-height: 1.6;
}
.processing-card__bar {
    margin-top: 0.8rem;
    height: 3px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
}
.processing-card__bar span {
    display: block;
    width: 38%;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, rgba(74, 207, 225, 0.2), rgba(104, 164, 230, 0.95), rgba(74, 207, 225, 0.2));
    animation: processingBar 1.6s ease-in-out infinite;
}
@keyframes processingSheen {
    0% { transform: translateX(-140%); opacity: 0; }
    18% { opacity: 1; }
    60% { opacity: 1; }
    100% { transform: translateX(160%); opacity: 0; }
}
@keyframes processingPulse {
    0% {
        transform: scale(0.92);
        box-shadow: 0 0 0 0 rgba(74, 207, 225, 0.42);
    }
    70% {
        transform: scale(1);
        box-shadow: 0 0 0 10px rgba(74, 207, 225, 0);
    }
    100% {
        transform: scale(0.92);
        box-shadow: 0 0 0 0 rgba(74, 207, 225, 0);
    }
}
@keyframes processingBar {
    0% { transform: translateX(-110%); }
    100% { transform: translateX(240%); }
}

@media (prefers-reduced-motion: reduce) {
    [data-testid="column"].result-panel-enter,
    [data-testid="stVerticalBlock"].result-panel-enter,
    .processing-card__sheen,
    .processing-card__pulse,
    .processing-card__bar span {
        animation: none !important;
    }
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
    background: linear-gradient(135deg, #20a3b8 0%, #3478c6 100%);
    color: #f4fbff !important;
    box-shadow: 0 4px 18px rgba(32, 163, 184, 0.30), 0 0 28px rgba(52, 120, 198, 0.16);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 26px rgba(32, 163, 184, 0.36), 0 0 38px rgba(52, 120, 198, 0.20);
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
.stTextArea,
.stTextArea *,
.stTextInput,
.stTextInput *,
.stSelectbox,
.stSelectbox * {
    box-sizing: border-box !important;
}

.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: transparent !important;
    backdrop-filter: none !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    transition: border-color 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                background-color 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                color 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.stTextArea > div > div > textarea:focus {
    box-shadow: none !important;
    animation: none !important;
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

/* text input - 只保留最外层一层边框 */
.stTextInput > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
.stTextInput > div > div {
    border: none !important;
    border-radius: 10px !important;
    background: transparent !important;
    overflow: visible !important;
    box-shadow: none !important;
}

/* 强制隐藏输入框内部的滚动条 */
.stTextInput input::-webkit-scrollbar {
    display: none !important;
    width: 0 !important;
}
.stTextInput > div > div:focus-within {
    box-shadow: none !important;
}
.stTextInput [data-baseweb="input"],
.stTextInput [data-baseweb="base-input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* textarea - 单层边框 */
.stTextArea textarea {
    color: #ffffff !important;
    caret-color: #00d4ff !important;
    border: none !important;
    background: transparent !important;
    width: 100% !important;
    box-sizing: border-box !important;
    overflow-y: auto !important;
    scrollbar-gutter: stable !important;
}
.stTextArea [data-baseweb="textarea"],
.stTextArea [data-baseweb="base-input"] {
    background-color: transparent !important;
    border: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.stTextArea > div,
.stTextArea > div > div > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
/* 强制所有 textarea 内部元素透明 */
.stTextArea * {
    background-color: transparent !important;
}
/* 只在最外层容器加边框和背景 */
.stTextArea > div > div {
    border: none !important;
    border-radius: 8px !important;
    background-color: rgba(15, 15, 26, 0.8) !important;
    overflow: hidden !important;
    width: 100% !important;
    box-sizing: border-box !important;
    box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.3) !important;
    transition: box-shadow 0.25s ease, background-color 0.25s ease !important;
}
.stTextArea > div > div:focus-within {
    box-shadow: inset 0 0 0 1px #00d4ff, 0 0 15px rgba(0, 212, 255, 0.3) !important;
}

.stTextInput input,
.stTextInput > div,
.stTextInput > div > div,
.stTextInput [data-baseweb="input"],
.stTextInput [data-baseweb="base-input"] {
    width: 100% !important;
    box-sizing: border-box !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease, background-color 0.25s ease, color 0.25s ease !important;
}

.stTabs [data-baseweb="tab-panel"] {
    scrollbar-gutter: stable both-edges !important;
}

/* ========== 下拉框样式 - 终极修复版 ========== */
/* 0. 下拉框外层容器 */
.stSelectbox {
    background: rgba(15, 15, 26, 0.6) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: none !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.3) !important;
    transition: border-color 0.25s ease !important, box-shadow 0.25s ease !important, background-color 0.25s ease !important;
}
.stSelectbox:hover {
    box-shadow: inset 0 0 0 1px rgba(0, 212, 255, 0.5), 0 0 15px rgba(0, 212, 255, 0.2) !important;
}
.stSelectbox:focus-within {
    box-shadow: inset 0 0 0 1px #00d4ff, 0 0 20px rgba(0, 212, 255, 0.3) !important;
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
    box-shadow: none !important;
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
border: 1px solid rgba(0, 212, 255, 0.35) !important;
border-radius: 10px !important;
background-color: rgba(15, 15, 26, 0.8) !important;
overflow: hidden;
box-shadow: none !important;
}
.stTextInput [data-testid="stTextInputRootElement"]:focus-within {
border-color: #00d4ff !important;
box-shadow: none !important;
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
box-shadow: none !important;
outline: none !important;
border-radius: 10px !important;
color: #ffffff !important;
caret-color: #00d4ff !important;
-webkit-text-fill-color: #ffffff !important;
}
.stTextInput > div > div > input,
.stTextInput > div > div > input:focus {
background: transparent !important;
border: none !important;
box-shadow: none !important;
outline: none !important;
animation: none !important;
color: #ffffff !important;
caret-color: #00d4ff !important;
-webkit-text-fill-color: #ffffff !important;
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
    transition: color 0.25s ease, background-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
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
    transform: none !important;
    animation: none !important;
    transition: color 0.25s ease, background-color 0.25s ease, box-shadow 0.25s ease !important;
}
/* 选中标签悬停效果 */
.stTabs [aria-selected="true"]:hover {
    transform: none !important;
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
    animation: none !important;
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
    animation: none !important;
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

/* 输入类组件禁止入场动画，避免加载时出现“变宽 / 变大一下”的视觉抖动 */
.stTextArea,
.stTextInput,
.stSelectbox,
.stTextArea *,
.stTextInput *,
.stSelectbox * {
    animation: none !important;
    transform: none !important;
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
    animation: none !important;
}

/* 登录/注册按钮特效 */
.stButton > button[kind="primary"] {
    position: relative;
    overflow: hidden;
}
.stButton > button[kind="primary"]::before {
    display: none !important;
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
    animation: none !important;
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

/* 让 columns 中的按钮高度与 Toggle 对齐 */
[data-testid="stHorizontalBlock"] [data-testid="stButton"],
[data-testid="stHorizontalBlock"] [data-testid="stCheckbox"] {
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stButton"] > div,
[data-testid="stHorizontalBlock"] [data-testid="stCheckbox"] > div,
[data-testid="stHorizontalBlock"] [data-testid="stCheckbox"] label[data-baseweb="checkbox"] {
    margin: 0 !important;
    min-height: 32px !important;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
    padding-top: 0.15rem !important;
    padding-bottom: 0.15rem !important;
    min-height: 32px !important;
}

/* Toggle - 保持标签文字区域透明，并直接用 CSS 跟随选中态 */
[data-testid="stCheckbox"] [data-testid="stWidgetLabel"],
[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] *,
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:last-child,
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div:last-child * {
    background: transparent !important;
    box-shadow: none !important;
}
</style>
"""
st.markdown(custom_style, unsafe_allow_html=True)

components.html("""
<script>
(function() {
    const markReady = () => {
        try {
            const parentBody = window.parent && window.parent.document && window.parent.document.body;
            if (parentBody) {
                parentBody.classList.add('style-ready');
            }
        } catch (e) {}
    };

    requestAnimationFrame(() => {
        requestAnimationFrame(markReady);
    });
})();
</script>
""", height=0)

components.html("""
<script>
(function() {
    const applyToggleStyles = () => {
        try {
            const parentDoc = window.parent && window.parent.document;
            if (!parentDoc) return;

            const labels = parentDoc.querySelectorAll('[data-testid="stCheckbox"] label[data-baseweb="checkbox"]');
            labels.forEach((label) => {
                const input = label.querySelector('input[type="checkbox"]');
                const allDivs = Array.from(label.querySelectorAll('div'));
                const track = allDivs.find((node) => {
                    const rect = node.getBoundingClientRect();
                    const text = (node.textContent || '').trim();
                    return !text && rect.width >= 24 && rect.width <= 64 && rect.height >= 14 && rect.height <= 34 && rect.width > rect.height * 1.5;
                });
                const textWrap = label.querySelector('[data-testid="stWidgetLabel"]');
                if (!input || !track) return;

                const checked = !!input.checked || label.getAttribute('aria-checked') === 'true';
                track.style.background = checked
                    ? 'linear-gradient(135deg, #239bb0 0%, #3478c6 100%)'
                    : 'rgba(255, 255, 255, 0.18)';
                track.style.borderColor = checked
                    ? 'rgba(52, 120, 198, 0.48)'
                    : 'rgba(42, 157, 178, 0.28)';
                track.style.boxShadow = checked
                    ? '0 0 14px rgba(35, 155, 176, 0.22)'
                    : 'none';
                track.style.transition = 'background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease';

                Array.from(track.querySelectorAll('div, span')).forEach((node) => {
                    const rect = node.getBoundingClientRect();
                    if (rect.width < 8 || rect.height < 8) return;
                    node.style.background = '#f7fbff';
                    node.style.boxShadow = 'none';
                });

                if (textWrap) {
                    textWrap.style.background = 'transparent';
                    textWrap.style.boxShadow = 'none';
                    Array.from(textWrap.querySelectorAll('*')).forEach((node) => {
                        node.style.background = 'transparent';
                        node.style.boxShadow = 'none';
                    });
                }
            });
        } catch (e) {}
    };

    const scheduleApply = () => {
        requestAnimationFrame(() => {
            requestAnimationFrame(applyToggleStyles);
        });
    };

    scheduleApply();
    setTimeout(scheduleApply, 120);
    setTimeout(scheduleApply, 500);

    try {
        const parentDoc = window.parent && window.parent.document;
        if (parentDoc && parentDoc.body) {
            const observer = new MutationObserver(scheduleApply);
            observer.observe(parentDoc.body, {
                subtree: true,
                childList: true,
                attributes: true,
                attributeFilter: ['checked', 'aria-checked', 'class', 'style']
            });
        }
    } catch (e) {}
})();
</script>
""", height=0)

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

# 播放提示音的函数（使用内联 WAV + Web Audio API 双重方案）
def play_notification_sound():
    """播放处理完成的提示音"""
    sound_js = """
    <script>
    (function() {
        // 方案1：在父页面(Streamlit主页面)中播放，绕过 iframe 限制
        try {
            const parentDoc = window.parent.document;
            
            // 移除之前的提示音元素（避免堆积）
            const oldAudio = parentDoc.getElementById('notif-sound-element');
            if (oldAudio) oldAudio.remove();
            
            // 使用 Web Audio API 在父页面上下文中播放
            const parentWindow = window.parent;
            const AudioCtx = parentWindow.AudioContext || parentWindow.webkitAudioContext;
            const ctx = new AudioCtx();
            
            // 必须 resume，否则浏览器自动播放策略会阻止
            ctx.resume().then(() => {
                // 第一个音：800Hz
                const osc1 = ctx.createOscillator();
                const gain1 = ctx.createGain();
                osc1.connect(gain1);
                gain1.connect(ctx.destination);
                osc1.frequency.value = 800;
                osc1.type = 'sine';
                gain1.gain.setValueAtTime(0.3, ctx.currentTime);
                gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                osc1.start(ctx.currentTime);
                osc1.stop(ctx.currentTime + 0.3);
                
                // 第二个音：1000Hz（延迟150ms）
                setTimeout(() => {
                    const osc2 = ctx.createOscillator();
                    const gain2 = ctx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.frequency.value = 1000;
                    osc2.type = 'sine';
                    gain2.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                    osc2.start(ctx.currentTime);
                    osc2.stop(ctx.currentTime + 0.3);
                }, 150);
            });
        } catch(e) {
            console.log('Parent audio failed, trying fallback:', e);
            // 方案2：在 iframe 内直接播放
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                ctx.resume().then(() => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.frequency.value = 800;
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.3);
                });
            } catch(e2) {
                console.log('All audio methods failed:', e2);
            }
        }
    })();
    </script>
    """
    st.components.v1.html(sound_js, height=1)


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
                            log_operation("登录", f"用户 {username} 登录成功")
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
tab3, tab2, tab5, tab4 = st.tabs(['参考笔记生成', '独立质检', 'AI 对话', 'API 配置'])

# 用 session_state 追踪当前 tab（st.tabs 不返回索引，需要在各 tab 内处理）

# 加载用户的 API 配置
if "user_config" not in st.session_state or st.session_state.user_config is None:
    st.session_state.user_config = load_user_config()

# API 配置
with tab4:
    st.subheader("API 配置")
    st.caption("这里统一管理接口和模型配置，修改后点击「保存配置」生效")
    
    # 模型选项列表
    MODEL_OPTIONS = [
        "流式抗截断/gemini-3.1-pro-high",
        "流式抗截断/gemini-3.1-pro-preview-high",
        "流式抗截断/gemini-3.1-pro-preview",
        "流式抗截断/gemini-3.1-pro-preview-search",
        "gemini-3.1-pro-preview-search",
        "gemini-pro-latest",
        "claude-opus-4-6",
        "claude-opus-4-6-thinking",
        "claude-sonnet-4-6",
        "claude-sonnet-4-6-thinking",
        "gpt-5.2",
        "gpt-5.4"
    ]

    LOG_ACTION_FILTERS = {
        "全部": None,
        "登录": {"登录"},
        "参考笔记生成": {"笔记生成"},
        "一键修复": {"自动修复"},
        "独立质检": {"AI质检"},
        "AI 对话": {"AI对话"},
        "保存配置": {"保存配置"},
    }

    LOG_ACTION_LABELS = {
        "登录": "登录",
        "笔记生成": "参考笔记生成",
        "自动修复": "一键修复",
        "AI质检": "独立质检",
        "AI对话": "AI 对话",
        "保存配置": "保存配置",
        "AI修改": "历史修改",
        "历史修改": "历史修改",
    }
    
    st.divider()
    st.markdown("**接口配置**")
    st.caption("当前账户共用同一套接口信息")
    api_url = st.text_input("API 地址", value=st.session_state.user_config.get("api_url", DEFAULT_API_URL), key="api_url_input")
    api_key = st.text_input("API 密钥", value=st.session_state.user_config.get("api_key", DEFAULT_API_KEY), type="password", key="api_key_input")
    
    st.divider()
    st.markdown("**模型配置**")
    st.caption("为参考笔记生成、中文翻译、独立质检和 AI 对话分别选择模型")
    
    # 参考笔记生成模型
    def get_model_index(key, default_model):
        current = st.session_state.user_config.get(key, default_model)
        return MODEL_OPTIONS.index(current) if current in MODEL_OPTIONS else 0
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        model_edit = st.selectbox("参考笔记生成", options=MODEL_OPTIONS, 
                                   index=get_model_index("model_edit", DEFAULT_MODEL_EDIT),
                                   key="model_edit_select", help="参考笔记生成功能使用")
        model_translate = st.selectbox("中文翻译", options=MODEL_OPTIONS,
                                        index=get_model_index("model_translate", DEFAULT_MODEL_TRANSLATE),
                                        key="model_translate_select", help="翻译功能使用")
    with col_m2:
        model_qc = st.selectbox("独立质检", options=MODEL_OPTIONS,
                                 index=get_model_index("model_qc", DEFAULT_MODEL_QC),
                                 key="model_qc_select", help="独立质检功能使用")
        model_chat = st.selectbox("AI 对话", options=MODEL_OPTIONS,
                                   index=get_model_index("model_chat", DEFAULT_MODEL_CHAT),
                                   key="model_chat_select", help="AI 对话功能使用")
    
    if st.button("保存配置", type="primary"):
        config = {
            "api_url": api_url,
            "api_key": api_key,
            "model_edit": model_edit,
            "model_translate": model_translate,
            "model_qc": model_qc,
            "model_chat": model_chat,
            "model_qc_fast": model_qc,  # 兼容旧代码
            "model": model_edit  # 兼容旧代码
        }
        if save_user_config_full(config):
            st.session_state.user_config = config
            log_operation("保存配置", "更新了 API 配置")
            render_soft_notice("配置已保存", tone="success")
        else:
            st.error("保存失败")
    
    # 操作日志查看
    st.divider()
    st.markdown("**最近操作**")
    st.caption("最近 50 条记录，可按用户和操作筛选")
    with st.expander("查看操作日志", expanded=False):
        logs = load_logs(limit=50)
        if logs:
            # 日志筛选
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                user_options = ["全部"] + sorted({log["user"] for log in logs})
                filter_user = st.selectbox("筛选用户", user_options, key="log_filter_user")
            with col_filter2:
                filter_action = st.selectbox("筛选操作", list(LOG_ACTION_FILTERS.keys()), key="log_filter_action")
            
            # 应用筛选
            filtered_logs = logs
            if filter_user != "全部":
                filtered_logs = [log for log in filtered_logs if log["user"] == filter_user]
            allowed_actions = LOG_ACTION_FILTERS.get(filter_action)
            if allowed_actions:
                filtered_logs = [log for log in filtered_logs if log["action"] in allowed_actions]
            
            if filtered_logs:
                st.caption(f"共 {len(filtered_logs)} 条记录，最多显示最近 30 条")

                for log in filtered_logs[:30]:
                    display_action = LOG_ACTION_LABELS.get(log["action"], log["action"])

                    detail_parts = [log.get("details", "")]
                    if "input_length" in log:
                        detail_parts.append(f"输入: {log['input_length']}字符")
                    if "output_length" in log:
                        detail_parts.append(f"输出: {log['output_length']}字符")
                    if "model" in log:
                        model_short = log["model"].replace("gemini-3-", "g3-").replace("-preview", "")
                        detail_parts.append(f"模型: {model_short}")
                    if "tokens" in log:
                        tokens = log["tokens"]
                        if isinstance(tokens, dict):
                            detail_parts.append(f"Token: {tokens.get('input', 0)}→{tokens.get('output', 0)}")

                    detail_str = " · ".join([part for part in detail_parts if part])
                    header_parts = [log["timestamp"], display_action, log["user"]]
                    if detail_str:
                        header_parts.append(detail_str[:60])

                    with st.expander(" · ".join(header_parts), expanded=False):
                        if detail_str:
                            st.caption(detail_str)
                        if log.get("input_preview"):
                            st.markdown(f"**输入摘要：** {log['input_preview']}...")
                        if "instruction" in log:
                            st.markdown(f"**指令：** {log['instruction']}")
            else:
                st.info("当前筛选条件下还没有记录")
        else:
            st.info("还没有操作日志")

# 初始化 session state
if "ai_results" not in st.session_state:
    st.session_state.ai_results = []
if "final_result" not in st.session_state:
    st.session_state.final_result = ""
if "translated_result" not in st.session_state:
    st.session_state.translated_result = ""
if "notes_query" not in st.session_state:
    st.session_state.notes_query = ""
if "notes_ref" not in st.session_state:
    st.session_state.notes_ref = ""
if "notes_result" not in st.session_state:
    st.session_state.notes_result = ""
if "notes_translated_result" not in st.session_state:
    st.session_state.notes_translated_result = ""
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
if "play_sound" not in st.session_state:
    st.session_state.play_sound = False

# 检查是否需要播放提示音
if st.session_state.play_sound:
    play_notification_sound()
    st.session_state.play_sound = False

# ==================== 旧版修改功能（已停用） ====================
if False:
    st.subheader("旧版自动修改（已停用）")
    
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
                            st.session_state.final_result = result
                    
                    render_progress_card(2, '处理完成！', 100, is_done=True)
                    
                    # 保存到历史记录
                    st.session_state.history.append({
                        "input": ai_input,
                        "ref": ref_notes,
                        "results": st.session_state.ai_results.copy(),
                        "final": st.session_state.final_result,
                        "translated": ""
                    })
                    save_history(st.session_state.history)
                    st.session_state.current_input = ai_input
                    st.session_state.current_ref = ref_notes
                    st.session_state.is_locked = True
                    st.session_state.current_history_idx = len(st.session_state.history) - 1
                    st.session_state.play_sound = True  # 标记播放提示音
                    # 记录详细日志
                    tokens = st.session_state.total_tokens
                    log_operation("历史修改", f"输入: {len(ai_input)} 字符, 输出: {len(st.session_state.final_result)} 字符", extra={
                        "input_preview": ai_input[:100],
                        "input_length": len(ai_input),
                        "output_length": len(st.session_state.final_result),
                        "model": model,
                        "tokens": {"input": tokens["prompt"], "output": tokens["completion"]}
                    })
                    st.rerun()
        else:
            st.warning("请输入内容")

    # 显示各步骤结果
    if st.session_state.ai_results:
        st.divider()
        # 显示 Token 用量
        if "total_tokens" in st.session_state and st.session_state.total_tokens["total"] > 0:
            tokens = st.session_state.total_tokens
            # 总计 = 输入 + 输出（而不是 API 返回的 total，因为 API 的 total 可能包含 thinking tokens）
            calculated_total = tokens['prompt'] + tokens['completion']
            st.markdown(f"""
            <div style="background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3); border-radius: 8px; padding: 10px 15px; margin-bottom: 15px;">
                <span style="color: #00d4ff; font-weight: 500;">📊 Token 用量：</span>
                <span style="color: #fff; margin-left: 10px;">输入: {tokens['prompt']:,}</span>
                <span style="color: #fff; margin-left: 15px;">输出: {tokens['completion']:,}</span>
                <span style="color: #00ff88; margin-left: 15px; font-weight: 600;">总计: {calculated_total:,}</span>
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
                # view_mode = st.radio("", ["预览", "编辑"], horizontal=True, key="en_view_mode", label_visibility="collapsed")
                view_mode = st.toggle("预览模式", value=True, key="en_view_mode")
            
            if view_mode: # 预览模式
                with st.container(height=300):
                    st.markdown(st.session_state.final_result)
                # 预览模式：使用预编码内容
                st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
                encoded_en = base64.b64encode(st.session_state.final_result.encode('utf-8')).decode('utf-8')
                copy_js_en = f'''{html_style}<script>function copyEn(){{const b='{encoded_en}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnEn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnEn').innerText='复制英文',1500);}});}}</script><button id="btnEn" onclick="copyEn()" style="background:linear-gradient(135deg,#00d4ff 0%,#8b5cf6 100%);box-shadow:0 0 15px rgba(0,212,255,0.3);">复制英文</button>'''
                components.html(copy_js_en, height=60)
            else:
                # 使用 on_change 自动保存编辑内容
                def save_main_edit():
                    st.session_state.final_result = st.session_state.result_en_edit
                    if st.session_state.history and st.session_state.current_history_idx >= 0:
                        st.session_state.history[st.session_state.current_history_idx]["final"] = st.session_state.result_en_edit
                        save_history(st.session_state.history)
                
                st.text_area("英文结果", value=st.session_state.final_result, height=300, 
                            key="result_en_edit", label_visibility="collapsed",
                            on_change=save_main_edit)
                
                # 编辑模式：找到距离复制按钮最近的 textarea
                st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
                # 找到与当前 iframe 距离最近的 textarea
                copy_js_en = f'''{html_style}<script>function copyEn(){{const iframes=window.parent.document.querySelectorAll('iframe');let thisIframe=null;for(const f of iframes){{if(f.contentWindow===window){{thisIframe=f;break;}}}}if(thisIframe){{const iRect=thisIframe.getBoundingClientRect();const tas=window.parent.document.querySelectorAll('textarea');let closest=null;let minDist=Infinity;for(const ta of tas){{const tRect=ta.getBoundingClientRect();const dist=Math.abs(tRect.bottom-iRect.top)+Math.abs(tRect.left-iRect.left);if(dist<minDist){{minDist=dist;closest=ta;}}}}if(closest&&closest.value){{navigator.clipboard.writeText(closest.value).then(()=>{{document.getElementById('btnEn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnEn').innerText='复制英文',1500);}});return;}}}}alert('找不到编辑框');}}</script><button id="btnEn" onclick="copyEn()" style="background:linear-gradient(135deg,#00d4ff 0%,#8b5cf6 100%);box-shadow:0 0 15px rgba(0,212,255,0.3);">复制英文</button>'''
                components.html(copy_js_en, height=60)
        
        with col_translate:
            # 标题栏放翻译按钮
            h_c1, h_c2 = st.columns([3, 1])
            with h_c1:
                st.subheader("中文翻译")
            with h_c2:
                translate_clicked = st.button("翻译", use_container_width=True, type="primary", key="trans_btn_header")
            
            # 使用 container + markdown 显示翻译结果，更清晰
            with st.container(height=300):
                if st.session_state.translated_result:
                    st.markdown(st.session_state.translated_result)
                else:
                    st.caption("点击「翻译」按钮生成中文翻译...")
            
            # 复制中文按钮
            st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
            if st.session_state.translated_result:
                encoded_cn = base64.b64encode(st.session_state.translated_result.encode('utf-8')).decode('utf-8')
                copy_js_cn = f'''{html_style}<script>function copyCn(){{const b='{encoded_cn}';const bytes=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const t=new TextDecoder('utf-8').decode(bytes);navigator.clipboard.writeText(t).then(()=>{{document.getElementById('btnCn').innerText='✅ 已复制';setTimeout(()=>document.getElementById('btnCn').innerText='复制中文',1500);}});}}</script><button id="btnCn" onclick="copyCn()" style="background:linear-gradient(135deg,#8b5cf6 0%,#00d4ff 100%);box-shadow:0 0 15px rgba(139,92,246,0.3);">复制中文</button>'''
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
                        st.session_state.translated_result = normalize_markdown_spacing(result)
                        if st.session_state.history and st.session_state.current_history_idx >= 0:
                            st.session_state.history[st.session_state.current_history_idx]["translated"] = st.session_state.translated_result
                            save_history(st.session_state.history)
                        st.session_state.play_sound = True  # 翻译完成也播放提示音
                        st.rerun()
                    else:
                        st.error(result)

# ==================== 参考笔记生成功能 ====================
with tab3:
    st.subheader("参考笔记生成")
    st.caption("只需要粘贴参考笔记，笔记中已包含用户问题或搜索词")
    notes_ref = st.text_area(
        "参考笔记",
        height=360,
        value=st.session_state.notes_ref,
        placeholder="粘贴参考笔记...",
        key="notes_ref_input"
    )
    if notes_ref != st.session_state.notes_ref:
        st.session_state.notes_ref = notes_ref

    col_generate, col_clear = st.columns([2.2, 1], gap="small")
    with col_generate:
        notes_generate_clicked = st.button("开始生成", type="primary", use_container_width=True, key="notes_generate_btn")
    with col_clear:
        notes_clear_clicked = st.button("清空结果", use_container_width=True, key="notes_clear_btn")

    if notes_clear_clicked:
        st.session_state.notes_result = ""
        st.session_state.notes_translated_result = ""
        st.rerun()

    if notes_generate_clicked:
        if not notes_ref.strip():
            st.warning("请输入参考笔记")
        else:
            user_cfg = st.session_state.user_config
            api_url = user_cfg.get("api_url", DEFAULT_API_URL)
            api_key = user_cfg.get("api_key", DEFAULT_API_KEY)
            model = user_cfg.get("model_edit", user_cfg.get("model", DEFAULT_MODEL))

            if not api_key:
                st.error("请先在 API 配置中设置 API Key")
            else:
                rules = read_utf8_file(GENERATE_WITH_NOTES_RULES_FILE, "")
                if not rules:
                    st.error("无法读取 generate_with_notes_rules.md 文件")
                else:
                    loading_placeholder = st.empty()
                    with loading_placeholder.container():
                        render_loading_banner(
                            "正在根据参考笔记生成英文结果",
                            "只会使用当前粘贴的参考笔记，请稍候片刻。"
                        )

                    call_error = ""
                    result = ""
                    success = False
                    token_info = {}
                    try:
                        prompt = NOTES_ONLY_GENERATE_PROMPT.format(
                            ref_notes=notes_ref,
                            rules=rules
                        )
                        result, success, token_info = call_single_step(prompt, api_url, api_key, model)
                    except Exception as exc:
                        call_error = str(exc)
                    loading_placeholder.empty()

                    if call_error:
                        st.error(f"生成失败: {call_error}")
                    elif success:
                        st.session_state.notes_result = normalize_notes_generation_output(result)
                        st.session_state.notes_translated_result = ""
                        st.session_state.play_sound = True
                        log_operation("笔记生成", f"参考笔记输入: {len(notes_ref)} 字符", extra={
                            "input_preview": notes_ref[:100],
                            "input_length": len(notes_ref),
                            "output_length": len(st.session_state.notes_result),
                            "model": model,
                            "tokens": {"input": token_info.get("prompt_tokens", 0), "output": token_info.get("completion_tokens", 0)}
                        })
                        st.rerun()
                    else:
                        st.error(f"生成失败: {result}")

    if st.session_state.notes_result:
        st.divider()
        render_dual_result_panels(
            result_key="notes_result",
            translated_key="notes_translated_result",
            result_title="英文结果",
            result_title_style="subheader",
            result_view_key="notes_view_mode",
            result_edit_key="notes_result_edit",
            result_copy_prefix="notes_result",
            translate_button_key="notes_translate_btn",
            translate_copy_prefix="notes_translate",
            height=RESULT_PANEL_HEIGHT,
            result_textarea_label="英文结果",
            result_copy_label="复制英文",
            translation_title="中文翻译",
            translation_title_style="subheader",
            translation_empty_caption="点击「翻译」按钮生成中文翻译...",
            translation_copy_label="复制中文",
        )
        if st.button("清空结果", key="notes_clear_result_btn", use_container_width=True):
            st.session_state.notes_result = ""
            st.session_state.notes_translated_result = ""
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
        help="程序自动修复：秒级修复格式问题；AI质检：检查格式逻辑+内容准确性",
        label_visibility="collapsed"
    )
    
    if qc_mode == "程序自动修复":
        st.caption("秒级自动修复：引用格式、空格、句号位置、列表缩进等")
    else:
        st.caption("AI 检查格式逻辑，有参考笔记时也检查内容准确性")
    
    # AI质检时在输入框上方显示"只看问题"开关
    qc_issues_only = False  # 默认输出问题+修改结果
    if qc_mode == "AI 质检":
        # 初始化 session_state 中的按钮状态（记住用户选择）
        if "qc_issues_only_preference" not in st.session_state:
            st.session_state.qc_issues_only_preference = False
        
        col_toggle, col_help = st.columns([1, 3])
        with col_toggle:
            qc_issues_only = st.toggle("只看问题", 
                                        value=st.session_state.qc_issues_only_preference, 
                                        key="qc_issues_only_toggle", 
                                        help="开启后只输出问题清单，不输出修改后的 Markdown")
            # 保存用户选择
            st.session_state.qc_issues_only_preference = qc_issues_only
        with col_help:
            if qc_issues_only:
                st.caption("只输出问题清单，方便快速审阅")
            else:
                st.caption("输出问题清单和修改后的 Markdown")
    
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
            fix_clicked = st.button("一键修复", type="primary", use_container_width=True, key="auto_fix_btn")
        with col_analyze:
            analyze_clicked = st.button("分析问题", use_container_width=True, key="analyze_btn")
        
        if fix_clicked:
            if qc_input.strip():
                # 自动修复
                fixed_text = fix_all_format(qc_input)
                issues = analyze_format_issues(qc_input)
                
                # 保存结果
                st.session_state.qc_result = fixed_text
                st.session_state.qc_issues = "\n".join([f"- {issue}" for issue in issues]) if issues else "未发现可自动修复的格式问题"
                st.session_state.qc_tokens = {}
                st.session_state.qc_auto_fixed = True
                st.session_state.qc_issues_only_mode = False  # 程序自动修复不是"只看问题"模式
                st.session_state.qc_translated = ""  # 清空上一条的翻译
                st.session_state.play_sound = True  # 播放提示音
                log_operation("自动修复", f"输入: {len(qc_input)} 字符, 发现 {len(issues)} 个问题", extra={
                    "input_preview": qc_input[:100],
                    "input_length": len(qc_input),
                    "output_length": len(fixed_text),
                    "issues_count": len(issues)
                })
                st.rerun()
            else:
                st.warning("请输入待检查的回答")
        
        if analyze_clicked:
            if qc_input.strip():
                issues = analyze_format_issues(qc_input)
                if issues:
                    st.markdown("### 发现的问题")
                    for issue in issues:
                        if "需AI判断" in issue:
                            st.warning(issue)
                        else:
                            st.info(issue)
                else:
                    render_soft_notice("未发现格式问题", tone="success")
            else:
                st.warning("请输入待检查的回答")
    
    # AI 质检模式
    elif st.button("开始质检", type="primary", use_container_width=True, key="qc_start_btn"):
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
                format_rules = read_utf8_file(FORMAT_ONLY_RULES_FILE)
                
                # 如果有参考笔记，额外读取 format_with_notes_rules.md
                notes_rules = ""
                if qc_notes.strip():
                    notes_rules = read_utf8_file(FORMAT_WITH_NOTES_RULES_FILE, "")
                
                if not format_rules:
                    st.error("无法读取格式规则文件 (format_only_rules.md)")
                else:
                    with st.spinner("正在质检，请勿切换页面..."):
                        # 根据是否有参考笔记构建不同的 prompt（使用程序修复后的文本）
                        # 根据是否只看问题，选择输出格式
                        if qc_issues_only:
                            output_format = """## 输出格式（严格按此格式）

---ISSUES_START---
（如果有问题，用表格列出；如果**没有问题**，只写一行：✅ 未发现问题）

| 序号 | 问题类型 | 问题描述 | 修改建议 |
|------|----------|----------|----------|
| 1 | 格式/内容 | ... | ... |

---ISSUES_END---

注意：只需输出问题清单，不要输出修改后的 Markdown。
"""
                        else:
                            output_format = """## 输出格式（严格按此格式）

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
                        
                        if qc_notes.strip():
                            # 有参考笔记：同时检查格式和内容，使用两套规则
                            qc_prompt = f"""## 任务：格式+内容质检

你是一个质检员。请**逐条对照规则**检查格式问题，并对照参考笔记检查内容准确性。

**检查要求**：
1. 逐条对照规则文件中的每一条规则进行检查
2. 特别注意：小标题命名一致性、禁止兜底型泛化命名、多义词内容平衡、信息来源筛选、**单项内容处理（四级标题下只有1项时不用列表和加粗小标题）**等规则
3. 如果发现问题，必须指出{"" if qc_issues_only else "并修复"}；如果确实没问题，才写"✅ 未发现问题"
4. **绝对禁止删除 Note 引用**：原文中的所有 `[Note X](#)` 标记必须100%保留，修改内容时需保持引用位置正确
5. 以下格式问题已由程序处理，无需检查：标点空格、列表缩进、Title Case、中文标点等

## 待检查的回答
{qc_input}

## 参考笔记
{qc_notes}

## 格式规则（无需参考笔记）
{format_rules}

## 内容规则（需对照参考笔记检查）
{notes_rules}

---

{output_format}
"""
                        else:
                            # 无参考笔记：只检查格式
                            qc_prompt = f"""## 任务：格式质检

你是一个格式规范质检员。请**逐条对照规则**检查格式问题。

**检查要求**：
1. 逐条对照规则文件中的每一条规则进行检查
2. 特别注意：小标题命名一致性、禁止兜底型泛化命名、多义词内容平衡、**单项内容处理（四级标题下只有1项时不用列表和加粗小标题）**等规则
3. 如果发现问题，必须指出{"" if qc_issues_only else "并修复"}；如果确实没问题，才写"✅ 未发现格式问题"
4. **绝对禁止删除 Note 引用**：原文中的所有 `[Note X](#)` 标记必须100%保留，修改内容时需保持引用位置正确
5. 以下格式问题已由程序处理，无需检查：标点空格、列表缩进、Title Case、中文标点等

## 待检查的回答
{qc_input}

## 格式规则
{format_rules}

---

{output_format}
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
                            
                            # 只有非"只看问题"模式才解析修改结果
                            if not qc_issues_only:
                                if "---FIXED_START---" in result:
                                    try:
                                        # 先尝试正常解析（有 END 标记）
                                        if "---FIXED_END---" in result:
                                            fixed = result.split("---FIXED_START---")[1].split("---FIXED_END---")[0].strip()
                                        else:
                                            # 没有 END 标记，取 FIXED_START 之后的所有内容
                                            fixed = result.split("---FIXED_START---")[1].strip()
                                    except:
                                        fixed = result
                                else:
                                    # 没有 FIXED_START 标记，尝试去除 ISSUES 部分后使用
                                    if "---ISSUES_END---" in result:
                                        fixed = result.split("---ISSUES_END---")[1].strip()
                                    else:
                                        fixed = result
                            else:
                                # "只看问题"模式下，fixed 设为空
                                fixed = ""
                            
                            st.session_state.qc_issues = issues
                            st.session_state.qc_result = fixed
                            st.session_state.qc_tokens = token_info
                            st.session_state.qc_auto_fixed = False
                            st.session_state.qc_issues_only_mode = qc_issues_only  # 保存当前模式
                            st.session_state.qc_translated = ""  # 清空上一条的翻译
                            st.session_state.play_sound = True  # 播放提示音
                            log_operation("AI质检", f"输入: {len(qc_input)} 字符, 模式: {'只看问题' if qc_issues_only else '问题+修复'}", extra={
                                "input_preview": qc_input[:100],
                                "input_length": len(qc_input),
                                "output_length": len(fixed),
                                "model": model_qc,
                                "tokens": {"input": token_info.get("prompt_tokens", 0), "output": token_info.get("completion_tokens", 0)}
                            })
                            st.rerun()
                        else:
                            st.error(f"质检失败: {result}")
        else:
            st.warning("请输入待检查的回答")
    
    # 显示质检结果
    # 判断是否有结果需要显示（问题清单或修改结果）
    has_qc_result = ("qc_result" in st.session_state and st.session_state.qc_result) or \
                    ("qc_issues" in st.session_state and st.session_state.qc_issues and 
                     st.session_state.get("qc_issues_only_mode", False))
    
    if has_qc_result:
        st.divider()
        
        # 显示修复来源标识
        if st.session_state.get("qc_auto_fixed", False):
            render_soft_notice("程序自动修复完成", tone="success")
        elif st.session_state.get("qc_issues_only_mode", False):
            render_soft_notice("当前是只看问题模式，仅显示问题清单。", tone="info")
        
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
            # 在"只看问题"模式下，问题清单默认展开且不放在 expander 里
            if st.session_state.get("qc_issues_only_mode", False):
                st.markdown("**问题清单**")
                st.markdown(st.session_state.qc_issues)
            else:
                with st.expander("发现的问题", expanded=True):
                    st.markdown(st.session_state.qc_issues)
    
    # 只有在非"只看问题"模式下，才显示修改后的 Markdown
    if "qc_result" in st.session_state and st.session_state.qc_result and not st.session_state.get("qc_issues_only_mode", False):
        render_dual_result_panels(
            result_key="qc_result",
            translated_key="qc_translated",
            result_title="英文结果",
            result_title_style="subheader",
            result_view_key="qc_view_mode",
            result_edit_key="qc_edit_area",
            result_copy_prefix="qc_result",
            translate_button_key="qc_translate_btn",
            translate_copy_prefix="qc_translate",
            height=RESULT_PANEL_HEIGHT,
            result_textarea_label="编辑结果",
            result_copy_label="复制英文",
            translation_title="中文翻译",
            translation_title_style="subheader",
            translation_empty_caption="点击「翻译」按钮生成中文翻译...",
            translation_copy_label="复制中文",
        )
        
        # 清空按钮
        if st.button("清空结果", key="qc_clear_btn", use_container_width=True):
            st.session_state.qc_result = ""
            st.session_state.qc_issues = ""
            st.session_state.qc_tokens = {}
            st.session_state.qc_translated = ""
            st.rerun()

# ==================== AI 对话功能 ====================
with tab5:
    st.subheader("AI 对话")
    st.caption("输入自定义提示词，让 AI 按你的要求修改 Markdown")
    
    # 初始化 session state
    if "chat_input" not in st.session_state:
        st.session_state.chat_input = ""
    if "chat_result" not in st.session_state:
        st.session_state.chat_result = ""
    if "chat_translated" not in st.session_state:
        st.session_state.chat_translated = ""
    
    # 输入区域
    col_input, col_prompt = st.columns([1, 1])
    
    with col_input:
        st.markdown("**待修改内容**")
        # 使用动态 key 来允许更新值
        if "chat_input_version" not in st.session_state:
            st.session_state.chat_input_version = 0
        chat_markdown = st.text_area(
            "输入 Markdown",
            value=st.session_state.chat_input,
            height=200,
            key=f"chat_markdown_input_{st.session_state.chat_input_version}",
            placeholder="粘贴需要修改的 Markdown 内容...",
            label_visibility="collapsed"
        )
        if chat_markdown != st.session_state.chat_input:
            st.session_state.chat_input = chat_markdown
    
    with col_prompt:
        st.markdown("**修改要求**")
        chat_prompt = st.text_area(
            "输入提示词",
            height=200,
            key="chat_prompt_input",
            placeholder="例如：\n- 把所有小标题改成具体的分类名称\n- 合并 Nature 和 Entertainment 相关的内容\n- 检查首段是否过于泛化",
            label_visibility="collapsed"
        )
    
    # 发送按钮
    if st.button("发送给 AI", type="primary", use_container_width=True, key="chat_send_btn"):
        if not chat_markdown.strip():
            st.warning("请输入待修改的 Markdown")
        elif not chat_prompt.strip():
            st.warning("请输入修改指令")
        else:
            user_cfg = st.session_state.user_config
            api_url = user_cfg.get("api_url", DEFAULT_API_URL)
            api_key = user_cfg.get("api_key", DEFAULT_API_KEY)
            model = user_cfg.get("model_chat", DEFAULT_MODEL_CHAT)
            
            if not api_key:
                st.error("请先在 API 配置中设置 API Key")
            else:
                with st.spinner("AI 正在处理..."):
                    format_only_rules = read_utf8_file(FORMAT_ONLY_RULES_FILE)
                    if not format_only_rules:
                        st.error("无法读取格式规则文件 (format_only_rules.md)")
                    else:
                        # 构建 prompt
                        full_prompt = f"""## 任务：按用户指令修改 Markdown，并严格遵守格式规则

## 格式规则（必须遵守）
{format_only_rules}

## 用户指令
{chat_prompt}

## 待修改的 Markdown
{chat_markdown}

---

## 要求
1. 严格按照用户指令进行修改
2. 直接输出修改后的完整 Markdown
3. 不要任何解释、注释、说明
4. 不要用代码块包裹"""

                        result, success, token_info = call_single_step(full_prompt, api_url, api_key, model)
                        if success:
                            st.session_state.chat_result = result
                            st.session_state.chat_translated = ""  # 清空翻译
                            st.session_state.play_sound = True  # 播放提示音
                            log_operation("AI对话", f"指令: {chat_prompt[:50]}", extra={
                                "input_preview": chat_markdown[:100] if chat_markdown else "",
                                "input_length": len(chat_markdown) if chat_markdown else 0,
                                "output_length": len(result),
                                "model": model,
                                "tokens": {"input": token_info.get("prompt_tokens", 0), "output": token_info.get("completion_tokens", 0)},
                                "instruction": chat_prompt[:100]
                            })
                            st.rerun()
                        else:
                            st.error(f"AI 处理失败: {result}")
    
    st.divider()
    
    # 结果显示区域
    if st.session_state.chat_result:
        render_dual_result_panels(
            result_key="chat_result",
            translated_key="chat_translated",
            result_title="英文结果",
            result_title_style="subheader",
            result_view_key="chat_view_toggle",
            result_edit_key="chat_edit_area",
            result_copy_prefix="chat_result",
            translate_button_key="chat_translate_btn",
            translate_copy_prefix="chat_translate",
            height=RESULT_PANEL_HEIGHT,
            result_textarea_label="编辑结果",
            result_copy_label="复制英文",
            translation_title="中文翻译",
            translation_title_style="subheader",
            translation_empty_caption="点击「翻译」按钮生成中文翻译...",
            translation_copy_label="复制中文",
        )
        
        # 使用修改结果作为新输入
        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if st.button("将结果作为新输入", use_container_width=True, key="chat_reuse_btn"):
                st.session_state.chat_input = st.session_state.chat_result
                st.session_state.chat_input_version += 1  # 增加 version 来刷新 widget
                st.session_state.chat_result = ""
                st.session_state.chat_translated = ""
                st.rerun()
        with col_action2:
            if st.button("清空结果", use_container_width=True, key="chat_clear_btn"):
                st.session_state.chat_result = ""
                st.session_state.chat_translated = ""
                st.rerun()

