"""
格式自动修复工具
用于修复 format_only_rules.md 中程序可自动处理的格式问题
"""

import re


# ==================== 基础修复函数 ====================

def fix_note_format(text: str) -> str:
    """修复引用格式：
    0. [Note 3, Note 5] → [Note 3](#)[Note 5](#)（逗号分隔的引用拆分）
    1. [Note1] → [Note 1]（数字前加空格）
    2. 内容.[Note X](#) → 内容 [Note X](#).（引用移到句号前，加空格）
    3. 内容[Note X](#). → 内容 [Note X](#).（引用前加空格）
    4. 首段 ***. [Note] → *** [Note].（*** 后的引用格式）
    5. 引号结尾 "内容." [Note] → "内容" [Note].（句号移到引号外、引用后）
    """
    # 步骤0：修复逗号分隔的引用 [Note 3, Note 5, Note 12] → [Note 3](#)[Note 5](#)[Note 12](#)
    def expand_comma_notes(match):
        content = match.group(1)  # 如 "Note 3, Note 5, Note 12"
        # 提取所有 Note 数字
        notes = re.findall(r'Note\s*(\d+)', content)
        return ''.join(f'[Note {n}](#)' for n in notes)
    text = re.sub(r'\[(Note\s*\d+(?:\s*,\s*Note\s*\d+)+)\]', expand_comma_notes, text)
    
    # 步骤1：修复 [Note1] → [Note 1]
    text = re.sub(r'\[Note(\d+)\]', r'[Note \1]', text)
    
    # 步骤2：将 .[Note X](#) 改为 [Note X](#).（引用移到句号前）
    # 匹配：句号后紧跟一个或多个 [Note X](#)
    def move_notes_before_period(match):
        notes = match.group(1)  # 所有的 [Note X](#) 部分
        return ' ' + notes + '.'
    text = re.sub(r'\.(\[Note\s*\d+\]\(#\)(?:\[Note\s*\d+\]\(#\))*)', move_notes_before_period, text)
    
    # 步骤3：修复首段 ***. [Note] → *** [Note].
    # 匹配：***. 后面跟着空格和引用
    def fix_highlight_notes(match):
        notes = match.group(1)  # 所有的 [Note X](#) 部分
        return '*** ' + notes + '.'
    text = re.sub(r'\*\*\*\.\s*(\[Note\s*\d+\]\(#\)(?:\[Note\s*\d+\]\(#\))*)', fix_highlight_notes, text)
    
    # 步骤4：修复引号结尾 "内容." [Note] → "内容" [Note].
    # 匹配：引号内句号 + 引号 + 空格 + 引用（没有句号结尾）
    def fix_quote_ending(match):
        content = match.group(1)  # 引号前的内容
        notes = match.group(2)  # 所有的 [Note X](#) 部分
        return content + '" ' + notes + '.'
    # 匹配 ." [Note...]（引号内有句号，且后面没有句号）
    text = re.sub(r'([^"]+)\.\"\s*(\[Note\s*\d+\]\(#\)(?:\[Note\s*\d+\]\(#\))*)(?!\.)', fix_quote_ending, text)
    
    # 步骤5：修复引号+星号 ".*** [Note] → "*** [Note].
    # 匹配：引号 + 句号 + *** + 空格 + 引用
    def fix_quote_star_ending(match):
        notes = match.group(1)  # 所有的 [Note X](#) 部分
        return '"*** ' + notes + '.'
    text = re.sub(r'"\.\*\*\*\s*(\[Note\s*\d+\]\(#\)(?:\[Note\s*\d+\]\(#\))*)(?!\.)', fix_quote_star_ending, text)
    
    # 步骤6：确保引用前有空格（如果前面是字母/数字/引号/***，但不是另一个引用）
    # 排除 )[Note 的情况（这是连续引用）
    text = re.sub(r'([^\s\)])\[Note\s', r'\1 [Note ', text)
    
    # 步骤7：修复段中note - 将段落中间的引用移到段落末尾
    # 匹配：引用后面还有内容，然后以句号结尾
    # 例如：The product [Note 1](#) is good. → The product is good [Note 1](#).
    def move_mid_note_to_end(match):
        before_note = match.group(1)  # 引用前的内容
        notes = match.group(2)  # 引用（可能有多个）
        after_note = match.group(3)  # 引用后、句号前的内容
        # 将引用移到句号前，确保空格正确
        return before_note.rstrip() + ' ' + after_note.strip() + ' ' + notes + '.'
    # 匹配模式：内容 + 引用 + 更多内容 + 句号
    text = re.sub(
        r'([^.]+?)\s*(\[Note\s*\d+\]\(#\)(?:\[Note\s*\d+\]\(#\))*)\s+([A-Za-z][^.]*)\.',
        move_mid_note_to_end,
        text
    )
    
    # 步骤8：去除重复的Note引用
    # 匹配连续的相同引用，只保留一个
    # 例如：[Note 1](#)[Note 1](#) → [Note 1](#)
    def remove_duplicate_notes(line):
        # 找到所有 [Note X](#) 引用
        notes = re.findall(r'\[Note\s*(\d+)\]\(#\)', line)
        if not notes:
            return line
        # 按顺序去重（保持第一次出现的顺序）
        seen = set()
        unique_notes = []
        for n in notes:
            if n not in seen:
                seen.add(n)
                unique_notes.append(n)
        # 如果没有重复，直接返回
        if len(notes) == len(unique_notes):
            return line
        # 重建引用部分
        new_notes = ''.join(f'[Note {n}](#)' for n in unique_notes)
        # 替换原有的所有连续引用
        line = re.sub(r'(\[Note\s*\d+\]\(#\))+', new_notes, line, count=1)
        return line
    
    lines = text.split('\n')
    text = '\n'.join(remove_duplicate_notes(line) for line in lines)
    
    return text


def fix_highlight_spaces(text: str) -> str:
    """修复 *** 内的多余空格"""
    # 修复结尾空格：*** *** → ******
    text = re.sub(r'\*\*\*\s+\*\*\*', '******', text)
    # 修复高亮内结尾空格：word *** → word***
    text = re.sub(r'\s+\*\*\*\.', '***.', text)
    text = re.sub(r'\s+\*\*\*(\[)', r'***\1', text)
    return text


def fix_period_position(text: str) -> str:
    """修复首段句号位置：句号应在***外面（但引号内的句号保留）"""
    # 修复：内容。*** → 内容***。 的情况（中文句号）
    text = re.sub(r'。\*\*\*', '***。', text)
    # 修复：内容.*** → 内容***. 的情况（英文句号，非引号结尾）
    # 注意：不处理 "text."*** 这种情况，因为引号内句号是正确的
    text = re.sub(r'([^""])\.(\*\*\*)', r'\1\2.', text)
    return text


def fix_title_case_in_parentheses(text: str) -> str:
    """修复小标题和四级标题中括号内容的Title Case
    例如：**Old Bund (lao Waitan)**: → **Old Bund (Lao Waitan)**:
    """
    # 定义介词和冠词（这些词不需要首字母大写，除非是括号开头）
    minor_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'by', 'of', 'in', 'with', 'as'}
    
    def title_case_word(word, is_first):
        """将单词转为Title Case，考虑介词规则"""
        if not word:
            return word
        # 如果是第一个词，或者不是介词/冠词，则首字母大写
        if is_first or word.lower() not in minor_words:
            return word[0].upper() + word[1:] if len(word) > 1 else word.upper()
        return word.lower()
    
    def fix_parentheses_content(match):
        """修复括号内容"""
        prefix = match.group(1)  # 括号前的内容
        content = match.group(2)  # 括号内的内容
        suffix = match.group(3)  # 括号后的内容（如 **: 或 **:）
        
        # 将括号内容按空格分割，逐词处理Title Case
        words = content.split()
        fixed_words = [title_case_word(w, i == 0) for i, w in enumerate(words)]
        fixed_content = ' '.join(fixed_words)
        
        return f'{prefix}({fixed_content}){suffix}'
    
    # 匹配小标题中的括号：**Title (content)**: 或 **Title (content)**:
    # 以及四级标题中的括号：#### Title (content)
    text = re.sub(r'(\*\*[^*]+)\(([^)]+)\)(\*\*:?)', fix_parentheses_content, text)
    text = re.sub(r'(#### [^(\n]+)\(([^)]+)\)', fix_parentheses_content, text)
    
    return text


def fix_list_item_period(text: str) -> str:
    """修复列表项末尾缺少句号"""
    lines = text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        # 检查是否是列表项（以 - 或数字. 开头）
        if re.match(r'^[\s]*[-\d]+\.?\s', line):
            stripped = line.rstrip()
            
            # 检查下一行是否是二级列表（有前导空格 + -）
            # 如果是，则当前行应该以冒号结尾，不需要加句号
            next_is_secondary_list = False
            if i + 1 < len(lines) and re.match(r'^\s+-', lines[i + 1]):
                next_is_secondary_list = True
            
            # 如果后面跟着二级列表，跳过（让 fix_list_item_colon 处理）
            if next_is_secondary_list:
                result.append(line)
                continue
            
            # 如果末尾是引用，检查引用前是否有句号
            if re.search(r'\[Note\s*\d+\](\(#\))?$', stripped):
                match = re.search(r'(\[Note\s*\d+\](\(#\))?)+$', stripped)
                if match:
                    before_notes = stripped[:match.start()]
                    notes = stripped[match.start():]
                    # 检查是否以句号结尾，包括 ." 和 .) 这种引号/括号内句号的情况
                    if before_notes and not re.search(r'[.。!?！？]["\')]?$', before_notes.rstrip()):
                        line = before_notes.rstrip() + '.' + notes
            # 检查是否以句号结尾，包括 ." 和 .) 这种引号/括号内句号的情况
            elif stripped and not re.search(r'[.。!?！？:：]["\')]?$', stripped):
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
    # 清理行内多余空格（保留行首缩进）
    lines = text.split('\n')
    result = []
    for line in lines:
        # 保留行首缩进
        leading_spaces = len(line) - len(line.lstrip())
        indent = line[:leading_spaces]
        content = line[leading_spaces:]
        # 只清理内容部分的多余空格
        content = re.sub(r'  +', ' ', content)
        result.append(indent + content)
    return '\n'.join(result)


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
    """修复空格规则：句号/逗号后空格、括号空格、冒号前后空格"""
    # 冒号前移除多余空格（如 "A : B" → "A: B"）
    text = re.sub(r'\s+:', ':', text)
    # 句号后加空格（排除以下情况）：
    # 1. 域名如 .com, .org
    # 2. 缩写如 U.S., e.g., i.e.
    # 先保护域名
    text = re.sub(r'\.(com|org|net|edu|gov|io|co|uk|cn)\b', r'.__DOMAIN_\1__', text)
    # 保护缩写（单个大写字母+句号+大写字母，如 U.S.）
    text = re.sub(r'([A-Z])\.([A-Z])', r'\1.__ABBR__\2', text)
    # 保护常见缩写
    text = re.sub(r'\b(e\.g|i\.e|etc|vs|Dr|Mr|Mrs|Ms|Jr|Sr|St)\b', lambda m: m.group(0).replace('.', '.__ABBR__'), text)
    # 句号后加空格
    text = re.sub(r'\.([A-Za-z])', r'. \1', text)
    # 恢复保护的内容
    text = re.sub(r'\.__DOMAIN_(\w+)__', r'.\1', text)
    text = re.sub(r'\.__ABBR__', '.', text)
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
    """只在首段将分号改为句号，其他地方保留分号"""
    lines = text.split('\n')
    if not lines:
        return text
    
    # 只处理首段（第一行，且不是标题或列表）
    first_line = lines[0]
    if not first_line.startswith('#') and not first_line.startswith('-'):
        # 匹配分号后跟空格和字母（不限大小写）
        first_line = re.sub(r';\s+([A-Za-z])', r'. \1', first_line)
        lines[0] = first_line
    
    return '\n'.join(lines)


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
    """修复冒号后首字母大写（包括列表小标题后的内容）"""
    # 规则：冒号后若有内容，首字母需大写
    def capitalize_after_colon(match):
        return match.group(1) + match.group(2).upper()
    
    lines = text.split('\n')
    result = []
    for line in lines:
        # 所有行都处理冒号后首字母大写
        # 匹配 ": a" 这种模式（冒号后跟空格和小写字母）
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


def fix_list_item_colon(text: str) -> str:
    """修复一级列表项缺少冒号的情况：
    1. 后面有二级列表但缺少冒号
    2. 小标题后直接跟内容但缺少冒号
    """
    lines = text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        # 情况1：一级列表项后跟二级列表（以 - **xxx** 结尾，没有冒号）
        match1 = re.match(r'^(-\s+\*\*[^*]+\*\*)(\s*)$', line)
        if match1:
            # 检查下一行是否是二级列表（有前导空格 + -）
            if i + 1 < len(lines) and re.match(r'^\s+-', lines[i + 1]):
                # 后面跟着二级列表，添加冒号
                line = match1.group(1) + ':'
        
        # 情况2：一级列表项小标题后直接跟内容但缺少冒号
        # 错误格式：- **Sizing Advice** Some users report...
        # 正确格式：- **Sizing Advice**: Some users report...
        match2 = re.match(r'^(-\s+\*\*[^*]+\*\*)(\s+)([^:\s].*)$', line)
        if match2:
            # 在 ** 后添加冒号
            line = match2.group(1) + ':' + match2.group(2) + match2.group(3)
        
        result.append(line)
    
    return '\n'.join(result)


def fix_bold_in_content(text: str) -> str:
    """
    检测并移除正文中的加粗（保留列表小标题的加粗）
    注意：这个函数只做检测，不自动修复，因为可能误伤
    """
    # 这个功能比较复杂，暂时只在分析中检测，不自动修复
    return text


def fix_paragraph_spacing(text: str) -> str:
    """
    修复空行问题：
    1. 首段与正文之间、四级标题与四级标题/免责声明之间：强制空2行
    2. 四级标题与其下方的列表：强制无空行
    3. 列表项之间：强制无空行
    """
    lines = text.split('\n')
    # 第一步：清理原有的多余空行，生成初步的处理列表
    # 我们遍历每一行，同时判断上下文来决定保留多少空行
    
    clean_lines = []
    
    # 免责声明模式
    disclaimer_patterns = [
        r'^The above content is for reference only',
        r'^This information is for entertainment purposes only',
        r'^please consult a professional',
    ]
    
    for i, line in enumerate(lines):
        clean_lines.append(line)
    
    # 使用状态机思想重新构建文本
    final_lines = []
    i = 0
    n = len(lines)
    
    while i < n:
        line = lines[i]
        stripped = line.strip()
        
        # 存入当前行
        final_lines.append(line)
        
        # 预读下一行非空内容
        next_content_idx = -1
        next_content_line = ""
        empty_lines_count = 0
        
        j = i + 1
        while j < n:
            if lines[j].strip():
                next_content_idx = j
                next_content_line = lines[j].strip()
                break
            empty_lines_count += 1
            j += 1
        
        # 如果后面没有内容了，结束循环
        if next_content_idx == -1:
            break
            
        # 判断当前行类型
        is_core_end = ('***' in stripped and stripped.endswith('.'))
        is_h4 = stripped.startswith('####')
        is_list_item = (stripped.startswith('- ') or stripped.startswith('1.') or 
                       (stripped and not is_h4 and not is_core_end))
        
        # 判断下一行类型
        next_is_h4 = next_content_line.startswith('####')
        next_is_list = (next_content_line.startswith('- ') or next_content_line.startswith('1.'))
        next_is_disclaimer = any(re.match(p, next_content_line, re.IGNORECASE) for p in disclaimer_patterns)
        
        # 决策空行数量
        target_empty_lines = -1 # -1 表示保持原样（如果不符合规则）
        
        # 规则1：首段 -> 四级标题：空2行
        if is_core_end and next_is_h4:
            target_empty_lines = 2
            
        # 规则2：四级标题 -> 列表：空0行
        elif is_h4 and next_is_list:
            target_empty_lines = 0
            
        # 规则3：列表项 -> 四级标题 或 免责声明：空2行
        elif is_list_item and (next_is_h4 or next_is_disclaimer):
            target_empty_lines = 2
            
        # 规则4：列表项 -> 列表项：空0行
        elif is_list_item and next_is_list:
            target_empty_lines = 0

        # 应用空行调整
        if target_empty_lines != -1:
            # 添加指定数量的空行
            for _ in range(target_empty_lines):
                final_lines.append('')
            # 跳过原文本中的空行，直接跳到下一段内容前
            i = next_content_idx - 1 # 外层循环会 +1
        
        i += 1
        
    return '\n'.join(final_lines)


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
    text = fix_title_case_in_parentheses(text)  # 修复括号内容的Title Case
    text = fix_backticks_and_asterisks(text)
    text = fix_semicolon_sentences(text)
    text = fix_quote_punctuation(text)
    text = fix_colon_capitalization(text)
    text = fix_taiwan_reference(text)
    text = fix_colon_after_no_content(text)
    text = fix_list_item_colon(text)  # 修复一级列表项缺少冒号
    text = fix_paragraph_spacing(text)  # 修复大段落间距
    return text


# ==================== 分析函数 ====================

def analyze_format_issues(text: str) -> list:
    """分析文本中的格式问题，返回问题列表（包含具体位置）"""
    issues = []
    lines = text.split('\n')
    
    # ===== 可自动修复的问题 =====
    
    # 检查引用格式（[Note1] 应为 [Note 1]）
    for i, line in enumerate(lines, 1):
        matches = re.findall(r'\[Note\d+\]', line)
        if matches:
            issues.append(f"第{i}行：引用格式错误 {matches} → 应为 [Note X]")
            break
    
    # 检查引用位置（应在句号前，而非句号后）
    for i, line in enumerate(lines, 1):
        if re.search(r'\.\[Note\s*\d+\]', line):
            issues.append(f"第{i}行：引用应在句号前，格式：内容 [Note X](#).")
            break
    
    # 检查引用前是否有空格
    for i, line in enumerate(lines, 1):
        # 排除连续引用的情况 )[Note
        if re.search(r'[^\s\)]\[Note\s', line):
            issues.append(f"第{i}行：引用前应有空格")
            break
    
    # 检查段中note（引用应在段落末尾，不应在段落中间）
    for i, line in enumerate(lines, 1):
        # 匹配：引用后面还有内容（不是句号、不是另一个引用、不是行尾）
        # 正确格式：内容 [Note X](#). 或 内容 [Note X](#)[Note Y](#).
        # 错误格式：内容 [Note X](#) 还有更多内容...
        match = re.search(r'\[Note\s*\d+\]\(#\)(?!\.)(?!\[Note)(?!$)\s*[A-Za-z]', line)
        if match:
            issues.append(f"第{i}行：引用应在段落末尾，不应在段落中间")
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
    
    # 检查分号连接句子（只检查首段）
    first_line = lines[0] if lines else ""
    if re.search(r';\s+[A-Za-z]', first_line):
        issues.append(f"第1行：首段不允许使用分号")
    
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
    
    # 检查小标题和四级标题中括号内容的 Title Case
    for i, line in enumerate(lines, 1):
        # 匹配小标题中的括号：**Title (content)**
        paren_match = re.search(r'\*\*[^*]+\(([^)]+)\)\*\*', line)
        if not paren_match:
            # 匹配四级标题中的括号：#### Title (content)
            paren_match = re.search(r'^####\s+[^(]+\(([^)]+)\)', line)
        if paren_match:
            content = paren_match.group(1)
            words = content.split()
            lowercase_exceptions = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'as'}
            for idx, w in enumerate(words):
                # 第一个词或非介词词必须首字母大写
                if w and w[0].islower() and (idx == 0 or w.lower() not in lowercase_exceptions):
                    issues.append(f"第{i}行：括号内容未使用 Title Case「({content})」→ 应为「({content.title()})」")
                    break
            break
    
    # 检查空格规则（排除缩写如 U.S. U.K. e.g. i.e. etc.）
    for i, line in enumerate(lines, 1):
        # 先排除常见缩写
        temp_line = re.sub(r'\b[A-Z]\.[A-Z]\.', '', line)  # U.S. U.K. 等
        temp_line = re.sub(r'\b(e\.g\.|i\.e\.|etc\.|vs\.|Dr\.|Mr\.|Mrs\.|Ms\.|Jr\.|Sr\.)', '', temp_line)
        # 排除 .com .org .net 等域名
        temp_line = re.sub(r'\.(com|org|net|edu|gov|io|co|uk|cn)\b', '', temp_line)
        # 检查标点后是否缺少空格，但排除标点后跟 [ 的情况（Markdown 链接）
        match = re.search(r'([.,:])[A-Za-z]', temp_line)
        if match:
            issues.append(f"第{i}行：标点「{match.group(1)}」后缺少空格")
            break
    
    # 检查引号内标点位置
    for i, line in enumerate(lines, 1):
        # 检查句号在引号外：".
        # 但排除引号内以 ? 或 ! 结尾的情况（如 "You Could Be Normal?". 是正确的）
        match = re.search(r'([^"]{0,20}[^?!])"\.', line)
        if match:
            context = match.group(0)
            issues.append(f"第{i}行：句号应在引号内，上下文：...{context}...")
            break
        # 检查逗号在引号外：",
        # 同样排除引号内以 ? 或 ! 结尾的情况
        match = re.search(r'([^"]{0,20}[^?!])",', line)
        if match:
            context = match.group(0)
            issues.append(f"第{i}行：逗号应在引号内，上下文：...{context}...")
            break
    
    # 检查冒号前多余空格（如 "A : B"）
    for i, line in enumerate(lines, 1):
        match = re.search(r'(\w)\s+:', line)
        if match:
            context = line[max(0, match.start()-10):match.end()+10]
            issues.append(f"第{i}行：冒号前有多余空格，上下文：...{context}...")
            break
    
    # 检查冒号后小写（包括列表小标题后的内容）
    for i, line in enumerate(lines, 1):
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
    
    # 检查四级标题下是否只有一项（一级列表项）
    sections = re.split(r'(####\s+[^\n]+)', text)
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            title = sections[i]
            content = sections[i + 1]
            # 匹配一级列表项：以 `- **xxx**` 开头（可能有冒号也可能没有），且没有前导空格
            # 排除二级列表（有前导空格的）
            list_items = re.findall(r'^-\s+\*\*[^*]+\*\*', content, re.MULTILINE)
            if len(list_items) == 1:
                issues.append(f"⚠️「{title.strip()}」下只有1个列表项（需AI判断）")
    
    # 检查四级标题后是否紧跟列表
    # 注意：根据规则，单项内容可以用段落形式，所以需要检查是否是单项内容的情况
    # 免责声明模式（不计入内容）
    disclaimer_patterns = [
        r'^The above content is for reference only',
        r'^This information is for entertainment purposes only',
        r'^please consult a professional',
    ]
    for i, line in enumerate(lines, 1):
        if line.startswith('####'):
            if i < len(lines):
                next_line = lines[i].lstrip() if i < len(lines) else ""
                if next_line and not re.match(r'^[-\d]', next_line):
                    # 检查这是否是"单项内容"的情况：
                    # 如果四级标题后只有一段内容（到下一个四级标题或文件结束），则允许段落形式
                    is_single_item = True
                    content_lines = 0
                    for j in range(i, len(lines)):
                        check_line = lines[j].strip()
                        if check_line.startswith('####'):
                            break  # 遇到下一个四级标题
                        # 排除免责声明
                        is_disclaimer = any(re.match(p, check_line, re.IGNORECASE) for p in disclaimer_patterns)
                        if check_line and not is_disclaimer:  # 非空行且不是免责声明
                            content_lines += 1
                            if content_lines > 1:
                                is_single_item = False
                                break
                    
                    if not is_single_item:
                        # 有多项内容但没有用列表，报错
                        issues.append(f"⚠️ 第{i}行：「{line.strip()}」后不是列表（多项内容应使用列表格式）")
                        break
                    # 单项内容用段落是允许的，不报错
    
    # 检查正文加粗（排除列表小标题）
    for i, line in enumerate(lines, 1):
        # 排除无序列表小标题：- **Title**: 或 - **Title**（无冒号）
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:?\s*$', line):
            continue
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            continue
        # 排除无序列表项开头的加粗小标题
        if re.match(r'^\s*-\s+\*\*', line):
            continue
        # 排除有序列表小标题：1. **Title**: 或 1. **Title**
        if re.match(r'^\s*\d+\.\s+\*\*[^*]+\*\*:?\s*', line):
            continue
        # 排除有序列表项开头的加粗小标题
        if re.match(r'^\s*\d+\.\s+\*\*', line):
            continue
        match = re.search(r'(?<!\*)\*\*(?!\*)([^*]+)(?<!\*)\*\*(?!\*)', line)
        if match:
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
    
    # ===== 新增可程序化检测 =====
    
    # 检查首段句号位置（句号应在 *** 外面，但引号结尾除外）
    first_line = lines[0] if lines else ""
    if '***' in first_line:
        # 错误1：.*** 且前面不是引号（句号在***内）
        if re.search(r'[^"\']\.\*\*\*', first_line):
            issues.append(f"第1行：首段句号在 *** 内，应移到 *** 外面")
        
        # 错误2：首段以引号结尾时，句号在引号外面
        # 如 ''***.[Note 或 "***.[Note（引号***后跟句号）
        # 正确应该是 .''***[Note 或 ."***[Note（句号在引号内）
        if re.search(r"['\"]''?\*\*\*\.", first_line) or re.search(r'["\']["\']?\*\*\*\.', first_line):
            issues.append(f"第1行：首段以引号结尾时，句号应在引号内（如 .''*** 而非 ''***.）")
    
    # 检查列表项缺少小标题加粗（只检查一级列表，二级列表不需要加粗）
    for i, line in enumerate(lines, 1):
        # 一级列表：以 `- ` 开头，没有前导空格
        # 二级列表：有前导空格（如 4 个空格）+ `- `，不需要加粗
        if re.match(r'^-\s+[^*\[]', line) and not re.match(r'^-\s+\*\*', line):
            # 是一级列表项但没有加粗小标题
            if not re.match(r'^-\s*$', line):  # 排除空列表项
                content = line.strip()[:40]
                issues.append(f"第{i}行：列表项缺少加粗小标题「{content}...」")
                break
    
    # 检查一级列表项后有二级列表时，一级列表项必须以冒号结尾
    for i, line in enumerate(lines, 1):
        # 匹配一级列表项（以 - **xxx** 开头，没有前导空格）
        if re.match(r'^-\s+\*\*[^*]+\*\*', line):
            # 检查下一行是否是二级列表（有前导空格 + -）
            next_line_idx = i  # i 是 1-indexed，所以 i 就是下一行的 0-indexed
            if next_line_idx < len(lines) and re.match(r'^\s+-', lines[next_line_idx]):
                # 后面跟着二级列表，检查当前行是否以冒号结尾（在 ** 之后）
                # 正确格式：- **Key Albums**:
                # 错误格式：- **Key Albums**
                if not re.search(r'\*\*:\s*$', line.rstrip()):
                    title_match = re.search(r'\*\*([^*]+)\*\*', line)
                    title = title_match.group(1) if title_match else "未知"
                    issues.append(f"第{i}行：一级列表项「{title}」后有二级列表，但缺少冒号（应为 **{title}**:）")
                    break
    
    # 检查一级列表项加粗小标题后缺少冒号（后面跟内容而不是二级列表）
    # 错误格式：- **Sizing Advice** Some users report...
    # 正确格式：- **Sizing Advice**: Some users report...
    for i, line in enumerate(lines, 1):
        # 匹配一级列表项：以 `- **xxx**` 开头，后面紧跟非冒号的内容
        match = re.match(r'^-\s+\*\*([^*]+)\*\*\s+[^:\s]', line)
        if match:
            title = match.group(1)
            issues.append(f"第{i}行：列表项「{title}」小标题后缺少冒号（应为 **{title}**:）")
            break
    
    # 检查列表项缺少引用
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            if not re.search(r'\[Note\s*\d+\]', line):
                # 检查下一行是否是二级列表（如果是，则 Note 应该在二级列表中，不报错）
                next_line_idx = i  # i 是 1-indexed，所以 i 就是下一行的 0-indexed
                if next_line_idx < len(lines) and re.match(r'^\s+-', lines[next_line_idx]):
                    # 后面跟着二级列表，Note 应该在二级列表项中，跳过检查
                    continue
                title_match = re.search(r'\*\*([^*]+)\*\*', line)
                title = title_match.group(1) if title_match else "未知"
                issues.append(f"第{i}行：列表项「{title}」缺少 Note 引用")
                break
    
    # 检查列表项末尾缺少句号
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:', line):
            stripped = line.rstrip()
            # 如果末尾是引用，检查引用前
            note_match = re.search(r'(\[Note\s*\d+\](\(#\))?)+$', stripped)
            if note_match:
                before_note = stripped[:note_match.start()].rstrip()
                # 检查是否以句号结尾，包括 ." 和 .) 这种引号/括号内句号的情况
                if before_note and not re.search(r'[.!?]["\')]?$', before_note):
                    # 显示引用前的内容片段
                    context = before_note[-30:] if len(before_note) > 30 else before_note
                    issues.append(f"第{i}行：列表项引用前缺少句号，上下文：...{context}[Note...]")
                    break
            elif stripped and not re.search(r'[.!?:]["\')]?$', stripped):
                # 显示行末内容
                context = stripped[-40:] if len(stripped) > 40 else stripped
                issues.append(f"第{i}行：列表项末尾缺少句号，上下文：...{context}")
                break
    
    # 检查平台特定称呼
    platform_terms = ['薯宝', '薯友', '家人们', '宝子', '姐妹们']
    for i, line in enumerate(lines, 1):
        for term in platform_terms:
            if term in line:
                issues.append(f"第{i}行：存在平台特定称呼「{term}」")
                break
        else:
            continue
        break
    
    # 检查首段是否有 *** 高亮
    if lines and not re.search(r'\*\*\*', lines[0]):
        if re.match(r'^[A-Za-z""]', lines[0]):  # 看起来像首段
            issues.append(f"第1行：首段缺少 *** 高亮")
    
    # 检查首段冠词是否在 *** 外
    if '***' in first_line:
        # 检查 is/are *** a/an/the 的情况（冠词应在 *** 内）
        if re.search(r'(is|are|refers to)\s+\*\*\*\s*(a|an|the)\b', first_line, re.IGNORECASE):
            pass  # 正确
        elif re.search(r'(is|are|refers to)\s+(a|an|the)\s+\*\*\*', first_line, re.IGNORECASE):
            issues.append(f"第1行：冠词应在 *** 内部")
    
    # ===== 更多可程序化检测 =====
    
    # 检查系动词是否在 *** 内（应在外）
    if '***' in first_line:
        if re.search(r'\*\*\*\s*(is|are|was|were|refers? to)', first_line, re.IGNORECASE):
            issues.append(f"第1行：系动词应在 *** 外部")
    
    # 检查四级标题后有冒号（标题后跟列表时不应有冒号）
    for i, line in enumerate(lines, 1):
        if re.match(r'^####\s+.+:\s*$', line):
            # 检查下一行是否是列表
            if i < len(lines) and re.match(r'^\s*[-\d]', lines[i]):
                issues.append(f"第{i}行：四级标题后跟列表时不应有冒号")
                break
    
    # 检查二级列表缩进（应为4空格）
    for i, line in enumerate(lines, 1):
        match = re.match(r'^(\s+)-\s', line)
        if match:
            indent = len(match.group(1))
            if indent > 0 and indent != 4:
                issues.append(f"第{i}行：二级列表缩进应为4空格，当前为{indent}空格")
                break
    
    # 检查 emoji 作为列表符号
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*[\U0001F300-\U0001F9FF]', line):
            issues.append(f"第{i}行：禁止使用 emoji 作为列表符号")
            break
    
    # 检查1级数字+2级数字（禁止）
    in_numbered_list = False
    for i, line in enumerate(lines, 1):
        if re.match(r'^\d+\.\s', line):
            in_numbered_list = True
        elif re.match(r'^\s+\d+\.\s', line) and in_numbered_list:
            issues.append(f"第{i}行：禁止1级数字列表下使用2级数字列表")
            break
        elif re.match(r'^[^0-9\s]', line):
            in_numbered_list = False
    
    # 检查中文字符（英文回答中不应有中文）
    for i, line in enumerate(lines, 1):
        # 排除平台称呼检测（已单独检测）
        if re.search(r'[\u4e00-\u9fff]', line):
            # 找到具体的中文字符
            match = re.search(r'[\u4e00-\u9fff]+', line)
            if match:
                chinese_text = match.group(0)
                # 排除已检测的平台称呼
                if chinese_text not in ['薯宝', '薯友', '家人们', '宝子', '姐妹们']:
                    issues.append(f"第{i}行：英文回答中存在中文「{chinese_text}」")
                    break
    
    # 检查引用堆砌在末尾（多个连续引用在最后一行）
    if lines:
        last_line = lines[-1].strip()
        note_count = len(re.findall(r'\[Note\s*\d+\]', last_line))
        if note_count >= 5:
            issues.append(f"第{len(lines)}行：可能存在引用堆砌（{note_count}个引用）")
    
    # 检查列表小标题 Title Case
    for i, line in enumerate(lines, 1):
        match = re.match(r'^\s*-\s+\*\*([^*:]+)\*\*:', line)
        if match:
            title = match.group(1)
            words = title.split()
            lowercase_exceptions = {'a', 'an', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
            for w in words:
                if w and w[0].islower() and w.lower() not in lowercase_exceptions:
                    issues.append(f"第{i}行：列表小标题未使用 Title Case「{title}」")
                    break
            else:
                continue
            break
    
    # ===== 最后一批可程序化检测 =====
    
    # 检查括号空格（左括号前、右括号后）
    for i, line in enumerate(lines, 1):
        # 左括号前缺空格：word(
        if re.search(r'[A-Za-z]\(', line):
            issues.append(f"第{i}行：左括号前缺少空格")
            break
        # 右括号后缺空格：)word
        if re.search(r'\)[A-Za-z]', line):
            issues.append(f"第{i}行：右括号后缺少空格")
            break
    
    # 检查引用在句号前（应在句号后）
    for i, line in enumerate(lines, 1):
        if re.search(r'\[Note\s*\d+\]\s*\.', line):
            issues.append(f"第{i}行：引用应在句号后，不是句号前")
            break
    
    # 检查段中有 Note（Note 应在段末，Note 后不能再有其他文字）
    # 错误：Sentence A.[Note 1](#) Sentence B.
    # 正确：Sentence A. Sentence B.[Note 1](#)
    for i, line in enumerate(lines, 1):
        # 匹配 [Note X](#) 后面跟着非 Note 的内容（排除空格、换行、更多 Note）
        # 模式：[Note X](#) 后面有字母或数字开头的内容
        match = re.search(r'\[Note\s*\d+\](\(#\))?\s+[A-Za-z0-9]', line)
        if match:
            # 找到具体位置用于显示上下文
            context_start = max(0, match.start() - 20)
            context_end = min(len(line), match.end() + 20)
            context = line[context_start:context_end]
            issues.append(f"第{i}行：Note 引用应在段末，引用后不能有其他内容，上下文：...{context}...")
            break
    
    # 检查一级列表有二级列表时，一级标题后有非冒号内容
    for i, line in enumerate(lines, 1):
        # 检查是否是一级列表项
        if re.match(r'^-\s+\*\*[^*]+\*\*:', line):
            # 检查冒号后是否有内容（除了空格）
            after_colon = re.search(r'\*\*:\s*(.+)$', line)
            if after_colon and after_colon.group(1).strip():
                # 检查下一行是否是二级列表
                if i < len(lines) and re.match(r'^\s+-', lines[i]):
                    content = after_colon.group(1).strip()[:20]
                    issues.append(f"第{i}行：有二级列表时，一级标题后只能有冒号，不能有「{content}...」")
                    break
    
    # 检查无后续内容时有冒号（列表项末尾只有冒号）
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*-\s+\*\*[^*]+\*\*:\s*$', line):
            # 检查下一行是否是二级列表
            if i >= len(lines) or not re.match(r'^\s+-', lines[i]):
                title_match = re.search(r'\*\*([^*]+)\*\*', line)
                title = title_match.group(1) if title_match else "未知"
                issues.append(f"第{i}行：列表项「{title}」无后续内容时不应有冒号")
                break
    
    # 检查术语一致性（U.S. vs US）
    us_dot = len(re.findall(r'\bU\.S\.', text))
    us_no_dot = len(re.findall(r'\bUS\b', text))
    if us_dot > 0 and us_no_dot > 0:
        issues.append(f"术语不一致：同时使用了 U.S.（{us_dot}次）和 US（{us_no_dot}次）")
    
    # 检查首段后直接接四级标题（应有解释文字）
    if len(lines) >= 2:
        first_line = lines[0]
        second_line = lines[1] if len(lines) > 1 else ""
        # 首段有 *** 且第二行是四级标题
        if '***' in first_line and second_line.startswith('####'):
            issues.append(f"第2行：首段后直接接四级标题，应有解释文字")
    
    # 检查大段落间距：主要内容板块之间应空两行
    # 检测模式：首段 → 正文、四级标题 → 四级标题、正文 → 免责声明
    disclaimer_patterns = [
        r'^The above content is for reference only',
        r'^This information is for entertainment purposes only',
        r'^please consult a professional',
    ]
    
    for i in range(len(lines) - 1):
        current_line = lines[i].strip()
        next_idx = i + 1
        
        # 跳过空行
        if not current_line:
            continue
        
        # 情况1：首段（包含 ***）后面应该空两行再接四级标题
        if '***' in current_line and current_line.endswith('.'):
            # 查找下一个非空内容
            empty_count = 0
            for j in range(next_idx, min(next_idx + 5, len(lines))):
                if not lines[j].strip():
                    empty_count += 1
                elif lines[j].strip().startswith('####'):
                    if empty_count < 2:
                        issues.append(f"第{i+1}行：首段与正文之间应空两行（当前只有{empty_count}个空行）")
                    break
                else:
                    break
        
        # 情况2：四级标题内容结束后，下一个四级标题前应空两行
        if current_line.startswith('####'):
            # 找到这个四级标题的内容结束位置
            content_end = next_idx
            for j in range(next_idx, len(lines)):
                line_j = lines[j].strip()
                if line_j.startswith('####') or any(re.match(p, line_j, re.IGNORECASE) for p in disclaimer_patterns):
                    break
                if line_j:  # 非空行
                    content_end = j
            
            # 检查 content_end 到下一个四级标题/免责声明之间的空行数
            if content_end < len(lines) - 1:
                empty_count = 0
                for j in range(content_end + 1, min(content_end + 5, len(lines))):
                    line_j = lines[j].strip()
                    if not line_j:
                        empty_count += 1
                    elif line_j.startswith('####'):
                        if empty_count < 2:
                            issues.append(f"第{content_end + 1}行：四级标题之间应空两行（当前只有{empty_count}个空行）")
                        break
                    elif any(re.match(p, line_j, re.IGNORECASE) for p in disclaimer_patterns):
                        if empty_count < 2:
                            issues.append(f"第{j + 1}行：正文与免责声明之间应空两行（当前只有{empty_count}个空行）")
                        break
                    else:
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
