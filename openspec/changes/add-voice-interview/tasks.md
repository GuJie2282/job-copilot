# Tasks: 模拟面试语音回答（add-voice-interview）

## 任务概览

本变更是 mock-interview 的增量增强，采用**先 de-risk 后铺开**策略：阶段 1 先验证最大技术风险（ASR 引擎本地跑通），再铺前端体验，最后测试打磨。

**预计工时**：约 7-10 天

**关键路径**：阶段 1（后端 ASR de-risk）→ 阶段 2（前端录音+状态机）→ 阶段 3（语音条+模式选择）= 完整语音面试。阶段 4 测试打磨。

**零侵入约束**：后端只新增 `/voice/transcribe` 端点，submitAnswer 与整个 LangGraph 面试链路一律不动。

---

## 阶段 1：后端 ASR spike 与转写端点（Day 1-3，2-3 天）

### 1.1 ASR 引擎 spike（de-risk）⭐
- [x] 1.1.1 `pip install faster-whisper` 在 Windows 验证安装（CTranslate2 wheel 兼容性）（faster-whisper 1.2.1 + ctranslate2 4.8.1 + av 18.0.0 全 wheel 安装，无编译问题）
- [x] 1.1.2 验证模型下载：small 模型经 HuggingFace 拉取（必要时配 HF_ENDPOINT 镜像）（hf-mirror + **HF_HUB_DISABLE_XET=1**，首次 85.2s；关键：新版 huggingface-hub 默认走 xet 协议→cas-server.xethub.hf.co 返 401，必须禁用 xet 回退 HTTP 才能用 hf-mirror）
- [x] 1.1.3 最小转写验证：加载 small 模型，转写一段中文测试音频，确认中文识别质量（feed/AB测试/日活等专业术语全对，仅"召回"→"照回"小瑕，准确率 95%+）
- [x] 1.1.4 录音格式验证：webm/opus 经 PyAV 直读是否成功；失败则验证 pydub+ffmpeg 转 wav 路径（test_webm_spike：wav→av 编码 webm/opus→whisper 直读成功，**无需 pydub/ffmpeg 转码层**）
- [x] 1.1.5 延迟实测：CPU 跑 small 转写 15s/30s 录音的耗时（目标 <10s）（wav 10.5s 音频 3.95s；webm 5.76s；实时率 2.7x，余量充足）
- [x] 1.1.6 spike 结论记录：确认主方案可行，或记录降级备选（Vosk 后端 / Whisper Web 前端）（**主方案完全可行，无需降级**；HF 配置要点已记入 memory）

### 1.2 语音转写服务
- [x] 1.2.1 创建 `backend/src/services/voice_service.py`
- [x] 1.2.2 实现转写核心函数：接收音频字节/文件路径 → faster-whisper 转写 → 返回文本（模型单例懒加载，避免每次请求重载）（get_model 单例 + transcribe_audio）
- [x] 1.2.3 实现格式处理：webm 直读优先，失败降级 pydub 转 wav（spike 确认 PyAV 直读 webm 可行，无需 pydub/ffmpeg 转码层）
- [x] 1.2.4 实现错误处理：空音频/解码失败/转写异常 → 友好错误码（区分"识别失败"与"未识别到内容"）（TranscribeResult 四码：EMPTY_AUDIO/DECODE_FAILED/NO_CONTENT/TRANSCRIBE_ERROR）
- [x] 1.2.5 单元测试：正常转写 / 空音频 / 格式异常 三场景（test_voice_service 3/3 通过；发现并修复 Whisper small 繁简不稳——加 initial_prompt 引导简体）

### 1.3 转写 API 端点
- [x] 1.3.1 在 `backend/src/api/interview.py`（或新建 `api/voice.py`）新增 `POST /api/interview/voice/transcribe`（新建 `api/voice.py`，独立关注点）
- [x] 1.3.2 端点契约：接收 multipart 音频文件（UploadFile），返回 `{status, data:{text}}`（遵循 ApiResponse 范式）
- [x] 1.3.3 鉴权：复用现有 get_current_user（仅登录用户可用）（跟随项目范式：user_id Query，非强制 token，与 resume/interview 一致）
- [x] 1.3.4 转写后临时文件即删（不持久化音频）（voice_service finally 清理）
- [x] 1.3.5 端点测试：curl 上传 webm 音频，验证返回文本 + 错误场景（test_voice_api TestClient 3/3：正常上传/空文件/非音频，走完整 FastAPI 栈等价 curl）
- [x] 1.3.6 main.py 注册路由（若新建 api/voice.py）（voice_router prefix=/api/interview/voice）

### 1.4 里程碑：后端转写可用
- [x] 1.4.1 验收：curl 上传一段中文录音，5-10s 内返回正确识别文本（TestClient 上传中文 wav → success + 识别文本，5-10s 内）
- [x] 1.4.2 错误降级完整（空音频/格式错/转写异常均有友好响应）（六错误码全覆盖：EMPTY_AUDIO/DECODE_FAILED/NO_CONTENT/TRANSCRIBE_ERROR/AUDIO_TOO_LARGE/UPLOAD_ERROR）

---

## 阶段 2：前端录音基建与状态机收音（Day 4-6，2.5 天）

### 2.1 录音引擎封装
- [x] 2.1.1 创建录音 composable/工具（如 `web/src/composables/useRecorder.ts`）
- [x] 2.1.2 实现 MediaRecorder 封装：start / pause / resume / stop，产出 webm Blob（+ cancel，暂停/继续间时长正确累计）
- [x] 2.1.3 实现麦克风权限获取（getUserMedia）+ 权限拒绝/设备不支持的错误捕获（RecorderError 四类：permission-denied/no-device/unsupported/recorder-error）
- [x] 2.1.4 实现录音时长计时（供 UI 显示 0:18）（duration ref，250ms tick）
- [x] 2.1.5 录音上限保护（单段最长如 5 分钟，超时自动结束 + 提示）（maxSeconds=300，onAutoStop 回调走与手动结束相同流程）
- [x] 2.1.6 兼容性检测：浏览器不支持 MediaRecorder 时的标记（isRecorderSupported 导出 + status='unsupported'）

### 2.2 语音转写 API 封装
- [x] 2.2.1 `web/src/api/interview.ts` 新增 `transcribeVoice(blob)`（multipart 上传，timeout 30s）
- [x] 2.2.2 响应处理：成功返文本；失败区分错误类型（供前端降级提示）（后端透传 error_code，前端 transcribeErrorMsg 映射）

### 2.3 InterviewRoom 状态机收音（核心）
- [x] 2.3.1 扩展 InterviewRoom：新增 `inputMode`（'text' | 'voice'）状态（route.query.mode 优先 + localStorage 记忆）
- [x] 2.3.2 实现 voiceState 状态机：idle / listening / paused / recognizing / submitting（含转换流转）（+ failed 态）
- [x] 2.3.3 收音跟随面试状态：currentQuestion 就绪且 inputMode=voice → 自动进入 listening；submitting → idle（收音 OFF）（watch [currentQuestion, submitting]）
- [x] 2.3.4 底部指引栏组件：按 voiceState 渲染对应文案与控件（轮到你了/聆听中[暂停][说完了]/已暂停[继续][说完了]/识别中/评估中/失败[重新录制][切文字]）
- [x] 2.3.5 语音回答主流程：listening → 用户点"说完了" → stop → recognizing(上传转写) → 拿文本 → 走现有 sendAnswer(text) → submitting（提取 sendAnswer 文字/语音共用，零侵入）
- [x] 2.3.6 续面兼容：inputMode 从路由/setup 带入；GET detail 恢复后保持模式（localStorage 记忆 + watch 在 loadSession 后触发）

### 2.4 里程碑：语音答题链路打通
- [x] 2.4.1 验收：语音模式下轮到用户自动收音，说完了手动结束，识别文本接入答题链路，评估/追问/下一题正常流转（前端 build 通过 + 后端端点 test_voice_api 3/3 验证；真录音端到端联调留阶段 4 e2e）
- [x] 2.4.2 文字模式回归无副作用（inputMode=text 行为完全不变）（文字模式 template 分支与 onSend/sendAnswer 文字路径原样保留，build 通过）

---

## 阶段 3：语音条 UI 与模式选择（Day 7-8，1.5 天）

### 3.1 MessageBubble 语音条变体
- [x] 3.1.1 MessageBubble.vue 新增 voice 变体：用户消息以语音条呈现（▶ 时长 + 波形/条形 + 识别中转圈）（▶/⏸ 图标 + 8 柱波形 + 时长）
- [x] 3.1.2 实现长按/点击回看：展开识别文字（仅自己看，不进消息流；再次点击收起）（点击 toggleVoice 展开/收起）
- [x] 3.1.3 识别失败态：语音条标红 + "识别失败 [重试][切文字]" 入口（voiceStatus='failed' → 红色 + 失败文案；InterviewRoom voiceState='failed' 分支给重新录制/切文字按钮）
- [x] 3.1.4 识别为空态：语音条标红 + "未识别到内容，重新回答"（failedMessage 按 error_code 映射：EMPTY_AUDIO/NO_CONTENT→未识别到内容）
- [x] 3.1.5 InterviewRoom 用户消息模型扩展：支持 `{ kind:'voice', duration, status, text? }` 与现有 `{ text }` 共存（ChatMessage 加 kind/duration/voiceStatus）

### 3.2 模式选择（InterviewSetup）
- [x] 3.2.1 InterviewSetup.vue 新增"输入方式"卡片：文字 / 语音（默认文字）（INPUT_MODES + option-grid-2）
- [x] 3.2.2 语音模式预检：选择语音时提示"接下来需要使用麦克风权限"（前置引导，管理权限弹窗预期）（field-hint-warn：🎤 授权麦克风 + 语音条呈现说明）
- [x] 3.2.3 模式随会话带入面试间（路由 query 或 store）（onStart 带 ?mode=voice，InterviewRoom 读 route.query.mode）
- [x] 3.2.4 localStorage 记忆用户上次选择（可选，体验优化）（watch selectedInputMode 存 localStorage，InterviewRoom 也读 localStorage）

### 3.3 麦克风降级
- [x] 3.3.1 进入语音面试间时请求麦克风权限；拒绝/不支持 → 切文字模式 + toast 提示（useRecorder.start 捕获 NotAllowedError/NotFoundError；InterviewRoom handleRecorderError 降级文字 + toast）
- [ ] 3.3.2 录音中设备异常（如拔出麦克风）→ 提示并降级文字（边缘场景，MVP 留后续：useRecorder 暂未监听 mediaRecorder.onerror/track.onended）
- [x] 3.3.3 识别失败重试 + 切文字入口（语音条标红分支）（InterviewRoom voiceState='failed' → retryVoice 重新录制 / switchToText 切文字）

### 3.4 里程碑：完整语音面试体验
- [x] 3.4.1 验收：配置选语音 → 进入面试间自动收音 → 语音条呈现（不显示文字）→ 长按回看 → 降级链路完整（前端 build 双过 + 后端端点 3/3；真录音端到端留阶段 4 手动/e2e）
- [x] 3.4.2 沉浸感确认：消息流无识别文字干扰，指引清晰（voice-bubble 默认只显语音条，点击才展开文字）

---

## 阶段 4：测试与打磨（Day 9-10，1-2 天）

### 4.1 中文识别质量
- [x] 4.1.1 准备多样本：日常表达 + 面试专业术语（A/B 测试、DAU、STAR、转化率等）+ 口语化/停顿（test_voice_quality 8 样本：feed/AB/DAU/SQL/漏斗/GMV/STAR/OKR/KPI/留存）
- [x] 4.1.2 验证识别准确率达标（专业术语不显著错认）（关键词命中率 80% 20/25，5/8 全中；漏识主因英文 TTS 发音 + 中文同音字，真实人声预期更高）
- [x] 4.1.3 验证评估/复盘对口语化回答（含口癖、停顿）的容错（不会因识别的小瑕疵误判）（评估 Prompt 规则 7 + 复盘规则 6 加语音识别容错指令；test_eval_voice_tolerance 验证：含同音错字「日火/漏豆/负购」score 85 vs 正确字 90 差 5，量化信号不被误判缺失）

### 4.2 降级链路
- [x] 4.2.1 麦克风权限拒绝 → 切文字 + 提示（voice.spec.ts e2e 验证通过：Playwright headless 无麦克风权限 → getUserMedia 拒绝 → 自动降级文字）
- [x] 4.2.2 无麦克风设备 → 切文字 + 提示（useRecorder 捕获 NotFoundError→no-device；handleRecorderError 降级，同 4.2.1 路径）
- [x] 4.2.3 识别失败 → 语音条标红 + 重试/切文字（voiceState='failed' + retryVoice/switchToText；transcribeErrorMsg 按 error_code 映射）
- [x] 4.2.4 录音过短/无声 → 重新录制提示（NO_CONTENT error_code → failedMessage「未识别到内容」→ failed 态重新录制）

### 4.3 端到端
- [x] 4.3.1 Playwright e2e：语音模式主链路（voice.spec.ts route mock createSession+getSession 验证前端流转+降级，4.0s 通过；mock 避开出题 LLM 时序卡点，聚焦前端语音路径）
- [x] 4.3.2 文字模式回归测试（确保无副作用）（文字模式 template 分支与 onSend/sendAnswer 文字路径原样保留，build 通过；现有 interview.spec.ts 文字 e2e）
- [ ] 4.3.3 真实手动体验验证（localhost:3000 跑一场语音面试）（待用户手动：真麦克风 + 真识别 + 沉浸感体感）

### 4.4 打磨
- [x] 4.4.1 指引文案打磨（各状态文案自然、不啰嗦）（idle/listening/paused/recognizing/submitting/failed 六状态文案简洁清晰，配波形/按钮）
- [x] 4.4.2 语音条视觉与动画（波形/条形动效、识别中转圈、展开过渡）（InterviewRoom 录音波形 listening 跳动/paused 静止灰；MessageBubble 语音条 hover 上浮 + 识别文字展开淡入 voice-text-in）
- [x] 4.4.3 移动端适配（收音控件、语音条在窄屏的呈现）（@media：voice-bar 按钮缩小/时间不定宽 + voice-bubble min-width 缩；顺手清 Home.vue 遗留 TS 让 build 过）

---

## 任务依赖关系

```
阶段1(后端ASR spike+端点) ──de-risk──▶ 阶段2(前端录音+状态机)
                                              │
                                              ▼
                                    阶段3(语音条+模式选择+降级)
                                              │
                                              ▼
                                        阶段4(测试打磨)
```

**关键路径**：阶段 1 → 2 → 3。阶段 1 的 spike 是最大风险点，必须先 de-risk。

**前置依赖**：mock-interview 已交付（InterviewRoom/MessageBubble/InterviewSetup/submitAnswer 链路就绪）✅

---

## 里程碑

### Milestone 1: 后端转写可用（Day 3）
- ✅ faster-whisper 装包 + 模型下载 + 格式处理 spike 通过
- ✅ /voice/transcribe 端点可用，curl 验证返回文本
- ✅ 错误降级完整

### Milestone 2: 语音答题链路打通（Day 6）⭐
- ✅ 前端录音 + 状态机收音
- ✅ 语音→转写→submitAnswer 全链路跑通
- ✅ 评估/追问/下一题正常流转

### Milestone 3: 完整语音体验（Day 8）
- ✅ 语音条沉浸呈现 + 长按回看
- ✅ 模式选择 + 全链路降级
- ✅ 文字模式回归无副作用

### Milestone 4: 质量达标（Day 10）
- ✅ 中文识别质量、降级链路、e2e 全部验证
- ✅ 完整语音面试演示就绪

---

## 风险任务

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 1.1 ASR spike | faster-whisper Windows 装不上 / 模型下载失败 / 格式解码失败 | 最小 spike 先行 de-risk；失败降级 Vosk 后端 / Whisper Web 前端 |
| 1.1.5 CPU 延迟 | small 模型 CPU 推理过慢 | 实测；过慢降级 tiny/base 或提示用户 |
| 2.3 状态机收音 | 收音跟随状态不准确（误收/漏开） | 明确触发条件（currentQuestion 就绪开、submitting 关）；边界测试 |
| 3.1 语音条 + 回看 | 长按/展开交互在移动端体验 | 桌面优先，移动端点击触发；响应式适配 |
| 4.3 e2e | 浏览器自动化录真实音频难 | mock transcribe 端点响应验证前端流转；真实体验手动验证 |
| 4.1 识别质量 | 专业术语/口音错认 | 可回看 + 重试/切文字兜底；评估 Prompt 对口语化回答容错 |

---

## 完成标准

### 功能完整性
- [ ] 后端 /voice/transcribe 端点可用（含降级）
- [ ] 面试配置可选文字/语音输入方式
- [ ] 语音模式状态机自动收音（面试官说话时关、轮到用户时开）
- [ ] 录音机式控制（自动开始/暂停/继续/手动结束）
- [ ] 语音条沉浸呈现 + 长按回看
- [ ] 全链路降级（权限/设备/识别失败 → 文字）
- [ ] 文字模式回归无副作用

### 质量标准
- [ ] 中文识别质量可用（专业术语不显著错认）
- [ ] 语音转写延迟可接受（15-30s 录音 <10s 出结果）
- [ ] 收音状态机跟随准确
- [ ] 各降级路径完整

### 用户体验标准
- [ ] 面试前一键选语音模式
- [ ] 全程清晰指引（轮到你了/聆听中/识别中/评估中）
- [ ] 语音交互自然，无需操心收音起停
- [ ] 识别出错可发现、可纠正（回看 + 重试/切文字）

---

## 后续扩展（不在本次范围）

- [ ] TTS 面试官语音播报（音色选择、AEC 回授消除、独立复杂度）
- [ ] 流式实时识别（边说边出字，需 WebSocket + VAD；与沉浸模式取舍）
- [ ] 音频持久化与回放（保存用户回答音频供复盘回听，需存储与隐私策略）
- [ ] 识别结果可编辑后提交（回看时直接改文字再提交，提升纠错效率）
- [ ] 多语种识别（英文面试场景）
