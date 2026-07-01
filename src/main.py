"""
程序入口：终端对话循环。

运行方式：python -m src.main
"""
from langchain_core.messages import HumanMessage

from src.graph import graph


def main():
    print("=" * 56)
    print("   求职 Copilot —— 你的 AI 求职教练")
    print("   输入 quit/exit 退出；输入内容后回车发送")
    print("=" * 56)

    # thread_id 用来标识"一次会话"。
    # 同一个 thread_id 的多轮对话会共享记忆（靠 checkpointer）。
    config = {"configurable": {"thread_id": "user-1"}}

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见，祝你早日拿到心仪的 offer！💪")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("加油，祝你早日拿到心仪的 offer！💪")
            break
        if not user_input:
            continue

        # 调用图：把用户消息送进去，拿回 AI 回复
        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )
        reply = result["messages"][-1].content
        print(f"\n教练: {reply}")


if __name__ == "__main__":
    main()
