#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import emis_chat
import sovits_tts
import sys

# ==================== 配置 ====================
AUTO_VOICE = True  # 是否每句回复自动合成语音

# ==================== 主程序 ====================

def main():
    print("=" * 50)
    print("爱弥斯 (Emis) 启动中...")
    print("=" * 50)
    print()

    # 1. 启动 SoVITS API（后台加载 AMS 模型）
    print("[1/3] 正在启动 GPT-SoVITS API...")
    ok = sovits_tts.start_api()
    if not ok:
        print("[警告] SoVITS API 启动失败，语音功能将不可用")
        print("        但文本对话仍可继续。\n")
    else:
        print()

    # 2. 加载 Qwen2.5
    print("[2/3] 正在加载 Qwen2.5 模型...")
    try:
        emis_chat.load_model()
        print("[2/3] 模型加载完成！\n")
    except Exception as e:
        print(f"[2/3] 模型加载失败: {e}")
        sys.exit(1)

    # 3. 进入对话
    print("[3/3] 爱弥斯已就绪！")
    print("-" * 50)
    print("命令：")
    print("  直接输入文字  →  与爱弥斯对话")
    print("  /voice on     →  开启自动语音")
    print("  /voice off    →  关闭自动语音")
    print("  /tts <文字>   →  只合成语音，不走 AI")
    print("  quit / q      →  退出")
    print("-" * 50 + "\n")

    global AUTO_VOICE

    try:
        while True:
            try:
                user_input = input("你> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in {"quit", "q", "exit", "退出"}:
                break

            # 命令处理
            if user_input.startswith("/tts "):
                text = user_input[5:].strip()
                if text:
                    sovits_tts.tts(text)
                continue

            if user_input == "/voice on":
                AUTO_VOICE = True
                print("[设置] 自动语音已开启\n")
                continue
            if user_input == "/voice off":
                AUTO_VOICE = False
                print("[设置] 自动语音已关闭\n")
                continue

            # AI 对话
            result = emis_chat.generate(user_input)
            print(f"爱弥斯> {result}\n")

            # 自动语音
            if AUTO_VOICE:
                sovits_tts.tts(result)

    finally:
        print("\n正在关闭服务...")
        sovits_tts.stop_api()
        print("再见~")


if __name__ == "__main__":
    main()