"""
节奏决策单测（evolve-interview-pacing）
=======================================

纯逻辑测试 _decide / _apply_guardrails / _rule_decide_fallback，**不调 LLM**。
覆盖：LLM action 采纳、规则 fallback、四类防崩盘护栏纠正。

节奏决策逻辑：
  - _decide 优先采用评估 LLM 的 action，经 _apply_guardrails 护栏校验；
  - action 缺失/非法 → _rule_decide_fallback（原计数器规则，降级与回滚通道）。

护栏（防崩盘，非业务限制）：
  - 最低总轮数 _PACE_MIN_ROUNDS=2：过早 end（且有下一题）→ 强制 next
  - 单题追问 _PACE_PROBE_LIMIT=5：达上限仍选 probe → 换题/收尾
  - 反问至多 _PACE_QA_MAX=1：已反问却选 enter_qa → 换题/结束
  - 最高总轮数 = total_q*(1+5)：达上限 → 强制 end

跑法：
  cd backend && ./.venv/Scripts/python.exe -m pytest test_pacing.py -v
  （或 python test_pacing.py 脚本式逐条打印）

作者：求职 Copilot 项目
日期：2026-07-23
"""

from src.graph.nodes import mock_interview as mi


# ── 测试夹具：构造最小 state / eval_result（不依赖 LLM）──

def _state(idx=0, probe_count=0, qa_done=False, transcript_len=0,
           total_q=5, has_qa=True, probing_limit=3):
    """构造 _decide 所需的最小 state。question_count 用 plan 值（与实现一致）。"""
    return {
        "current_q_idx": idx,
        "current_q_probes": probe_count,
        "qa_done": qa_done,
        "transcript": [{}] * transcript_len,
        "question_plan": {
            "question_count": total_q,
            "has_qa_session": has_qa,
            "probing_limit": probing_limit,
        },
        "question_bank": [{"qid": f"q{i}"} for i in range(total_q)],
    }


def _eval(action=None, miss_signals=None, miss_probe_map=None):
    return {
        "action": action,
        "miss_signals": miss_signals or [],
        "miss_probe_map": miss_probe_map or {},
    }


# ── 6.1 LLM action 采纳路径（护栏不拦时直接采用）──

def test_adopt_probe_action():
    assert mi._decide(_state(probe_count=0), _eval(action="probe")) == "probe"


def test_adopt_next_action():
    assert mi._decide(_state(idx=0, total_q=5), _eval(action="next")) == "next"


def test_adopt_enter_qa_action():
    assert mi._decide(_state(qa_done=False, has_qa=True), _eval(action="enter_qa")) == "enter_qa"


def test_adopt_end_action_when_allowed():
    # 已过最低轮数（completed_rounds=2，+1=3 ≥ MIN_ROUNDS=2）→ end 通过
    assert mi._decide(_state(transcript_len=2), _eval(action="end")) == "end"


# ── 6.1 规则 fallback 路径（action 缺失/非法 → _rule_decide_fallback）──

def test_fallback_when_action_missing():
    ev = _eval(action=None, miss_signals=["量化"], miss_probe_map={"量化": "具体数据"})
    assert mi._decide(_state(probe_count=0), ev) == "probe"


def test_fallback_when_action_illegal():
    ev = _eval(action="bogus", miss_signals=["量化"], miss_probe_map={"量化": "具体数据"})
    assert mi._decide(_state(probe_count=0), ev) == "probe"


def test_fallback_next_when_no_miss():
    # action=None 且无缺失信号 → 规则走 next
    assert mi._decide(_state(idx=0, total_q=5), _eval(action=None)) == "next"


# ── 6.2 护栏：最低轮数（过早 end 且还有题 → 强制 next）──

def test_guardrail_min_rounds_blocks_early_end():
    # completed_rounds=0，+1=1 < MIN_ROUNDS(2)，has_next=True → end 纠正为 next
    assert mi._decide(_state(transcript_len=0, idx=0, total_q=5), _eval(action="end")) == "next"


def test_guardrail_min_rounds_allows_end_when_no_next():
    # 过早 end 但已无下一题 → end 通过（题问完了，结束合理，不强行追问）
    assert mi._decide(_state(transcript_len=0, idx=4, total_q=5), _eval(action="end")) == "end"


# ── 6.2 护栏：单题追问上限（达上限仍 probe → 换题/收尾）──

def test_guardrail_probe_limit_to_next():
    # probe_count=5 ≥ _PACE_PROBE_LIMIT(5)，has_next → next
    assert mi._decide(_state(probe_count=5, idx=0, total_q=5), _eval(action="probe")) == "next"


def test_guardrail_probe_limit_no_next_to_qa():
    # probe 达上限且无下一题但有反问 → enter_qa
    assert mi._decide(_state(probe_count=5, idx=4, total_q=5, has_qa=True), _eval(action="probe")) == "enter_qa"


# ── 6.2 护栏：反问重复（已反问却 enter_qa → 换题/结束）──

def test_guardrail_qa_repeat_to_next():
    assert mi._decide(_state(qa_done=True, idx=0, total_q=5), _eval(action="enter_qa")) == "next"


def test_guardrail_qa_repeat_no_next_to_end():
    assert mi._decide(_state(qa_done=True, idx=4, total_q=5), _eval(action="enter_qa")) == "end"


# ── 6.2 护栏：next 无下一题 → 反问/结束 ──

def test_guardrail_next_no_more_to_qa():
    assert mi._decide(_state(idx=4, total_q=5, has_qa=True), _eval(action="next")) == "enter_qa"


def test_guardrail_next_no_more_to_end():
    assert mi._decide(_state(idx=4, total_q=5, has_qa=False), _eval(action="next")) == "end"


# ── 6.2 护栏：最高总轮数 → 强制结束（防永不收尾）──

def test_guardrail_max_rounds_force_end():
    # total_q=5 → max_rounds=5*(1+5)=30；completed_rounds=29，+1=30 ≥ 30 → end
    assert mi._decide(_state(transcript_len=29, total_q=5), _eval(action="probe")) == "end"


# ── _rule_decide_fallback 直测（降级/回滚通道）──

def test_rule_fallback_probe():
    ev = _eval(miss_signals=["量化"], miss_probe_map={"量化": "数据"})
    assert mi._rule_decide_fallback(_state(probe_count=0), ev) == "probe"


def test_rule_fallback_next():
    assert mi._rule_decide_fallback(_state(idx=0, total_q=5), _eval()) == "next"


def test_rule_fallback_qa():
    assert mi._rule_decide_fallback(_state(idx=4, total_q=5, has_qa=True), _eval()) == "enter_qa"


def test_rule_fallback_end():
    assert mi._rule_decide_fallback(_state(idx=4, total_q=5, has_qa=False), _eval()) == "end"


if __name__ == "__main__":
    # 脚本式逐条跑（不依赖 pytest，方便手动验证）
    import sys
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for f in funcs:
        try:
            f()
            print(f"[✓ PASS] {f.__name__}")
            passed += 1
        except AssertionError:
            print(f"[✗ FAIL] {f.__name__}")
    print(f"\n{passed}/{len(funcs)} passed")
    sys.exit(0 if passed == len(funcs) else 1)
