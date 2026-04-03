const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function createJob(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: '上传失败' }))
    throw new Error(payload.detail || '上传失败')
  }

  return response.json()
}

export async function getJob(jobId) {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`)
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: '查询任务失败' }))
    throw new Error(payload.detail || '查询任务失败')
  }
  return response.json()
}

export async function getResult(jobId) {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/result`)
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: '获取结果失败' }))
    throw new Error(payload.detail || '获取结果失败')
  }
  return response.json()
}
