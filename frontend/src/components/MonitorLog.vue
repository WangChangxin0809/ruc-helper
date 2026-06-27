<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

interface LogEntry {
  id: number; student_id: string; status: string; message: string; created_at: string
}

const logs = ref<LogEntry[]>([])
const expanded = ref(false)
let timer: any = null

async function fetch() {
  try {
    const r = await axios.get('/api/monitor/logs')
    logs.value = r.data
  } catch (_) { /* ignore */ }
}

onMounted(() => { fetch(); timer = setInterval(fetch, 5000) })
onUnmounted(() => clearInterval(timer))

function statusLabel(s: string) {
  if (s === 'ok') return '✅'
  if (s === 'fail') return '❌'
  return '⏸'
}
function statusColor(s: string) {
  if (s === 'ok') return '#27ae60'
  if (s === 'fail') return '#e74c3c'
  return '#999'
}
function formatTime(t: string) {
  if (!t) return ''
  return t.substring(11, 19)
}
</script>

<template>
  <div class="log-panel">
    <div class="log-header" @click="expanded = !expanded">
      <span>📋 监控日志</span>
      <span class="arrow">{{ expanded ? '▾' : '▸' }}</span>
    </div>
    <div v-if="expanded" class="log-body">
      <div v-if="!logs.length" class="empty">暂无记录</div>
      <div v-for="l in logs" :key="l.id" class="log-entry">
        <span :style="{color: statusColor(l.status)}">{{ statusLabel(l.status) }}</span>
        <span class="log-time">{{ formatTime(l.created_at) }}</span>
        <span class="log-sid">{{ l.student_id }}</span>
        <span class="log-msg">{{ l.message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 20px;
  font-size: 13px;
}
.log-header {
  display: flex;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  font-weight: 600;
  color: #333;
}
.arrow { color: #999; }
.log-body { max-height: 300px; overflow-y: auto; padding: 0 16px 10px; }
.empty { padding: 20px; text-align: center; color: #999; }
.log-entry {
  display: flex;
  gap: 10px;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
  align-items: center;
}
.log-time { color: #999; font-family: monospace; min-width: 60px; }
.log-sid { color: #1a5276; font-weight: 500; min-width: 80px; }
.log-msg { color: #555; }
</style>
