<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Student } from '../types'

const props = defineProps<{ student: Student }>()
const emit = defineEmits<{ toggleMonitor: []; delete: [] }>()
const router = useRouter()

function formatTime(t: string | null) {
  if (!t) return '暂无记录'
  const d = new Date(t)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <article class="card" :class="{ monitored: student.is_monitored }">
    <div class="card-accent"></div>

    <div class="card-header">
      <div class="card-identity" @click="router.push(`/student/${student.student_id}`)">
        <h3>{{ student.name || student.student_id }}</h3>
        <span class="sid">{{ student.student_id }}</span>
      </div>

      <div class="card-actions">
        <label class="toggle-switch" :title="student.is_monitored ? '取消监控' : '加入监控'">
          <input
            type="checkbox"
            :checked="student.is_monitored"
            @change="emit('toggleMonitor')"
          />
          <span class="toggle-slider"></span>
        </label>
        <button class="btn-delete" @click.stop="emit('delete')" title="删除">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
        </button>
      </div>
    </div>

    <div class="card-body" @click="router.push(`/student/${student.student_id}`)">
      <div class="stat-col">
        <span class="stat-num">{{ student.grade_count }}</span>
        <span class="stat-label">门成绩</span>
      </div>
      <div class="meta-col">
        <div class="meta-row">
          <span class="meta-label">最近变动</span>
          <span class="meta-value">{{ formatTime(student.last_change_at) }}</span>
        </div>
        <div class="meta-row" v-if="student.is_monitored">
          <span class="meta-label">监控状态</span>
          <span class="meta-value monitoring-on">监控中</span>
        </div>
        <div class="meta-row" v-else>
          <span class="meta-label">监控状态</span>
          <span class="meta-value monitoring-off">未监控</span>
        </div>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  position: relative;
  background: var(--white);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition);
  border: 1px solid transparent;
}
.card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.card.monitored {
  border-color: var(--jade-light);
}
.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--ink-200);
  transition: background var(--transition);
}
.card.monitored .card-accent {
  background: var(--jade);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 20px 0;
}
.card-identity {
  cursor: pointer;
  flex: 1;
  min-width: 0;
}
.card-identity h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sid {
  font-size: 12px;
  color: var(--ink-300);
  margin-top: 2px;
  display: block;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
  cursor: pointer;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--ink-200);
  border-radius: 11px;
  transition: background var(--transition);
}
.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 2px;
  bottom: 2px;
  background: #fff;
  border-radius: 50%;
  transition: transform var(--transition);
}
.toggle-switch input:checked + .toggle-slider {
  background: var(--jade);
}
.toggle-switch input:checked + .toggle-slider::before {
  transform: translateX(18px);
}

.btn-delete {
  background: none;
  color: var(--ink-200);
  padding: 4px;
  border-radius: var(--radius-sm);
}
.btn-delete:hover {
  color: var(--cinnabar);
  background: var(--cinnabar-light);
}

.card-body {
  display: flex;
  gap: 28px;
  padding: 16px 20px 20px;
  cursor: pointer;
}
.stat-col {
  text-align: center;
  flex-shrink: 0;
}
.stat-num {
  font-size: 34px;
  font-weight: 700;
  color: var(--ink-800);
  display: block;
  line-height: 1;
}
.stat-label {
  font-size: 12px;
  color: var(--ink-300);
  margin-top: 4px;
  display: block;
}
.meta-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  justify-content: center;
}
.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.meta-label {
  color: var(--ink-300);
}
.meta-value {
  color: var(--ink-600);
  font-weight: 500;
}
.monitoring-on { color: var(--jade); }
.monitoring-off { color: var(--ink-300); }
</style>
