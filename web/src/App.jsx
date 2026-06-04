import { useState, useRef, useEffect, useCallback } from 'react'

/**
 * ═══════════════════════════════════════════════════════════════
 * 走起 GoNow — 本地场景短时活动规划网页应用
 *
 * 设计语言（参考 TryPost）：
 *   - 米白底 + 暖珊瑚橙强调色，浅色清爽 SaaS 风
 *   - 大号衬线标题（display serif）配干净无衬线正文
 *   - 产品截图式卡片：描边 / 圆角 / mac 红绿灯 / 状态条
 *   - 统一内联线性图标（无第三方图标库依赖）
 *
 * 逻辑（SSE 流式规划）与上一版一致，仅重做表现层。
 * 后端 SSE 事件契约：step / skeleton / chunk / booking / done / error
 * ═══════════════════════════════════════════════════════════════
 */

// ════════════════════════════════════════════════════════════════
// 内联线性图标（stroke 风格，currentColor 着色，无依赖）
// ════════════════════════════════════════════════════════════════

const Icon = ({ path, size = 20, className = '', strokeWidth = 1.6 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {path}
  </svg>
)

const icons = {
  car: <><path d="M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13" /><path d="M5 13h14v4a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H8v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z" /><circle cx="7.5" cy="15.5" r=".5" /><circle cx="16.5" cy="15.5" r=".5" /></>,
  food: <><path d="M6 3v7a2 2 0 0 0 2 2 2 2 0 0 0 2-2V3" /><path d="M8 3v18" /><path d="M16 3c-1.5 0-2.5 1.8-2.5 4s1 4 2.5 4v10" /></>,
  play: <><circle cx="12" cy="12" r="9" /><path d="M10 9l5 3-5 3z" /></>,
  eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z" /><circle cx="12" cy="12" r="2.5" /></>,
  shop: <><path d="M6 7h12l-1 13H7z" /><path d="M9 7a3 3 0 0 1 6 0" /></>,
  rest: <><path d="M3 12h11a4 4 0 0 1 4 4v2H3z" /><path d="M3 8v10" /><path d="M7 12V9a1 1 0 0 1 1-1h4" /></>,
  pin: <><path d="M12 21s-6-5.3-6-10a6 6 0 0 1 12 0c0 4.7-6 10-6 10z" /><circle cx="12" cy="11" r="2" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  wallet: <><path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M16 12h3v-2h-3a1 1 0 0 0 0 2z" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 9h18M8 3v4M16 3v4" /></>,
  spark: <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /></>,
  send: <><path d="M4 12l16-7-7 16-2-7z" /><path d="M11 14l9-9" /></>,
  check: <><path d="M20 6L9 17l-5-5" /></>,
  cross: <><path d="M18 6L6 18M6 6l12 12" /></>,
  alert: <><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17v.01" /></>,
  route: <><circle cx="6" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="M8 6h6a4 4 0 0 1 0 8H8a4 4 0 0 0 0 8" opacity=".5" /><path d="M8 6h6a4 4 0 0 1 0 8h-4" /></>,
  users: <><circle cx="9" cy="8" r="3" /><path d="M4 20a5 5 0 0 1 10 0" /><path d="M16 6a3 3 0 0 1 0 6M20 20a5 5 0 0 0-3.5-4.8" /></>,
  github: <path d="M9 19c-4 1.5-4-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12 12 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" />,
  gear: <><circle cx="12" cy="12" r="3" /><path d="M12 2l1.5 2.5 2.9-.5.4 2.9 2.5 1.5-1.4 2.6 1.4 2.6-2.5 1.5-.4 2.9-2.9-.5L12 22l-1.5-2.5-2.9.5-.4-2.9L4.7 16l1.4-2.6L4.7 10.8l2.5-1.5.4-2.9 2.9.5z" opacity=".55" /></>,
  key: <><circle cx="7.5" cy="15.5" r="4.5" /><path d="M10.5 12.5l8-8M15.5 4.5l3 3M13 7l2.5 2.5" /></>,
}

// 活动类型 → 图标 + 主题色（浅色卡片）
const ACTIVITY_META = {
  交通: { icon: 'car', tint: 'bg-sky-50 text-sky-600 ring-sky-100' },
  移动: { icon: 'car', tint: 'bg-sky-50 text-sky-600 ring-sky-100' },
  吃: { icon: 'food', tint: 'bg-orange-50 text-orange-600 ring-orange-100' },
  玩: { icon: 'play', tint: 'bg-rose-50 text-rose-600 ring-rose-100' },
  看: { icon: 'eye', tint: 'bg-violet-50 text-violet-600 ring-violet-100' },
  购: { icon: 'shop', tint: 'bg-emerald-50 text-emerald-600 ring-emerald-100' },
  休: { icon: 'rest', tint: 'bg-indigo-50 text-indigo-600 ring-indigo-100' },
  配送: { icon: 'send', tint: 'bg-amber-50 text-amber-600 ring-amber-100' },
}
const DEFAULT_META = { icon: 'pin', tint: 'bg-stone-100 text-stone-500 ring-stone-200' }
const metaFor = (type) => ACTIVITY_META[type] ?? DEFAULT_META

// ════════════════════════════════════════════════════════════════
// 常量
// ════════════════════════════════════════════════════════════════

const API = { PLAN_STREAM: '/api/plan/stream', HEALTH: '/api/health' }

const EXAMPLE_PROMPTS = [
  { icon: 'users', text: '今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下' },
  { icon: 'spark', text: '周末下午想和朋友聚会，4个人，2男2女，有哪些好玩的？' },
]
const PLACEHOLDER = '今天下午是空的，想和老婆孩子出去玩几个小时，别离家太远，帮我安排一下'

// ════════════════════════════════════════════════════════════════
// API 调用（流式，逐事件回调）
// ════════════════════════════════════════════════════════════════

async function callPlan(message, { auto_execute = false, onEvent, signal, llmKey, amapKey } = {}) {
  const body = { message, auto_execute }
  if (llmKey) body.llm_api_key = llmKey
  if (amapKey) body.amap_api_key = amapKey
  const res = await fetch(API.PLAN_STREAM, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  if (!res.body) throw new Error('响应不支持流式读取')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let curEvent = null
  let curData = null

  const parse = (raw) => { try { return JSON.parse(raw) } catch { return raw } }
  const flush = () => {
    if (curEvent && curData !== null) onEvent?.({ event: curEvent, data: parse(curData) })
    curEvent = null
    curData = null
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        const t = line.trim()
        if (!t) { flush(); continue }
        if (t.startsWith('event:')) curEvent = t.slice(6).trim()
        else if (t.startsWith('data:')) curData = t.slice(5).trim()
      }
    }
    flush()
  } finally {
    reader.releaseLock()
  }
}

async function callHealth() {
  const offline = { status: 'offline', llm_configured: false }
  try {
    const res = await fetch(API.HEALTH)
    if (!res.ok) return offline
    return await res.json()
  } catch { return offline }
}

function extractPlanJson(text) {
  if (!text) return null
  const fenced = text.match(/```json\s*([\s\S]*?)```/)
  try { return JSON.parse((fenced ? fenced[1] : text).trim()) } catch { return null }
}

// ════════════════════════════════════════════════════════════════
// 小组件
// ════════════════════════════════════════════════════════════════

/** 角标小药丸（黑描边、轻微旋转，TryPost 风格） */
function TiltPill({ children, className = '', rotate = '-2deg' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold tracking-wide uppercase rounded-lg border-2 border-stone-900 shadow-[2px_2px_0_0_#1c1917] ${className}`}
      style={{ transform: `rotate(${rotate})` }}
    >
      {children}
    </span>
  )
}

/** 进度步骤（线性、连点） */
function StepTracker({ steps }) {
  if (!steps.length) return null
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-2 text-sm mb-6">
      {steps.map((s, i) => (
        <span key={i} className="inline-flex items-center gap-2 animate-fadeIn">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-orange-500 text-white">
            <Icon path={icons.check} size={13} strokeWidth={2.4} />
          </span>
          <span className="text-stone-600">{s}</span>
          {i < steps.length - 1 && <span className="text-stone-300">/</span>}
        </span>
      ))}
    </div>
  )
}

/** 结构化行程时间轴（产品截图式卡片） */
function PlanContent({ data }) {
  if (!data?.title) return null
  return (
    <div className="space-y-5">
      {/* 标题区 */}
      <div>
        <h3 className="font-serif text-2xl text-stone-900 leading-tight">{data.title}</h3>
        {data.description && <p className="mt-1.5 text-sm text-stone-500 leading-relaxed">{data.description}</p>}
      </div>

      {/* 成本摘要 */}
      {data.total_cost != null && (
        <div className="flex items-center gap-3 rounded-2xl bg-orange-50 ring-1 ring-orange-100 px-5 py-4">
          <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white text-orange-600 ring-1 ring-orange-100">
            <Icon path={icons.wallet} size={20} />
          </span>
          <div>
            <p className="text-xs text-orange-700/70 font-medium">预计总花费</p>
            <p className="text-xl font-bold text-stone-900">¥{data.total_cost}</p>
          </div>
        </div>
      )}

      {/* 时间轴 */}
      {data.items?.length > 0 && (
        <div className="rounded-2xl bg-white ring-1 ring-stone-200/70 p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-5 text-stone-900">
            <Icon path={icons.calendar} size={18} className="text-orange-500" />
            <span className="font-semibold">行程安排</span>
          </div>
          <ol className="relative">
            {data.items.map((item, idx) => {
              const meta = metaFor(item.type)
              const last = idx === data.items.length - 1
              return (
                <li key={idx} className="relative flex gap-4 pb-5 last:pb-0">
                  {/* 连接线 */}
                  {!last && <span className="absolute left-[19px] top-11 bottom-0 w-px bg-stone-200" aria-hidden="true" />}
                  {/* 节点图标 */}
                  <span className={`relative z-10 inline-flex items-center justify-center w-10 h-10 shrink-0 rounded-xl ring-1 ${meta.tint}`}>
                    <Icon path={icons[meta.icon]} size={19} />
                  </span>
                  {/* 内容 */}
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-medium text-stone-900 truncate">{item.activity}</p>
                        {item.location_name && (
                          <p className="mt-0.5 inline-flex items-center gap-1 text-xs text-stone-400">
                            <Icon path={icons.pin} size={13} />
                            <span className="truncate">{item.location_name}</span>
                          </p>
                        )}
                      </div>
                      {item.cost > 0 && (
                        <span className="shrink-0 text-sm font-semibold text-stone-700">¥{item.cost}</span>
                      )}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-stone-400">
                      <span className="inline-flex items-center gap-1">
                        <Icon path={icons.clock} size={13} />{item.arrive_time} – {item.leave_time}
                      </span>
                      {item.stay_minute != null && <span>停留 {item.stay_minute} 分钟</span>}
                    </div>
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}

/** 方案卡片：JSON → 结构化，否则纯文本 */
function PlanCard({ planText, skeleton }) {
  const json = extractPlanJson(planText)
  return (
    <div className="animate-slideUp">
      {skeleton && (
        <div className="mb-4 inline-flex items-center gap-2 rounded-xl bg-stone-100 px-3 py-1.5 text-xs text-stone-500 ring-1 ring-stone-200/70">
          <Icon path={icons.spark} size={14} className="text-orange-500" />
          <span>命中骨架模板</span>
          <span className="font-semibold text-stone-700">{skeleton.name}</span>
        </div>
      )}
      {json ? (
        <PlanContent data={json} />
      ) : (
        <div className="rounded-2xl bg-white ring-1 ring-stone-200/70 p-6 shadow-sm">
          <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-stone-700">{planText}</div>
        </div>
      )}
    </div>
  )
}

/** 预订结果 */
function BookingResults({ results }) {
  if (!results.length) return null
  return (
    <div className="mt-6 animate-slideUp rounded-2xl bg-white ring-1 ring-stone-200/70 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4 text-stone-900">
        <Icon path={icons.check} size={18} className="text-orange-500" />
        <span className="font-semibold">预订结果</span>
      </div>
      <ul className="space-y-2">
        {results.map((r, i) => {
          const ok = r.status === 'success'
          return (
            <li key={i} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm ring-1 ${ok ? 'bg-emerald-50 text-emerald-800 ring-emerald-100' : 'bg-rose-50 text-rose-800 ring-rose-100'}`}>
              <Icon path={ok ? icons.check : icons.cross} size={16} strokeWidth={2.2} className="shrink-0" />
              <span className="flex-1 truncate">{r.message || r.location_name}</span>
              {r.order_id && <code className="shrink-0 rounded-md bg-white/70 px-2 py-0.5 text-xs font-mono text-stone-500">{r.order_id}</code>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════
// 主应用
// ════════════════════════════════════════════════════════════════

export default function App() {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState([])
  const [planText, setPlanText] = useState('')
  const [skeleton, setSkeleton] = useState(null)
  const [bookingResults, setBookingResults] = useState([])
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)
  const [autoExec, setAutoExec] = useState(false)
  // API Key 设置（仅存于内存，刷新即清空，不落盘）
  const [showSettings, setShowSettings] = useState(false)
  const [llmKey, setLlmKey] = useState('')
  const [amapKey, setAmapKey] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    let alive = true
    callHealth().then((h) => { if (alive) setHealth(h) })
    return () => { alive = false }
  }, [])

  const handleEvent = useCallback(({ event, data }) => {
    switch (event) {
      case 'step': setSteps((p) => [...p, data]); break
      case 'skeleton': setSkeleton(data); break
      case 'chunk': setPlanText((p) => p + data); break
      case 'booking': {
        const text = typeof data === 'string' ? data : String(data)
        setBookingResults((p) => [...p, { message: text, status: text.startsWith('✅') ? 'success' : 'failed' }])
        break
      }
      case 'done': setSteps((p) => [...p, '规划完成']); break
      case 'error': setError(typeof data === 'string' ? data : '规划过程中出现错误'); break
      default: break
    }
  }, [])

  const runPlan = useCallback(async (text) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    setLoading(true); setSteps([]); setPlanText(''); setSkeleton(null); setBookingResults([]); setError('')
    try {
      await callPlan(trimmed, { auto_execute: autoExec, onEvent: handleEvent, llmKey: llmKey.trim(), amapKey: amapKey.trim() })
    } catch (err) {
      setError('请求失败：' + (err?.message ?? '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [autoExec, handleEvent, loading, llmKey, amapKey])

  const handleSubmit = (e) => { e.preventDefault(); runPlan(message) }
  const canSubmit = !loading && message.trim().length > 0
  const online = health?.status === 'ok'

  return (
    <div className="min-h-screen bg-[#faf7f2] text-stone-900 antialiased">
      {/* 顶部细点阵 + 右上渐晕背景 */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 opacity-[0.5]" style={{ backgroundImage: 'radial-gradient(#d6d3d1 0.5px, transparent 0.5px)', backgroundSize: '22px 22px' }} />
        <div className="absolute -top-32 right-[-10%] h-[420px] w-[520px] rounded-full bg-gradient-to-br from-orange-200/40 via-rose-200/30 to-transparent blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-3xl px-5 py-10 md:py-14">
        {/* 顶栏 */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-9 h-9 rounded-xl bg-stone-900 text-white">
              <Icon path={icons.route} size={20} />
            </span>
            <span className="font-serif text-xl tracking-tight">走起</span>
          </div>
          <button
            type="button"
            onClick={() => setShowSettings((s) => !s)}
            className="inline-flex items-center gap-2 rounded-xl border-2 border-stone-900 bg-white px-3 py-1.5 text-sm font-semibold shadow-[2px_2px_0_0_#1c1917] hover:translate-y-px transition-transform"
          >
            <Icon path={icons.gear} size={16} />
            设置
            {(llmKey || amapKey) && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="已配置 Key" />}
          </button>
        </div>

        {/* 设置面板：API Key（仅存内存，刷新清空） */}
        {showSettings && (
          <div className="mb-8 animate-slideUp rounded-2xl border-2 border-stone-900 bg-white p-5 shadow-[4px_4px_0_0_#1c1917]">
            <div className="flex items-center gap-2 mb-1">
              <Icon path={icons.key} size={17} className="text-orange-500" />
              <span className="font-semibold">API Key 设置</span>
            </div>
            <p className="text-xs text-stone-400 mb-4 leading-relaxed">
              填入后本次会话生效（仅存于浏览器内存，刷新页面即清空，不会上传或保存）。留空则使用服务端默认配置或规则降级。
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-stone-500">LLM API Key（DeepSeek，用于 AI 规划）</label>
                <input
                  type="password"
                  value={llmKey}
                  onChange={(e) => setLlmKey(e.target.value)}
                  placeholder="sk-..."
                  className="mt-1 w-full rounded-xl bg-stone-50 px-3 py-2 text-sm text-stone-800 ring-1 ring-stone-200 placeholder-stone-300 focus:outline-none focus:ring-2 focus:ring-orange-400"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-stone-500">高德地图 API Key（Web 服务，用于真实地点）</label>
                <input
                  type="password"
                  value={amapKey}
                  onChange={(e) => setAmapKey(e.target.value)}
                  placeholder="留空则使用内置 mock 地点"
                  className="mt-1 w-full rounded-xl bg-stone-50 px-3 py-2 text-sm text-stone-800 ring-1 ring-stone-200 placeholder-stone-300 focus:outline-none focus:ring-2 focus:ring-orange-400"
                />
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <button
                type="button"
                onClick={() => { setLlmKey(''); setAmapKey('') }}
                className="text-xs text-stone-400 hover:text-stone-600"
              >
                清空
              </button>
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="rounded-xl bg-stone-900 px-4 py-1.5 text-sm font-semibold text-white hover:bg-stone-700 transition-colors"
              >
                完成
              </button>
            </div>
          </div>
        )}

        {/* Hero */}
        <header className="mb-9 animate-fadeIn">
          <h1 className="font-serif text-[2.75rem] leading-[1.05] md:text-6xl md:leading-[1.02] tracking-tight">
            一句话，<br />搞定一下午的<span className="relative whitespace-nowrap"> 行程
              <svg className="absolute -bottom-1 left-0 w-full" height="10" viewBox="0 0 200 10" preserveAspectRatio="none" aria-hidden="true">
                <path d="M2 7 C 50 2, 150 2, 198 6" stroke="#fb923c" strokeWidth="3" fill="none" strokeLinecap="round" />
              </svg>
            </span>。
          </h1>
          <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-stone-500">
            描述你的出行场景，「走起」自动解析意图、搜索附近候选、规划带时间轴的行程并可一键预订。
          </p>
        </header>

        {/* 产品卡片：输入区（TryPost 截图式） */}
        <form onSubmit={handleSubmit} className="relative animate-slideUp">
          {/* 角标（置于左上，避免与右上 LIVE 状态重叠） */}
          <div className="absolute -top-3 left-5 z-20">
            <TiltPill className="bg-amber-200 text-stone-900" rotate="-3deg">下午出行</TiltPill>
          </div>

          <div className="overflow-hidden rounded-[20px] border-2 border-stone-900 bg-white shadow-[5px_5px_0_0_#1c1917]">
            {/* 状态条 */}
            <div className="flex items-center justify-between border-b border-stone-200 bg-stone-50 px-4 py-2.5">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-rose-400" />
                <span className="w-3 h-3 rounded-full bg-amber-400" />
                <span className="w-3 h-3 rounded-full bg-emerald-400" />
              </div>
              <span className="text-[11px] font-semibold uppercase tracking-widest text-stone-400">走起 · 新规划</span>
              <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold ${online ? 'text-emerald-600' : 'text-stone-400'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-500 animate-pulse' : 'bg-stone-300'}`} />
                {online ? 'LIVE' : '离线'}
              </span>
            </div>

            {/* 编辑区 */}
            <div className="p-5">
              <label className="text-[11px] font-semibold uppercase tracking-widest text-stone-400">描述你的出行</label>
              <textarea
                className="mt-2 w-full resize-none bg-transparent text-[15px] leading-relaxed text-stone-800 placeholder-stone-300 focus:outline-none"
                rows={3}
                placeholder={PLACEHOLDER}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
              <div className="mt-3 flex items-center justify-between border-t border-stone-100 pt-3">
                <label className="inline-flex items-center gap-2 text-sm text-stone-500 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={autoExec}
                    onChange={(e) => setAutoExec(e.target.checked)}
                    className="w-4 h-4 rounded border-stone-300 text-orange-500 focus:ring-orange-400"
                  />
                  确认后自动下单
                  {health && (
                    <span className="ml-1 text-xs text-stone-400">· {health.llm_configured ? 'AI 规划' : '规则生成'}</span>
                  )}
                </label>
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
                >
                  {loading ? '规划中…' : '开始规划'}
                  <Icon path={loading ? icons.spark : icons.send} size={16} className={loading ? 'animate-spin' : ''} />
                </button>
              </div>
            </div>
          </div>
        </form>

        {/* 进度 */}
        {loading && <div className="mt-7"><StepTracker steps={steps} /></div>}

        {/* 错误 */}
        {error && (
          <div className="mt-6 flex items-start gap-2 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-100 animate-slideUp">
            <Icon path={icons.alert} size={17} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* 方案 */}
        {planText && <div className="mt-7"><PlanCard planText={planText} skeleton={skeleton} /></div>}

        {/* 预订结果 */}
        {bookingResults.length > 0 && <BookingResults results={bookingResults} />}

        {/* 示例 */}
        {!loading && !planText && (
          <div className="mt-10 animate-fadeIn">
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-stone-400">试试这样说</p>
            <div className="grid gap-3">
              {EXAMPLE_PROMPTS.map((ex, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setMessage(ex.text)}
                  className="group flex items-start gap-3 rounded-2xl bg-white px-4 py-3.5 text-left ring-1 ring-stone-200/70 transition-all hover:ring-orange-200 hover:shadow-sm"
                >
                  <span className="mt-0.5 inline-flex items-center justify-center w-8 h-8 shrink-0 rounded-lg bg-orange-50 text-orange-500 ring-1 ring-orange-100">
                    <Icon path={icons[ex.icon]} size={17} />
                  </span>
                  <span className="text-sm leading-relaxed text-stone-600 group-hover:text-stone-900">{ex.text}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  )
}
