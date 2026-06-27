<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getStudent, getGrades, refreshGrades, reloginStudent } from '../api'
import type { Student, GradeItem, GradeRefreshResult } from '../types'
import GradeTable from '../components/GradeTable.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()

const student = ref<Student | null>(null)
const grades = ref<GradeItem[]>([])
const loading = ref(true)
const refreshing = ref(false)
const result = ref<GradeRefreshResult | null>(null)

const semesters = computed(() => {
  const set = new Set(grades.value.map(g => g.semester))
  return Array.from(set).sort().reverse()
})

async function load() {
  loading.value = true
  try {
    const [s, g] = await Promise.all([getStudent(props.id), getGrades(props.id)])
    student.value = s
    grades.value = g
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

async function refresh() {
  refreshing.value = true
  result.value = null
  try {
    result.value = await refreshGrades(props.id)
    const g = await getGrades(props.id)
    grades.value = g
  } catch (e: any) {
    if (e.response?.status === 502) {
      await reloginStudent(props.id)
      await refresh()
    } else {
      alert('刷新失败: ' + (e.response?.data?.detail || e.message))
    }
  }
  refreshing.value = false
}

onMounted(load)
</script>

<template>
  <div class="detail-page">
    <!-- Top Bar -->
    <header class="detail-topbar">
      <div class="topbar-inner">
        <button class="btn-back" @click="router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
          返回
        </button>
        <div class="brand-sm">◈ RUC 成绩监控</div>
      </div>
    </header>

    <main class="detail-main">
      <div v-if="loading" class="state-box">
        <div class="spinner"></div>
      </div>

      <template v-else-if="student">
        <!-- Student Header -->
        <div class="student-header">
          <div class="header-left">
            <h2>{{ student.name || student.student_id }}</h2>
            <div class="header-meta">
              <span class="meta-tag">学号 {{ student.student_id }}</span>
              <span class="meta-tag" v-if="student.grade">年级 {{ student.grade }}</span>
              <span class="meta-tag" v-if="student.major">{{ student.major }}</span>
            </div>
          </div>
          <div class="header-right">
            <span class="grade-count-badge">{{ grades.length }} 门成绩</span>
            <button class="btn-refresh" :disabled="refreshing" @click="refresh">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spinning: refreshing }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ refreshing ? '刷新中...' : '刷新成绩' }}
            </button>
          </div>
        </div>

        <!-- Refresh Result Banner -->
        <div v-if="result" class="result-banner">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <span>刷新完成：共 {{ result.total }} 门，新增 <strong>{{ result.new_count }}</strong> 门，更新 <strong>{{ result.updated_count }}</strong> 门</span>
        </div>

        <!-- Grade Table -->
        <GradeTable :grades="grades" :newIds="result?.new_grades.map(g => g.cjgl016id) || []" />
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--paper);
}
.detail-topbar {
  background: var(--ink-900);
  position: sticky;
  top: 0;
  z-index: 50;
}
.detail-topbar .topbar-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 28px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.btn-back {
  background: none;
  color: #ccc;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}
.btn-back:hover { color: #fff; background: rgba(255,255,255,0.08); }
.brand-sm {
  font-size: 14px;
  color: var(--ink-300);
}

.detail-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 28px;
}

.state-box { text-align: center; padding: 80px; }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--ink-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Student Header */
.student-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}
.header-left h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--ink-900);
  margin-bottom: 8px;
}
.header-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.meta-tag {
  font-size: 12px;
  color: var(--ink-600);
  background: var(--white);
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid var(--ink-100);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.grade-count-badge {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-600);
  background: var(--white);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ink-100);
}
.btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--ink-900);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
}
.btn-refresh:hover { background: var(--ink-800); }
.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.spinning { animation: spin 1s linear infinite; }

/* Result Banner */
.result-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--jade-light);
  border: 1px solid var(--jade);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--ink-800);
}
.result-banner svg { color: var(--jade); flex-shrink: 0; }
</style>
