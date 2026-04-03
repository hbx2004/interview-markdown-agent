<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import { createJob, getJob, getResult } from './api'

const STORAGE_KEY = 'interview-markdown-app-state'

const file = ref(null)
const jobId = ref('')
const status = ref('')
const stage = ref('')
const progress = ref(0)
const message = ref('')
const markdown = ref('')
const downloadingName = ref('interview.md')
const exportFilename = ref('interview.md')
const error = ref('')
const loading = ref(false)

let timer = null

const renderedMarkdown = computed(() => marked.parse(markdown.value || ''))
const progressLabel = computed(() => {
  const labels = {
    queued: '任务已创建',
    preparing_audio: '正在提取音频',
    transcribing: '正在语音转写',
    formatting_markdown: '正在整理 Markdown',
    completed: '处理完成',
    failed: '处理失败',
  }
  return labels[stage.value] || '处理中'
})

function handleFileChange(event) {
  file.value = event.target.files?.[0] || null
  error.value = ''
}

async function startUpload() {
  if (!file.value) {
    error.value = '请先选择一个音频或视频文件。'
    return
  }

  resetJobState()
  loading.value = true

  try {
    const created = await createJob(file.value)
    jobId.value = created.job_id
    status.value = created.status
    stage.value = created.status
    progress.value = 5
    message.value = '文件上传成功，任务已创建。'
    beginPolling()
  } catch (err) {
    error.value = err.message
    loading.value = false
  }
}

function beginPolling() {
  stopPolling()
  timer = window.setInterval(fetchStatus, 2000)
  fetchStatus()
}

async function fetchStatus() {
  if (!jobId.value) return

  try {
    const job = await getJob(jobId.value)
    status.value = job.status
    stage.value = job.stage || job.status
    progress.value = typeof job.progress === 'number' ? job.progress : 0
    message.value = job.message || ''

    if (job.status === 'completed') {
      stopPolling()
      const result = await getResult(jobId.value)
      markdown.value = result.markdown
      downloadingName.value = result.filename
      exportFilename.value = result.filename
      loading.value = false
    } else if (job.status === 'failed') {
      stopPolling()
      loading.value = false
      error.value = job.message || '任务处理失败。'
    }
  } catch (err) {
    stopPolling()
    loading.value = false
    error.value = err.message
  }
}

async function downloadMarkdown() {
  const filename = normalizeFilename(exportFilename.value || downloadingName.value || 'interview.md')
  const blob = new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' })

  if ('showSaveFilePicker' in window) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [
          {
            description: 'Markdown 文件',
            accept: {
              'text/markdown': ['.md'],
            },
          },
        ],
      })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      downloadingName.value = filename
      exportFilename.value = filename
      return
    } catch (err) {
      if (err?.name === 'AbortError') {
        return
      }
    }
  }

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
  downloadingName.value = filename
  exportFilename.value = filename
}

function normalizeFilename(value) {
  const trimmed = value.trim() || 'interview.md'
  return trimmed.toLowerCase().endsWith('.md') ? trimmed : `${trimmed}.md`
}

function resetJobState() {
  markdown.value = ''
  status.value = ''
  stage.value = ''
  progress.value = 0
  message.value = ''
  error.value = ''
  exportFilename.value = 'interview.md'
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

function persistState() {
  const payload = {
    jobId: jobId.value,
    status: status.value,
    stage: stage.value,
    progress: progress.value,
    message: message.value,
    markdown: markdown.value,
    downloadingName: downloadingName.value,
    exportFilename: exportFilename.value,
    error: error.value,
    loading: loading.value,
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
}

function restoreState() {
  const raw = window.localStorage.getItem(STORAGE_KEY)
  if (!raw) return

  try {
    const payload = JSON.parse(raw)
    jobId.value = payload.jobId || ''
    status.value = payload.status || ''
    stage.value = payload.stage || ''
    progress.value = typeof payload.progress === 'number' ? payload.progress : 0
    message.value = payload.message || ''
    markdown.value = payload.markdown || ''
    downloadingName.value = payload.downloadingName || 'interview.md'
    exportFilename.value = payload.exportFilename || payload.downloadingName || 'interview.md'
    error.value = payload.error || ''
    loading.value = Boolean(payload.loading)
  } catch {
    window.localStorage.removeItem(STORAGE_KEY)
  }
}

watch(
  [jobId, status, stage, progress, message, markdown, downloadingName, exportFilename, error, loading],
  persistState,
  { deep: false },
)

onMounted(() => {
  restoreState()
  if (jobId.value && status.value && status.value !== 'completed' && status.value !== 'failed') {
    beginPolling()
  }
})

onBeforeUnmount(() => stopPolling())
</script>

<template>
  <main class="page">
    <section class="hero">
      <p class="eyebrow">Interview Markdown Studio</p>
      <h1>把音频或视频整理成可读的面试 Markdown</h1>
      <p class="subtitle">
        本地转写，自动区分面试官/候选人，修正明显识别错误，并生成适合归档的对话稿。
      </p>
    </section>

    <section class="panel upload-panel">
      <label class="upload-box">
        <span>选择音频或视频文件</span>
        <input type="file" accept="audio/*,video/*" @change="handleFileChange" />
        <strong>{{ file ? file.name : '支持 mp3 / wav / mp4 / mov 等常见格式' }}</strong>
      </label>

      <button class="primary-btn" :disabled="loading" @click="startUpload">
        {{ loading ? '处理中...' : '开始转换' }}
      </button>

      <div v-if="status" class="status-card">
        <span class="status-tag">{{ status }}</span>
        <div class="progress-meta">
          <strong>{{ progressLabel }}</strong>
          <span>{{ progress }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
        <p>{{ message }}</p>
        <p v-if="jobId" class="job-id">任务 ID: {{ jobId }}</p>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
    </section>

    <section class="panel preview-panel">
      <div class="preview-header">
        <div>
          <p class="preview-label">Markdown 预览</p>
          <h2>整理结果</h2>
        </div>
        <div class="download-actions">
          <input
            v-model="exportFilename"
            class="filename-input"
            type="text"
            placeholder="输入导出文件名"
          />
          <button class="secondary-btn" :disabled="!markdown" @click="downloadMarkdown">
            下载
          </button>
        </div>
      </div>

      <div v-if="markdown" class="markdown-body" v-html="renderedMarkdown"></div>
      <div v-else class="empty-state">
        上传文件并等待处理完成后，这里会显示整理后的 Markdown 内容。
      </div>
    </section>
  </main>
</template>
