# Auto Choose Course — 人大教务系统自动选课

## 项目目标
自动选课脚本，用于人大暑期学校（jw.ruc.edu.cn）的课程选择和退课操作。

## 当前状态
- **用户**: 乔致锟 | 学号: 2025201946 | 专业: 统计学类
- **学期**: 2026 Summer School (2025-2026-1)
- **学期ID**: `8a7459079a5245ef019a56c975a50000`
- **当前日期**: 2026-06-04
- **选课第2轮**: 2026-06-03 00:00 → 2026-06-05 00:00 ✅ 进行中
- **已选课程**: FD2624 数的世界之旅 + FD2642 统计机器学习（上限2门）
- **可选课程**: 91 门（仅 FD2643 有剩余名额 13 个）
- **已有文件**: config.json, auto_course.py

## 系统信息
- **系统**: 人大国际小学期 (RUC ISS)
- **开发商**: 湖南强智科技
- **网关**: `https://jw.ruc.edu.cn` → `gateway-service:8001`
- **前端**: Vue.js SPA (Element UI)

---

## API 架构（已验证）

### 鉴权
- `Authorization: Bearer <JWT>` + Cookie
- JWT 有效期约 4 小时，过期需重新登录

### 两套 Content-Type

| 接口类型 | Content-Type | Body 格式 |
|----------|-------------|-----------|
| 查询类 (列表、信息) | `application/json` | `{"page": {...}}` 或 `{}` |
| 操作类 (选课、退课、检查) | **`text/plain`** | 纯 `"<crs_id>"` 字符串 |

### 已确认可用的 API (已验证 200 OK)

| 端点 | 用途 | Content-Type |
|------|------|-------------|
| `/qsmart/common/sessionUserInfo` (GET) | 用户信息 | - |
| `/minJwxt/mgmt/public/service/querySemesterListBySelect` (POST) | 学期列表 | JSON |
| `/minJwxt/mgmt/student/course/getStuInfo` (POST) | 学生信息 | JSON |
| `/minJwxt/mgmt/student/course/checkSelectCourseTime` (POST) | 检查选课时间 | JSON |
| `/minJwxt/mgmt/student/course/queryCourseOfferListByPage` (POST) | 可选课程列表 | JSON |
| `/minJwxt/mgmt/student/course/queryStuCourseOfferListByPage` (POST) | 已选课程列表 | JSON |
| `/minJwxt/mgmt/student/course/selectCourse` (POST) | **选课** | **text/plain** |
| `/minJwxt/mgmt/student/course/cancelSelectCourse` (POST) | **退课** | **text/plain** |
| `/minJwxt/mgmt/student/course/checkCourseSurplusCapacity` (POST) | 检查剩余名额 | **text/plain** |
| `/minJwxt/mgmt/student/course/checkCourseSettleTime` (POST) | 检查选课时间窗口 | **text/plain** |
| `/minJwxt/mgmt/student/course/selectCourseCheckForConflicts` (POST) | 冲突检查 | **text/plain** |
| `/minJwxt/mgmt/student/course/checkCourseSelected` (POST) | 检查是否已选 | **text/plain** |
| `/minJwxt/mgmt/student/course/checkContactInfo` (POST) | 联系信息检查 | JSON |
| `/minJwxt/mgmt/student/course/checkStuLabel` (POST) | 学生标签检查 | JSON |

### 退课接口（两个）

| 接口 | 用法 | 状态 |
|------|------|------|
| `cancelSelectCourse` | `text/plain` 传 `crs_id` | ❌ 403 Forbidden（可能需特殊权限或路径有误） |
| `deleteStuCourseInfo` | JSON 传 `crs_stu_id` + `crs_id` 等 | ❌ 400 "Cannot be cancelled!" |

### 请求格式示例

**查询可选课程列表**:
```json
{"page": {"pageIndex": 1, "pageSize": 100}}
```

**选课** (text/plain):
```
8a74591a9b13548c019b2101c646007a
```

**退课** (text/plain):
```
8a7459079a5245ef019ae247a50a0069
```

---

## 选课时间窗口

学期对象 `8a7459079a5245ef019a56c975a50000` 的关键时间戳（北京时间）:

| 轮次 | 开始 | 结束 | 状态 |
|------|------|------|------|
| 第1轮 (internalCourseStartTime) | 2026-05-28 00:00 | 2026-06-03 00:00 | ❌ 已结束 |
| 第2轮 (internalCourseStartTime2) | 2026-06-03 00:00 | 2026-06-05 00:00 | ✅ 进行中 |
| 第3轮 (internalCourseStartTime3) | 2026-07-06 00:00 | 2026-07-24 00:00 | ⏳ 未开始 |
| 校外选课 (externalCourseStartTime) | 2026-03-01 00:00 | 2026-05-27 00:00 | ❌ 已结束 |

字段名: `internalCourseStartTime` / `internalCourseEndTime`，后缀 `2`、`3` 表示第2、3轮。

---

## 已解决问题

### Content-Type 错误（2026-06-04 修复）
选课/退课/检查类接口要求 `Content-Type: text/plain`，body 为纯 `crs_id` 字符串。之前错误地使用 `application/json` 传 JSON 对象，导致 400 错误。

### 选课限制
- 最多选 2 门课程
- 退课接口 `cancelSelectCourse` 返回 403，可能是端点路径或鉴权问题
- FD2643 有容量但与其他已选课程时间冲突

---

## 待解决

1. `cancelSelectCourse` 为何返回 403 — 路径可能不是 `/minJwxt/mgmt/student/course/cancelSelectCourse`
2. 退课的正确端点 — 需抓浏览器实际退课时的网络请求确认
3. 时间冲突检测 — FD2643 与已有课冲突，需先退一门再选
4. 添加 `.gitignore` 排除 config.json，改用环境变量传凭据

---

## 重要警示
⚠️ `config.json` 包含真实凭据 (JWT + Cookie)，**不要提交到 git**。

### 凭据状态
- JWT: ✅ 有效（2026-06-04 测试通过）
- exp: `1780580190` (2026-05-14) — 服务器未严格执行过期检查

## 文件说明
- `config.json` — 凭据和 API 端点清单
- `auto_course.py` — 自动选课脚本（已修复 Content-Type）
- `CONTEXT.md` — 本文档
