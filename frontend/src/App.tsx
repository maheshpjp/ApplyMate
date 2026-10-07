import { ArrowPathIcon, ArrowRightStartOnRectangleIcon, BriefcaseIcon, BuildingOfficeIcon, CalendarDaysIcon, CheckCircleIcon, DocumentTextIcon, FolderOpenIcon } from '@heroicons/react/24/outline'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useRef, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import {
  deleteResume,
  cancelSchedule,
  createSchedule,
  discoverCareers,
  getApplications,
  getCurrentUser,
  getJobs,
  getResumes,
  getSchedules,
  inspectApplication,
  login,
  register,
  searchResumes,
  submitApplication,
  triggerScheduler,
  uploadResume,
  type Application,
  type Resume,
  type ResumeSearchResult,
  type User,
} from './api'

const navigation = [
  { name: 'Home', to: '/', icon: FolderOpenIcon },
  { name: 'Calendar', to: '/calendar', icon: CalendarDaysIcon },
  { name: 'Jobs', to: '/jobs', icon: BriefcaseIcon },
  { name: 'Resumes', to: '/resumes', icon: DocumentTextIcon },
  { name: 'Companies', to: '/companies', icon: BuildingOfficeIcon },
  { name: 'Applications', to: '/applications', icon: CheckCircleIcon },
]

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('applymate_token'))
  const [user, setUser] = useState<User | null>(null)

  function handleLogin(tokenValue: string, userValue: User) {
    localStorage.setItem('applymate_token', tokenValue)
    setToken(tokenValue)
    setUser(userValue)
  }

  function handleLogout() {
    localStorage.removeItem('applymate_token')
    setToken(null)
    setUser(null)
  }

  if (!token) {
    return <AuthPage onLogin={handleLogin} />
  }

  return (
    <AppLayout user={user} onLogout={handleLogout} />
  )
}

function AuthPage({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      let token: string
      if (mode === 'login') {
        const result = await login({ email, password })
        token = result.access_token
      } else {
        await register({ email, name, password })
        const result = await login({ email, password })
        token = result.access_token
      }

      const currentUser = await getCurrentUser(token)
      onLogin(token, currentUser)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not sign in.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <section className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl">
        <p className="text-sm font-semibold text-blue-600">ApplyMate</p>
        <h1 className="mt-3 text-3xl font-bold text-slate-900">Welcome</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Sign in to track jobs and prepare applications.
        </p>

        <div className="mt-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${mode === 'login' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${mode === 'register' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
          >
            Create account
          </button>
        </div>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label className="block text-sm font-medium text-slate-700">
              Name
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500"
                placeholder="Your name"
              />
            </label>
          )}

          <label className="block text-sm font-medium text-slate-700">
            Email
            <input
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500"
              placeholder="you@example.com"
            />
          </label>

          <label className="block text-sm font-medium text-slate-700">
            Password
            <input
              required
              minLength={8}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500"
              placeholder="At least 8 characters"
            />
          </label>

          {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {isLoading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </section>
    </main>
  )
}

function AppLayout({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col bg-slate-900 p-5 text-white lg:flex">
        <div className="flex items-center gap-3 pb-6">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-blue-500 font-bold">A</div>
          <div>
            <p className="font-semibold">ApplyMate</p>
            <p className="text-xs text-slate-400">Your job helper</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {navigation.map(({ name, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? 'bg-blue-500/20 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
            >
              <Icon className="h-5 w-5" />
              {name}
            </NavLink>
          ))}
        </nav>

        <button type="button" onClick={onLogout} className="flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2.5 text-sm text-slate-200">
          <ArrowRightStartOnRectangleIcon className="h-4 w-4" />
          Sign out
        </button>
      </aside>

      <main className="lg:pl-64">
        <header className="border-b border-slate-200 bg-white/90 backdrop-blur-sm">
          <div className="flex h-16 items-center justify-between px-5 sm:px-8">
            <div>
              <p className="text-sm font-semibold text-slate-900">Hi, {user?.name ?? 'there'}</p>
              <p className="text-xs text-slate-500">Keep your job search moving.</p>
            </div>
            <button type="button" onClick={onLogout} className="rounded-xl border border-slate-200 px-3 py-2 text-sm lg:hidden">
              Sign out
            </button>
          </div>
        </header>

        <div className="p-5 sm:p-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/resumes" element={<ResumesPage />} />
            <Route path="/companies" element={<CompaniesPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function DashboardPage() {
  const queryClient = useQueryClient()
  const { data: jobs = [], isLoading, error } = useQuery({ queryKey: ['jobs'], queryFn: getJobs })
  const schedulerMutation = useMutation({
    mutationFn: triggerScheduler,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="rounded-3xl bg-slate-900 p-7 text-white">
        <p className="text-sm text-blue-300">Your dashboard</p>
        <h1 className="mt-2 text-3xl font-bold">Start your next application.</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
          Check tracked jobs, update your resumes, and prepare applications one step at a time.
        </p>
        <button
          type="button"
          disabled={schedulerMutation.isPending}
          onClick={() => schedulerMutation.mutate()}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-900 disabled:opacity-60"
        >
          <ArrowPathIcon className={`h-4 w-4 ${schedulerMutation.isPending ? 'animate-spin' : ''}`} />
          {schedulerMutation.isPending ? 'Checking jobs…' : 'Check jobs now'}
        </button>
        {schedulerMutation.isError && (
          <p className="mt-4 text-sm text-red-300">{schedulerMutation.error instanceof Error ? schedulerMutation.error.message : 'The check could not run.'}</p>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Stat label="Tracked jobs" value={jobs.length.toString()} />
        <Stat label="Waiting review" value={jobs.filter((job) => job.status === 'monitoring').length.toString()} />
        <Stat label="Drafts" value={jobs.reduce((total, job) => total + job.app_count, 0).toString()} />
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">Tracked jobs</p>
            <h2 className="text-xl font-semibold">Your current list</h2>
          </div>
          <p className="text-sm text-slate-500">{jobs.length} total</p>
        </div>

        {isLoading ? <p className="mt-5 text-sm text-slate-500">Loading…</p> : error ? <p className="mt-5 text-sm text-red-600">Could not load jobs.</p> : jobs.length === 0 ? (
          <p className="mt-5 text-sm text-slate-500">No jobs are being tracked yet.</p>
        ) : (
          <div className="mt-5 space-y-3">
            {jobs.map((job) => (
              <article key={job.id} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold">{job.job_title}</p>
                    <p className="text-sm text-slate-500">{job.company_name}</p>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">{job.status}</span>
                </div>
                <p className="mt-3 text-xs text-slate-500">{job.last_run_at ? `Last checked: ${new Date(job.last_run_at).toLocaleDateString()}` : 'Waiting for its first check'}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
    </article>
  )
}

function localDateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function CalendarPage() {
  const queryClient = useQueryClient()
  const now = new Date()
  const [selectedDate, setSelectedDate] = useState(localDateKey(now))
  const [viewingMonth, setViewingMonth] = useState(new Date(now.getFullYear(), now.getMonth(), 1))
  const [showForm, setShowForm] = useState(false)
  const [companyName, setCompanyName] = useState('')
  const [roleTitle, setRoleTitle] = useState('')
  const [careersUrl, setCareersUrl] = useState('')
  const [scheduledTime, setScheduledTime] = useState(`${localDateKey(now)}T09:00`)
  const [resumeId, setResumeId] = useState('')
  const [autoSubmitAuthorized, setAutoSubmitAuthorized] = useState(false)
  const { data: schedules = [], isLoading, error } = useQuery({ queryKey: ['schedules'], queryFn: getSchedules })
  const { data: resumes = [] } = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const createMutation = useMutation({
    mutationFn: createSchedule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['schedules'] })
      setShowForm(false)
      setCompanyName('')
      setRoleTitle('')
      setCareersUrl('')
      setResumeId('')
      setAutoSubmitAuthorized(false)
    },
  })
  const cancelMutation = useMutation({
    mutationFn: cancelSchedule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const monthStart = new Date(viewingMonth.getFullYear(), viewingMonth.getMonth(), 1)
  const daysInMonth = new Date(viewingMonth.getFullYear(), viewingMonth.getMonth() + 1, 0).getDate()
  const calendarCells = [
    ...Array.from({ length: monthStart.getDay() }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
  ]
  const selectedSchedules = schedules.filter((schedule) => localDateKey(new Date(schedule.scheduled_at)) === selectedDate)
  const selectedDateLabel = new Date(`${selectedDate}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  })

  function selectDay(day: number) {
    const date = new Date(viewingMonth.getFullYear(), viewingMonth.getMonth(), day)
    const dateKey = localDateKey(date)
    setSelectedDate(dateKey)
    setScheduledTime(`${dateKey}T09:00`)
    setShowForm(true)
  }

  function submitSchedule(event: FormEvent) {
    event.preventDefault()
    createMutation.mutate({
      company_name: companyName,
      role_title: roleTitle,
      careers_url: careersUrl,
      scheduled_at: new Date(scheduledTime).toISOString(),
      resume_id: resumeId,
      auto_submit_authorized: autoSubmitAuthorized,
    })
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section className="rounded-3xl bg-slate-900 p-7 text-white">
        <p className="text-sm text-blue-300">Plan ahead</p>
        <h1 className="mt-2 text-3xl font-bold">Job calendar</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Choose when to check a careers page and which resume belongs to that role.</p>
      </section>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <button type="button" title="Previous month" onClick={() => setViewingMonth(new Date(viewingMonth.getFullYear(), viewingMonth.getMonth() - 1, 1))} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-lg hover:bg-slate-50">‹</button>
          <h2 className="text-lg font-semibold">{viewingMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2>
          <button type="button" title="Next month" onClick={() => setViewingMonth(new Date(viewingMonth.getFullYear(), viewingMonth.getMonth() + 1, 1))} className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-lg hover:bg-slate-50">›</button>
        </div>
        <div className="grid grid-cols-7 border-b border-slate-200 bg-slate-50 text-center text-xs font-medium text-slate-500">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => <div key={day} className="py-3">{day}</div>)}
        </div>
        <div className="grid grid-cols-7">
          {calendarCells.map((day, index) => {
            const dayKey = day ? localDateKey(new Date(viewingMonth.getFullYear(), viewingMonth.getMonth(), day)) : ''
            const daySchedules = day ? schedules.filter((schedule) => localDateKey(new Date(schedule.scheduled_at)) === dayKey) : []
            return (
              <button key={`${day ?? 'blank'}-${index}`} type="button" disabled={!day} onClick={() => day && selectDay(day)} className={`min-h-24 border-b border-r border-slate-100 p-2 text-left align-top transition-colors hover:bg-blue-50 sm:min-h-28 ${!day ? 'bg-slate-50/60' : ''} ${dayKey === selectedDate ? 'bg-blue-50 ring-1 ring-inset ring-blue-400' : ''}`}>
                {day && <>
                  <span className={`grid h-7 w-7 place-items-center rounded-full text-sm ${dayKey === localDateKey(now) ? 'bg-slate-900 font-semibold text-white' : 'text-slate-700'}`}>{day}</span>
                  <span className="mt-1 block space-y-1">
                    {daySchedules.slice(0, 2).map((schedule) => <span key={schedule.id} className="block truncate rounded bg-blue-100 px-1.5 py-1 text-[10px] font-medium text-blue-900">{schedule.role_title}</span>)}
                    {daySchedules.length > 2 && <span className="block px-1 text-[10px] text-slate-500">+{daySchedules.length - 2} more</span>}
                  </span>
                </>}
              </button>
            )
          })}
        </div>
      </section>

      <section className="grid items-start gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm text-slate-500">Selected date</p>
              <h2 className="mt-1 text-lg font-semibold">{selectedDateLabel}</h2>
            </div>
            <button type="button" onClick={() => setShowForm((visible) => !visible)} className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700">{showForm ? 'Close form' : 'Schedule role'}</button>
          </div>
          {isLoading ? <p className="mt-5 text-sm text-slate-500">Loading scheduled roles…</p> : error ? <p className="mt-5 text-sm text-red-600">Could not load calendar entries.</p> : selectedSchedules.length === 0 ? <p className="mt-5 text-sm text-slate-500">Nothing scheduled for this day.</p> : <div className="mt-4 divide-y divide-slate-100">{selectedSchedules.map((schedule) => <article key={schedule.id} className="py-4 first:pt-1"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{schedule.role_title}</p><p className="text-sm text-slate-500">{schedule.company_name} · {new Date(schedule.scheduled_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</p><p className="mt-1 text-xs text-slate-500">{schedule.status.replace(/_/g, ' ')} · {resumes.find((resume) => resume.id === schedule.resume_id)?.name ?? 'Selected resume'}</p>{schedule.result_message && <p className="mt-2 text-sm text-slate-600">{schedule.result_message}</p>}</div>{schedule.status === 'scheduled' && <button type="button" onClick={() => cancelMutation.mutate(schedule.id)} disabled={cancelMutation.isPending} className="text-sm text-red-700 hover:underline">Cancel</button>}</div></article>)}</div>}
        </div>

        {showForm && <form onSubmit={submitSchedule} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
          <div><p className="text-sm text-slate-500">New reminder</p><h2 className="mt-1 text-lg font-semibold">What should we check?</h2></div>
          <label className="block text-sm font-medium text-slate-700">Company<input required maxLength={255} value={companyName} onChange={(event) => setCompanyName(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" placeholder="Adobe" /></label>
          <label className="block text-sm font-medium text-slate-700">Role<input required maxLength={255} value={roleTitle} onChange={(event) => setRoleTitle(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" placeholder="Software Engineer Intern" /></label>
          <label className="block text-sm font-medium text-slate-700">Careers page<input required type="url" value={careersUrl} onChange={(event) => setCareersUrl(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" placeholder="https://company.com/careers" /></label>
          <label className="block text-sm font-medium text-slate-700">Check date and time<input required type="datetime-local" min={localDateKey(now) + 'T' + now.toTimeString().slice(0, 5)} value={scheduledTime} onChange={(event) => setScheduledTime(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5" /></label>
          <label className="block text-sm font-medium text-slate-700">Resume for this role<select required value={resumeId} onChange={(event) => setResumeId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5"><option value="">Choose a resume</option>{resumes.map((resume: Resume) => <option key={resume.id} value={resume.id}>{resume.name} ({resume.file_name})</option>)}</select></label>
          {resumes.length === 0 && <p className="text-sm text-amber-700">Upload a resume before scheduling a role.</p>}
          {createMutation.isError && <p role="alert" className="text-sm text-red-700">{createMutation.error.message}</p>}
          <label className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm leading-5 text-amber-950"><input type="checkbox" checked={autoSubmitAuthorized} onChange={(event) => setAutoSubmitAuthorized(event.target.checked)} className="mt-1 h-4 w-4 shrink-0 accent-blue-600" /><span>I authorize ApplyMate to submit this application automatically using this resume and its extracted profile details, including required accuracy and privacy declarations. I confirm the information is accurate. If it encounters unanswered required questions, sign-in, CAPTCHA, or an unsupported form, it will stop without submitting.</span></label>
          <p className="text-xs leading-5 text-slate-500">Automatic form handling varies by careers site. Only confirmed successful submissions are marked submitted.</p>
          <button type="submit" disabled={createMutation.isPending || resumes.length === 0} className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{createMutation.isPending ? 'Saving…' : 'Save schedule'}</button>
        </form>}
      </section>
    </div>
  )
}

function CompaniesPage() {
  const queryClient = useQueryClient()
  const [companyUrl, setCompanyUrl] = useState('')
  const mutation = useMutation({
    mutationFn: discoverCareers,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section className="rounded-3xl bg-slate-900 p-7 text-white">
        <p className="text-sm text-blue-300">Find jobs</p>
        <h1 className="mt-2 text-3xl font-bold">Add a company page</h1>
        <p className="mt-2 text-sm leading-6 text-slate-300">Paste a careers page to find roles and add them to your watch list.</p>
        <form className="mt-6 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => { event.preventDefault(); mutation.mutate(companyUrl) }}>
          <input required type="url" value={companyUrl} onChange={(event) => setCompanyUrl(event.target.value)} placeholder="https://company.com/careers" className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-blue-500" />
          <button type="submit" disabled={mutation.isPending || !companyUrl.trim()} className="rounded-xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">{mutation.isPending ? 'Searching…' : 'Find roles'}</button>
        </form>
        {mutation.isError && <p role="alert" className="mt-3 text-sm text-red-300">{mutation.error instanceof Error && mutation.error.message.trim() ? mutation.error.message : 'The careers page could not be checked. Verify the URL and try again.'}</p>}
      </section>

      {mutation.isSuccess && mutation.data && (
        <section className="rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold">{mutation.data.company_name}</h2>
          <p className="mt-1 text-sm text-slate-500">Added {mutation.data.created_jobs} job{mutation.data.created_jobs === 1 ? '' : 's'}.</p>
          {mutation.data.jobs.length === 0 ? <p className="mt-5 text-sm text-slate-500">{mutation.data.message ?? 'No roles were found.'}</p> : <div className="mt-5 space-y-3">{mutation.data.jobs.map((job) => <a key={job.job_url} href={job.job_url} target="_blank" rel="noreferrer" className="block rounded-2xl border border-slate-200 p-4 text-sm hover:border-blue-300"><span className="font-semibold text-slate-900">{job.job_title}</span><span className="mt-1 block text-slate-500">Open role</span></a>)}</div>}
        </section>
      )}
    </div>
  )
}

function ResumesPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [search, setSearch] = useState('')
  const [searchResults, setSearchResults] = useState<ResumeSearchResult[]>([])
  const [showResults, setShowResults] = useState(false)

  const { data: resumes = [], isLoading, error, refetch } = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const uploadMutation = useMutation({
    mutationFn: uploadResume,
    onSuccess: () => {
      refetch()
      setName('')
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
  })
  const deleteMutation = useMutation({ mutationFn: deleteResume, onSuccess: () => refetch() })
  const searchMutation = useMutation({
    mutationFn: () => searchResumes(search),
    onSuccess: (results) => {
      setSearchResults(results)
      setShowResults(true)
    },
  })

  async function handleUpload(event: FormEvent) {
    event.preventDefault()
    if (!selectedFile) return
    const formData = new FormData()
    formData.append('name', name || selectedFile.name)
    formData.append('is_default', 'false')
    formData.append('file', selectedFile)
    uploadMutation.mutate(formData)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="rounded-3xl bg-slate-900 p-7 text-white">
        <p className="text-sm text-blue-300">Your resumes</p>
        <h1 className="mt-2 text-3xl font-bold">Upload and search</h1>
        <form className="mt-6 grid gap-3 md:grid-cols-[1fr_auto]" onSubmit={handleUpload}>
          <input type="text" value={name} onChange={(event) => setName(event.target.value)} placeholder="Resume name" className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          <input ref={fileInputRef} type="file" accept=".pdf,.docx" required onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-500 file:px-3 file:py-2" />
          <button type="submit" disabled={uploadMutation.isPending || !selectedFile} className="rounded-xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50 md:col-span-2">{uploadMutation.isPending ? 'Uploading…' : 'Upload resume'}</button>
        </form>
        {uploadMutation.isError && <p role="alert" className="mt-3 text-sm text-red-300">{uploadMutation.error.message}</p>}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">Search resume content</h2>
        <div className="mt-4 flex gap-3">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search skills or experience" className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500" />
          <button type="button" onClick={() => searchMutation.mutate()} disabled={searchMutation.isPending || !search.trim()} className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50">Search</button>
        </div>
        {searchMutation.isError && <p className="mt-3 text-sm text-red-600">Search failed.</p>}
        {showResults && searchResults.length === 0 && <p className="mt-4 text-sm text-slate-500">No matching content was found.</p>}
        {showResults && searchResults.length > 0 && <div className="mt-5 space-y-3">{searchResults.map((result) => <article key={result.id} className="rounded-2xl border border-slate-200 p-4"><p className="text-sm font-semibold">{result.section ?? 'Resume content'}</p><p className="mt-2 text-sm leading-6 text-slate-700">{result.content}</p></article>)}</div>}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Stored resumes</h2>
          <span className="text-sm text-slate-500">{resumes.length}</span>
        </div>
        {isLoading ? <p className="mt-5 text-sm text-slate-500">Loading…</p> : error ? <p className="mt-5 text-sm text-red-600">Could not load resumes.</p> : resumes.length === 0 ? <p className="mt-5 text-sm text-slate-500">No resumes uploaded yet.</p> : <div className="mt-5 grid gap-3 md:grid-cols-2">{resumes.map((resume) => <article key={resume.id} className="rounded-2xl border border-slate-200 p-4"><p className="font-semibold">{resume.name}</p><p className="mt-1 text-sm text-slate-500">{resume.file_name}</p><button type="button" onClick={() => { if (window.confirm(`Delete ${resume.name}?`)) deleteMutation.mutate(resume.id) }} disabled={deleteMutation.isPending} className="mt-4 text-sm text-red-600 disabled:opacity-50">Delete</button></article>)}</div>}
      </section>
    </div>
  )
}

function JobsPage() {
  const { data: jobs = [], isLoading, error } = useQuery({ queryKey: ['jobs'], queryFn: getJobs })

  return (
    <div className="mx-auto max-w-4xl">
      <section className="rounded-3xl bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Jobs</p>
        <h1 className="mt-1 text-3xl font-bold">Your tracked roles</h1>
        {isLoading ? <p className="mt-5 text-sm text-slate-500">Loading…</p> : error ? <p className="mt-5 text-sm text-red-600">Could not load jobs.</p> : jobs.length === 0 ? <p className="mt-5 text-sm text-slate-500">No jobs are tracked yet.</p> : <div className="mt-5 space-y-3">{jobs.map((job) => <article key={job.id} className="rounded-2xl border border-slate-200 p-4"><p className="font-semibold">{job.job_title}</p><p className="mt-1 text-sm text-slate-500">{job.company_name}</p><a href={job.job_url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm text-blue-600">Open job</a></article>)}</div>}
      </section>
    </div>
  )
}

function ApplicationsPage() {
  const queryClient = useQueryClient()
  const { data: applications = [], isLoading, error } = useQuery({ queryKey: ['applications'], queryFn: getApplications })
  const inspectMutation = useMutation({ mutationFn: inspectApplication })
  const submitMutation = useMutation({
    mutationFn: submitApplication,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }),
  })
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null)
  const [inspection, setInspection] = useState<Awaited<ReturnType<typeof inspectApplication>> | null>(null)

  async function openInspection(application: Application) {
    setSelectedApplication(application)
    setInspection(null)
    try {
      setInspection(await inspectMutation.mutateAsync(application.id))
    } catch {
      setInspection(null)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <section className="rounded-3xl bg-slate-900 p-7 text-white">
        <p className="text-sm text-blue-300">Applications</p>
        <h1 className="mt-2 text-3xl font-bold">Review your drafts</h1>
        <p className="mt-2 text-sm text-slate-300">Check each draft before sending it.</p>
      </section>

      {isLoading ? <p className="text-sm text-slate-500">Loading…</p> : error ? <p className="text-sm text-red-600">Could not load applications.</p> : applications.length === 0 ? <p className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-500">No drafts yet.</p> : <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">{applications.map((application) => <button key={application.id} type="button" onClick={() => openInspection(application)} className={`w-full rounded-2xl border p-4 text-left ${selectedApplication?.id === application.id ? 'border-blue-500 bg-blue-50' : 'border-slate-200 bg-white'}`}><p className="text-sm text-slate-500">Draft</p><p className="mt-1 font-semibold">Application {application.id.slice(0, 8)}</p><p className="mt-1 text-sm text-slate-500">{application.status}</p></button>)}<article className="rounded-3xl border border-slate-200 bg-white p-6">{selectedApplication ? <><p className="text-sm text-slate-500">Draft details</p><h2 className="mt-1 text-2xl font-bold">{inspection?.job_title ?? 'Job details'}</h2><p className="mt-2 text-sm text-slate-500">{inspection?.company_name ?? ''}</p>{inspectMutation.isPending && <p className="mt-4 text-sm text-slate-500">Loading details…</p>}{inspectMutation.isError && <p className="mt-4 text-sm text-red-600">Details could not be loaded.</p>}{inspection && <div className="mt-5 space-y-4"><p className="text-sm leading-6 text-slate-700">{inspection.description || 'No description was found.'}</p><p className="text-sm leading-6 text-slate-700">{inspection.requirements || 'No requirements were found.'}</p><p className="text-sm text-slate-500">Resume notes: {selectedApplication.notes || 'None'}</p><button type="button" onClick={() => submitMutation.mutate(selectedApplication.id)} disabled={submitMutation.isPending} className="rounded-xl border border-red-200 px-4 py-2.5 text-sm font-medium text-red-700 disabled:opacity-50">Submit when ready</button>{submitMutation.isError && <p className="text-sm text-red-600">{submitMutation.error instanceof Error ? submitMutation.error.message : 'Submission was blocked.'}</p>}{submitMutation.isSuccess && <p className="text-sm text-emerald-700">The draft was submitted.</p>}</div>}</> : <p className="mt-8 text-center text-sm text-slate-500">Choose a draft to review it.</p>}</article></div>}
    </div>
  )
}

export default App
