"""
API 调用模块
包含 API 配置和调用函数
"""

import requests
import time

# 默认 API 配置
DEFAULT_API_URL = "https://nvewvip.preview.tencent-zeabur.cn/v1/chat/completions"
DEFAULT_API_KEY = "sk-mw0pY9lLORPwuDBab3CYIlzgnJLZO4zgj0kYn7wJ8NVOZjpi"

# 默认模型配置
DEFAULT_MODEL = "gemini-3-pro-preview-search"  # 通用默认
DEFAULT_MODEL_EDIT = "gemini-3-pro-preview-search"  # 深度修改
DEFAULT_MODEL_TRANSLATE = "gemini-3-flash-preview-nothinking"  # 翻译
DEFAULT_MODEL_QC = "gemini-3-pro-preview-search"  # AI质检


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
                time.sleep(2 * (attempt + 1))
    
    return f"API 调用失败 (重试{max_retries}次后): {str(last_error)}", False, {}
