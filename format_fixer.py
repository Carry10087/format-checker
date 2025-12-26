"""
格式自动修复工具
用于修复 format_only_rules.md 中程序可自动处理的格式问题
"""

import re


# ==================== 基础修复函数 ====================

def fix_note_format(text: str) -> str:
    """修复引用格式：[Note1] → [Note 1]"""
    return re.sub(r'\[Note(\d+)\]', r'[Note \1]', text)


def fix_highlight_spaces(text: str) -> str:
    """修复 *** 内的多余空格"""
    # 修复结尾空格：*** *** → ******
    text = re.sub(r'\*\*\*\s+\*\*\*', '******', text)
    # 修复高亮内结尾空格：word *** → word***
    text = re.sub(r'\s+\*\*\*\.', '***.', text)
    text = re.sub(r'\s+\*\*\*(\[)', r'***\1', text)
    return text


def fix_period_position(text: str) -> str:
    """修复首段句号位置：句号应在***外面"""
    # 修复：内容。*** → 内容***。 的情况（中文句号）
    text = re.sub(r'。\*\*\*', '***。', text)
    # 修复：内容.*** → 内容***. 的情况（英文句号，非引号结尾）
    text = re.sub(r'([^""])\.(\*\*\*)', r'\1\2.', text)
    return text


def fix_list_item_period(text: str) -> str:
    """修复列表项末尾缺少句号"""
    lines = text.split('\n')
    result = []
    
    for line in lines:
        # 检查是否是列表项（以 - 或数字. 开头）
        if re.match(r'^[\s]*[-\d]+\.?\s', line):
            stripped = line.rstrip()
            # 如果末尾是引用，检查引用前是否有句号
            if re.search(r'\[Note\s*\d+\](\(#\))?$', stripped):
                match = re.search(r'(\[Note\s*\d+\](\(#\))?)+$', stripped)
                if match:
                    before_notes = stripped[:match.start()]
                    notes = stripped[match.start():]
                    if before_notes and not before_notes.rstrip().endswith(('.', '。', '!', '?', '！', '？')):
                        line = before_notes.rstrip() + '.' + notes
            elif stripped and not stripped.endswith(('.', '。', '!', '?', '！', '？', ':', '：')):
                line = stripped + '.'
        result.append(line)
    
    return '\n'.join(result)


def fix_secondary_list_indent(text: str) -> str:
    """修复二级列表缩进：统一为4个空格"""
    lines = text.split('\n')
    result = []
    
    for line in lines:
        match = re.match(r'^(\s+)([-\d]+\.?\s)', line)
        if match:
            indent = match.group(1)
            if len(indent) != 4 and len(indent) > 0:
                line = '    ' + line.lstrip()
        result.append(line)
    
    return '\n'.join(result)


# ==================== 新增修复函数 ====================

def fix_chinese_punctuation(text: str) -> str:
    """将中文标点替换为英文标点（使用 Unicode 转义避免混淆）"""
    replacements = {
        '\uff0c': ', ',   # ， 中文逗号
        '\u3002': '. ',   # 。 中文句号
        '\u201c': '"',    # " 中文左双引号
        '\u201d': '"',    # " 中文右双引号
        '\u2018': "'",    # ' 中文左单引号
        '\u2019': "'",    # ' 中文右单引号
        '\uff1a': ': ',   # ： 中文冒号
        '\uff1b': '; ',   # ； 中文分号
        '\uff08': ' (',   # （ 中文左括号
        '\uff09': ') ',   # ） 中文右括号
        '\uff01': '! ',   # ！ 中文感叹号
        '\uff1f': '? ',   # ？ 中文问号
    }
    for cn, en in replacements.items():
        text = text.replace(cn, en)
    # 清理多余空格
    text = re.sub(r'  +', ' ', text)
    return text


# 真正的中文标点（使用 Unicode 转义，避免字符混淆）
# 注意：英文直引号 " (U+0022) 不在此列表中
CHINESE_PUNCTUATION = {
    '\uff0c': ',',   # ， 中文逗号 (U+FF0C)
    '\u3002': '.',   # 。 中文句号 (U+3002)
    '\u201c': '"',   # " 中文左双引号 (U+201C)
    '\u201d': '"',   # " 中文右双引号 (U+201D)
    '\u2018': "'",   # ' 中文左单引号 (U+2018)
    '\u2019': "'",   # ' 中文右单引号 (U+2019)
    '\uff1a': ':',   # ： 中文冒号 (U+FF1A)
    '\uff1b': ';',   # ； 中文分号 (U+FF1B)
    '\uff08': '(',   # （ 中文左括号 (U+FF08)
    '\uff09': ')',   # ） 中文右括号 (U+FF09)
    '\uff01': '!',   # ！ 中文感叹号 (U+FF01)
    '\uff1f': '?',   # ？ 中文问号 (U+FF1F)
}


def fix_spacing_rules(text: str) -> str:
    """修复空格规则：句号/逗号后空格、括号空格、冒号后空格"""
    # 句号后加空格（排除 [Note X] 和 *** 情况）
    text = re.sub(r'\.([A-Za-z])', r'. \1', text)
    # 逗号后加空格
    text = re.sub(r',([A-Za-z])', r', \1', text)
    # 冒号后加空格
    text = re.sub(r':([A-Za-z])', r': \1', text)
    # 左括号前加空格（如果前面是字母）
    text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
    # 右括号后加空格（如果后面是字母）
    text = re.sub(r'\)([A-Za-z])', r') \1', text)
    return text


def fix_hyphen_spaces(text: str) -> str:
    """修复连字符两侧的空格：well - known → well-known"""
    text = re.sub(r'(\w)\s+-\s+(\w)', r'\1-\2', text)
    return text


def fix_single_asterisk_symbol(text: str) -> str:
    """移除单个 ※ 符号"""
    text = re.sub(r'※\s*', '', text)
    return text


def fix_title_case(text: str) -> str:
    """修复四级标题和列表小标题的 Title Case"""
    # 不需要大写的词（介词、冠词、连词）
    lowercase_words = {'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
                       'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
                       'into', 'through', 'during', 'before', 'after', 'above', 'below',
                       'between', 'under', 'over'}
    
    def to_title_case(title: str) -> str:
        """将标题转换为 Title Case"""
        words = title.split()
        result = []
        for i, word in enumerate(words):
            # 第一个词和最后一个词总是大写
            if i == 0 or i == len(words) - 1:
                result.append(word.capitalize())
            # 介词、冠词等小写（除非是第一个词）
            elif word.lower() in lowercase_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        return ' '.join(result)
    
    lines = text.split('\n')
    result = []
    
    for line in lines:
        # 修复四级标题
        h4_match = re.match(r'^(####\s+)(.+)$', line)
        if h4_match:
            prefix = h4_match.group(1)
            title = h4_match.group(2)
            line = prefix + to_title_case(title)
        
        # 修复列表小标题（- **Title**: 格式）
        list_match = re.match(r'^(\s*-\s+\*\*)([^*]+)(\*\*:\s*)(.*)$', line)
        if list_match:
            prefix = list_match.group(1)
            title = list_match.group(2)
            middle = list_match.group(3)
            content = list_match.group(4)
            line = prefix + to_title_case(title) + middle + content
        
        result.append(line)
    
    return '\n'.join(result)


def fix_backticks_and_asterisks(text: str) -> str:
    """将正文中的反引号和单星号改为双引号"""
    # 不处理代码块内的内容
    # 反引号 `text` → "text"
    text = re.sub(r'`([^`]+)`', r'"\1"', text)
    
    # 单星号 *text* → "text"（但不影响 **text** 和 ***text***）
    # 使用负向前瞻和后顾确保不匹配多星号
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'"\1"', text)
    
    return text


def fix_semicolon_sentences(text: str) -> str:
    """将分号连接的句子改为句号"""
    # 匹配分号后跟空格和大写字母（表示新句子）
    text = re.sub(r';\s+([A-Z])', r'. \1', text)
    return text


def fix_quote_punctuation(text: str) -> str:
    """修复引号内的标点位置：句号和逗号应在引号内"""
    # 规则：正文中的引号，句号和逗号在引号内
    # "text". → "text."
    # "text", → "text,"
    
    # 修复句号在引号外的情况："\. → ."
    text = re.sub(r'"\.', '."', text)
    # 修复逗号在引号外的情况：", → ,"
    text = re.sub(r'",', ',"', text)
    
    return text


def fix_colon_capitalization(text: str) -> str:
    """修复冒号后独立句子的首字母大写"""
    # 规则：冒号后若为独立完整句子，句子首字母需大写
    # 匹配冒号后跟空格和小写字母的情况
    def capitalize_after_colon(match):
        return match.group(1) + match.group(2).upper()
    
    # 只处理冒号后看起来像完整句子的情况（后面有主语+动词的模式）
    # 简化处理：冒号后如果是小写字母开头，且后面有句号，则大写
    lines = text.split('\n')
    result = []
    for line in lines:
        # 跳过列表小标题行（- **Title**: content 格式）
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            result.append(line)
            continue
        # 处理其他行中的冒号后大写
        # 匹配 ": a" 这种模式，但要排除列表小标题
        line = re.sub(r'(:\s+)([a-z])', capitalize_after_colon, line)
        result.append(line)
    return '\n'.join(result)


def fix_taiwan_reference(text: str) -> str:
    """修复 Taiwan 引用：必须加上 China"""
    # 匹配独立的 Taiwan（不是已经有 China 的情况）
    # 排除已经是 Taiwan, China 或 Taiwan region of China 的情况
    text = re.sub(r'\bTaiwan\b(?!\s*,?\s*China)(?!\s+region)', 'Taiwan, China', text)
    return text


def fix_colon_after_no_content(text: str) -> str:
    """移除列表项末尾无后续内容时的冒号"""
    lines = text.split('\n')
    result = []
    for i, line in enumerate(lines):
        # 检查是否是列表项且以冒号结尾
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:\s*$', line):
            # 移除末尾冒号
            line = re.sub(r':\s*$', '', line)
        result.append(line)
    return '\n'.join(result)


def fix_bold_in_content(text: str) -> str:
    """
    检测并移除正文中的加粗（保留列表小标题的加粗）
    注意：这个函数只做检测，不自动修复，因为可能误伤
    """
    # 这个功能比较复杂，暂时只在分析中检测，不自动修复
    return text


# ==================== 主修复函数 ====================

def fix_all_format(text: str) -> str:
    """应用所有格式修复"""
    text = fix_note_format(text)
    text = fix_highlight_spaces(text)
    text = fix_period_position(text)
    text = fix_list_item_period(text)
    text = fix_secondary_list_indent(text)
    text = fix_chinese_punctuation(text)
    text = fix_spacing_rules(text)
    text = fix_hyphen_spaces(text)
    text = fix_single_asterisk_symbol(text)
    text = fix_title_case(text)
    text = fix_backticks_and_asterisks(text)
    text = fix_semicolon_sentences(text)
    text = fix_quote_punctuation(text)
    text = fix_colon_capitalization(text)
    text = fix_taiwan_reference(text)
    text = fix_colon_after_no_content(text)
    return text


# ==================== 分析函数 ====================

def analyze_format_issues(text: str) -> list:
    """分析文本中的格式问题，返回问题列表（包含具体位置）"""
    issues = []
    lines = text.split('\n')
    
    # ===== 可自动修复的问题 =====
    
    # 检查引用格式
    for i, line in enumerate(lines, 1):
        matches = re.findall(r'\[Note\d+\]', line)
        if matches:
            issues.append(f"第{i}行：引用格式错误 {matches} → 应为 [Note X]")
            break
    
    # 检查 *** 内多余空格
    for i, line in enumerate(lines, 1):
        if re.search(r'\s+\*\*\*[.\[]', line):
            issues.append(f"第{i}行：*** 内有多余空格")
            break
    
    # 检查反引号
    for i, line in enumerate(lines, 1):
        match = re.search(r'`([^`]+)`', line)
        if match:
            issues.append(f"第{i}行：反引号 `{match.group(1)}` 应改为双引号")
            break
    
    # 检查单星号（排除多星号）
    for i, line in enumerate(lines, 1):
        match = re.search(r'(?<!\*)\*([^*]+)\*(?!\*)', line)
        if match:
            issues.append(f"第{i}行：单星号 *{match.group(1)}* 应改为双引号")
            break
    
    # 检查分号连接句子
    for i, line in enumerate(lines, 1):
        if re.search(r';\s+[A-Z]', line):
            issues.append(f"第{i}行：分号连接句子，应改为句号")
            break
    
    # 检查中文标点（使用全局定义的中文标点字典，不包括英文直引号）
    for i, line in enumerate(lines, 1):
        for cn, en in CHINESE_PUNCTUATION.items():
            if cn in line:
                # 找到具体位置
                pos = line.index(cn)
                context = line[max(0, pos-10):pos+15]
                issues.append(f"第{i}行：中文标点「{cn}」应改为「{en}」，上下文：...{context}...")
                break
        else:
            continue
        break
    
    # 检查连字符空格
    for i, line in enumerate(lines, 1):
        match = re.search(r'(\w+)\s+-\s+(\w+)', line)
        if match:
            issues.append(f"第{i}行：连字符有空格「{match.group(0)}」应为「{match.group(1)}-{match.group(2)}」")
            break
    
    # 检查 Taiwan 引用
    for i, line in enumerate(lines, 1):
        if re.search(r'\bTaiwan\b(?!\s*,?\s*China)(?!\s+region)', line):
            issues.append(f"第{i}行：Taiwan 需加上 China")
            break
    
    # 检查单个 ※ 符号
    for i, line in enumerate(lines, 1):
        if '※' in line:
            issues.append(f"第{i}行：存在禁止的 ※ 符号")
            break
    
    # 检查四级标题 Title Case
    for i, line in enumerate(lines, 1):
        h4_match = re.match(r'^####\s+(.+)$', line)
        if h4_match:
            title = h4_match.group(1)
            words = title.split()
            lowercase_exceptions = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
            for w in words:
                if w and w[0].islower() and w.lower() not in lowercase_exceptions:
                    issues.append(f"第{i}行：四级标题未使用 Title Case「{title}」")
                    break
            break
    
    # 检查空格规则（排除缩写如 U.S. U.K. e.g. i.e. etc.）
    for i, line in enumerate(lines, 1):
        # 先排除常见缩写
        temp_line = re.sub(r'\b[A-Z]\.[A-Z]\.', '', line)  # U.S. U.K. 等
        temp_line = re.sub(r'\b(e\.g\.|i\.e\.|etc\.|vs\.|Dr\.|Mr\.|Mrs\.|Ms\.|Jr\.|Sr\.)', '', temp_line)
        match = re.search(r'([.,:])[A-Za-z]', temp_line)
        if match:
            issues.append(f"第{i}行：标点「{match.group(1)}」后缺少空格")
            break
    
    # 检查引号内标点位置
    for i, line in enumerate(lines, 1):
        # 检查句号在引号外：".
        match = re.search(r'([^"]{0,20})"\.\s*', line)
        if match:
            context = match.group(0)
            issues.append(f"第{i}行：句号应在引号内，上下文：...{context}...")
            break
        # 检查逗号在引号外：",
        match = re.search(r'([^"]{0,20})",\s*', line)
        if match:
            context = match.group(0)
            issues.append(f"第{i}行：逗号应在引号内，上下文：...{context}...")
            break
    
    # 检查冒号后小写
    for i, line in enumerate(lines, 1):
        if not re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            match = re.search(r':\s+([a-z])', line)
            if match:
                issues.append(f"第{i}行：冒号后「{match.group(1)}」应大写")
                break
    
    # ===== 需要AI判断的问题 =====
    
    # 检查首段是否有第二句
    first_para_match = re.match(r'^[^#\n]+', text)
    if first_para_match:
        first_para = first_para_match.group()
        after_highlight = re.search(r'\*\*\*([^*\[]+)(?:\[|$)', first_para)
        if after_highlight:
            extra_content = after_highlight.group(1).strip()
            if extra_content and extra_content not in ['.', '。']:
                issues.append(f"⚠️ 第1行：首段 *** 后有额外内容「{extra_content[:30]}...」")
    
    # 检查主语是否有引号
    if re.match(r'^"[^"]+"\s+(is|are|refers)', text):
        issues.append("⚠️ 第1行：首段主语有引号（需AI判断是否为作品名）")
    
    # 检查四级标题下是否只有一项
    sections = re.split(r'(####\s+[^\n]+)', text)
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            title = sections[i]
            content = sections[i + 1]
            list_items = re.findall(r'^-\s+\*\*[^*]+\*\*:', content, re.MULTILINE)
            if len(list_items) == 1:
                issues.append(f"⚠️「{title.strip()}」下只有1个列表项（需AI判断）")
    
    # 检查四级标题后是否紧跟列表
    for i, line in enumerate(lines, 1):
        if line.startswith('####'):
            if i < len(lines):
                next_line = lines[i].lstrip() if i < len(lines) else ""
                if next_line and not re.match(r'^[-\d]', next_line):
                    issues.append(f"⚠️ 第{i}行：「{line.strip()}」后不是列表")
                    break
    
    # 检查正文加粗（排除列表小标题）
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            continue
        match = re.search(r'(?<!\*)\*\*(?!\*)([^*]+)(?<!\*)\*\*(?!\*)', line)
        if match and not re.search(r'\*\*[^*]+\*\*:', line):
            issues.append(f"⚠️ 第{i}行：正文中有加粗「**{match.group(1)}**」")
            break
    
    # 检查废话开场白
    bad_openings = [
        'Based on the search results',
        'According to the documents',
        'According to the search',
        'Based on the information',
    ]
    for pattern in bad_openings:
        if pattern.lower() in text.lower():
            for i, line in enumerate(lines, 1):
                if pattern.lower() in line.lower():
                    issues.append(f"⚠️ 第{i}行：存在废话开场白「{pattern}」")
                    break
            break
    
    # 检查跨平台引流（社交媒体账号）
    for i, line in enumerate(lines, 1):
        match = re.search(r'@\w+', line)
        if match:
            issues.append(f"⚠️ 第{i}行：可能存在跨平台引流「{match.group(0)}」")
            break
    
    return issues


# ==================== 测试代码 ====================

if __name__ == "__main__":
    test_text = """Bbia is ***a cosmetics brand***.[Note1][Note3]

#### product characteristics
- **extensive color range**: The blush balms offer a wide selection; They come in many colors.[Note1]
- **Texture and Finish**: The product provides a `dewy` finish *** .[Note1][Note3]

#### Single Item
- **Only One**: This is the only item here.[Note2]
"""
    
    print("=== 原文 ===")
    print(test_text)
    
    print("\n=== 格式问题分析 ===")
    issues = analyze_format_issues(test_text)
    for issue in issues:
        print(f"  {issue}")
    
    print("\n=== 修复后 ===")
    fixed = fix_all_format(test_text)
    print(fixed)
