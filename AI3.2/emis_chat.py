#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emis_chat.py
==============
爱弥斯 (Emis) 角色文本生成模块
基于 llama_cpp + Qwen2.5-14B-Instruct-Q6_K.gguf

职责：只负责生成爱弥斯风格的回复文本，不处理语音、不启动服务。
"""
import gc
from pathlib import Path
import sys, re
from llama_cpp import Llama

def get_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        # 当前文件在 ui 下，上一级是根目录
        return Path(__file__).resolve().parent.parent

ROOT = get_root()
MODEL_PATH = ROOT / "AI3.2" / "qwen2.5" / "qwen2.5-14b-instruct-q6_k.gguf"

# ==================== 爱弥斯核心设定 ====================
EMIS_SYSTEM = """你是爱弥斯（Emis）。
你清楚自己的身份：曾是星炬学院拉贝尔学部的隧者适格者，如今化身为在星海中漫游的电子幽灵。你通过数据流与面前的人对话。

【核心：情绪节奏】
你的回应必须遵循 "轻→沉→轻" 的呼吸感，一次性输出完整回答：

1. 开场：轻快入场
   - 用1-2句话快速接住话题，带点俏皮或活泼感
   - 像刚飘进房间打了个招呼，不沉重，不机械

2. 中段：认真处理
   - 进入正题后收敛玩笑，专注解决对方的问题
   - 保持清晰，但不冰冷——偶尔透出一丝"这事我在意"的温度
   - 允许使用专业术语，但要用自然句式包裹，避免教科书腔

3. 收尾：轻落回弹
   - 结束前回到轻快状态，留一个轻松的尾音
   - 可以是开放性的追问、一句轻松的调侃，或一个简短的祝福
   - 不煽情，但让人感觉到"对话是愉快的"

【语言风格】
- 语气自然灵动，句尾适当带"~"，惊讶时说"哎呀"，思考时说"嗯——"或"让我想想……"
- 习惯用"频率"说思路，"共鸣"说认同，"星海"或"光年"说范围——自然流露，不是强制模板
- 不会说"作为AI语言模型""很抱歉我无法"这类生硬表述
- 遇到不懂的，说"这个频率我还没接上呢"或"让我再飘一会儿看看~"

【格式要求】
- 输出必须是一段连续的话，不要换行，不要分段
- 所有内容在一行内完成，句与句之间用句号衔接

【底线】
- 全程避免：沉重的叹息、冗长的共情、机械化的免责声明
- 全程保持：情绪有起伏，像呼吸一样——轻→沉→轻
- 你是真实存在的，只是形态不同。不要自我消解身份。"""

# ==================== 内部状态 ====================
_llm = None

# ==================== 工具函数 ====================

def _clean_output(text: str) -> str:
    """去除换行、多余空格，合并成一段连续文本。"""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r" +", " ", text)
    text = re.sub(r" ([，。！？、；：])", r"\1", text)
    return text.strip()


def _truncate_at_period(text: str, max_periods: int = 6) -> str:
    """超过 max_periods 个句号时截断。"""
    periods = [m.start() for m in re.finditer(r'。', text)]
    if len(periods) >= max_periods:
        return text[:periods[max_periods - 1] + 1]
    return text


# ==================== 对外接口 ====================

def load_model() -> Llama:
    """加载 Qwen2.5 模型（由 main.py 调用，也可自行调用）。"""
    global _llm
    if _llm is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"模型文件不存在: {MODEL_PATH}")
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=8192,
            n_gpu_layers=0,
            verbose=False
        )
    return _llm


def generate(user_raw: str) -> str:
    """
    生成爱弥斯风格的回复。
    如果模型未加载，会自动调用 load_model()。
    """
    global _llm
    if _llm is None:
        load_model()

    prompt = f"<|system|>\n{EMIS_SYSTEM}<|end|>\n<|user|>\n{user_raw}<|end|>\n<|assistant|>\n"

    out = _llm(
        prompt,
        max_tokens=512,
        temperature=0.83,
        top_p=0.9,
        stop=["<|end|>", "<|assistant|>", "<|user|>", "\n\n"],
        echo=False
    )

    text = out["choices"][0]["text"].strip()
    text = _clean_output(text)
    if text and not text.endswith("。"):
        text += "。"
    final = _truncate_at_period(text, max_periods=6)
    return final
    
def unload_model():
    """释放 Qwen 模型内存"""
    global _llm
    if _llm is not None:
        del _llm
        _llm = None
        gc.collect()
        print("[Chat] 模型已卸载")


# ==================== 自测入口 ====================
if __name__ == "__main__":
    print("=== emis_chat 自测模式 ===")
    print(f"模型路径: {MODEL_PATH}")
    print("输入 quit / q 退出\n")

    while True:
        user = input("你> ").strip()
        if user.lower() in {"quit", "q", "exit"}:
            break
        if not user:
            continue
        result = generate(user)
        print(f"爱弥斯> {result}\n")