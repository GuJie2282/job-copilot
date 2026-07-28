# Tasks

## home-onboarding（首页链路条）

- [x] 1. Home.vue 新增 `loadResumes()` + `loadSessions()`（静默失败，onMounted 调用）
- [x] 2. `stages` computed 改**链式 done 判定**（严格：匹配有分 / 简历 finalized / 面试 finished）
- [x] 3. 全 done **祝贺态**（隐藏 next-card + 祝贺卡 + thesis 完成论点 + CTA「再去匹配」）
- [x] 4. done 段连线**流光动效**（渐变 background-position 动画）+ active pulse 保留
- [x] 5. 链路条**放大**（圆点 18→24、节点名 sm→base、连线 2→3、padding 加大）
- [x] 6. `prefers-reduced-motion` 禁用流光 + pulse
- [x] 7. 截图验证各推进态：无画像 / 有画像 / 有匹配 / 有简历 / 全 done 祝贺

## page-cta-visibility（全站 CTA 可见性）

- [x] 8. **InterviewSetup** sticky 底部 CTA bar + 配置摘要
- [x] 9. **JdMatcher** 结果区「据此生成简历」上移 / 双 CTA
- [x] 10. **ResumeOptimizer** 结果区「进入精修」上移
- [x] 11. **Profile** 编辑/保存 sticky 或顶部
- [x] 12. 评估抽 `StickyActionBar` 共用组件（等 2-3 页落地模式稳定后）— 评估：暂不抽，各页独立实现（design B4），待模式稳定
- [x] 13. 截图验证各页主 CTA 在折叠线内可见（不滚动即可操作）— InterviewSetup/Profile sticky 验证粘视口底(bottom=900)；JdMatcher/ResumeOptimizer 结果CTA代码已加(e2e无结果未截)
