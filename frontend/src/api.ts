const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export type User = {
  id: string
  email: string
  name: string
}

export type Job = {
  id: string
  user_id: string
  company_name: string
  job_title: string
  job_url: string
  source: string
  status: string
  match_score: number | null
  last_run_at: string | null
  created_at: string
  updated_at: string
  app_count: number
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('applymate_token')
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const message = await readError(response)
    throw new Error(message || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

async function readError(response: Response): Promise<string> {
  try {
    const data = await response.json() as { detail?: string | { msg?: string }[] }
    if (typeof data.detail === 'string' && data.detail.trim()) return data.detail
    if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg ?? 'Invalid input').join(', ')
  } catch {
    // The response may contain plain text instead of JSON.
  }

  return response.statusText || 'Request failed.'
}

export function register(payload: { email: string; name: string; password: string }) {
  return request<{ access_token: string; token_type: string }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function login(payload: { email: string; password: string }) {
  return request<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCurrentUser(token: string) {
  return request<User>('/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createJob(payload: {
  company_name: string
  job_title: string
  job_url: string
  source: string
}) {
  return request<Job>('/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getJobs() {
  return request<Job[]>('/jobs')
}

export function triggerScheduler() {
  return request<{ status: string; jobs_processed: number }>('/scheduler/run', {
    method: 'POST',
  })
}

export type Resume = {
  id: string
  name: string
  file_name: string
  content_type: string
  is_default: boolean
  metadata_json: string | null
  created_at: string
  updated_at: string
}

export type ResumeSearchResult = {
  id: string
  content: string
  score: number
  section: string | null
  metadata: Record<string, unknown>
  resume_id: string
  user_id: string
}

export function uploadResume(formData: FormData) {
  return fetch(`${API_BASE_URL}/resumes`, {
    method: 'POST',
    headers: {
      ...(localStorage.getItem('applymate_token') ? { Authorization: `Bearer ${localStorage.getItem('applymate_token')}` } : {}),
    },
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      const message = await readError(response)
      throw new Error(message || `Upload failed with status ${response.status}`)
    }
    return response.json() as Promise<Resume>
  })
}

export function getResumes() {
  return request<Resume[]>('/resumes')
}

export type ScheduledApplication = {
  id: string
  user_id: string
  company_name: string
  role_title: string
  careers_url: string
  scheduled_at: string
  resume_id: string
  auto_submit_authorized: boolean
  status: string
  result_message: string | null
  matched_job_id: string | null
  created_at: string
  updated_at: string
}

export function getSchedules() {
  return request<ScheduledApplication[]>('/schedules')
}

export function createSchedule(payload: {
  company_name: string
  role_title: string
  careers_url: string
  scheduled_at: string
  resume_id: string
  auto_submit_authorized: boolean
}) {
  return request<ScheduledApplication>('/schedules', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function cancelSchedule(scheduleId: string) {
  return request<void>(`/schedules/${scheduleId}`, { method: 'DELETE' })
}

export function searchResumes(query: string, topK = 5) {
  return request<ResumeSearchResult[]>('/resumes/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK }),
  })
}

export function deleteResume(resumeId: string) {
  return request<void>(`/resumes/${resumeId}`, { method: 'DELETE' })
}

export type DiscoveredJob = {
  job_title: string
  job_url: string
  company_name: string
  source: string
}

export type JobDiscoveryResult = {
  company_url: string
  company_name: string
  discovered_jobs: number
  created_jobs: number
  jobs: DiscoveredJob[]
  message: string | null
}

export function discoverCareers(companyUrl: string) {
  const params = new URLSearchParams({ company_url: companyUrl })
  return request<JobDiscoveryResult>(`/companies/discover-careers?${params.toString()}`, {
    method: 'POST',
  })
}

export type Application = {
  id: string
  user_id: string
  job_id: string
  resume_id: string
  status: string
  cover_letter: string | null
  notes: string | null
  submitted_at: string | null
  created_at: string
  updated_at: string
}

export function getApplications() {
  return request<Application[]>('/applications')
}

export function inspectApplication(applicationId: string) {
  return request<{ job_title: string; company_name: string; description: string; requirements: string; source_url: string; extracted_at: string }>(`/applications/${applicationId}/inspect`, {
    method: 'POST',
  })
}

export function submitApplication(applicationId: string) {
  return request<{ detail: string }>(`/applications/${applicationId}/submit`, {
    method: 'POST',
  })
}
