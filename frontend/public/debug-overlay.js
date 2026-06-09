(function () {
  var STORAGE_KEY = 'app-debug-logs'
  var SNAPSHOT_KEY = 'app-debug-snapshot'
  var PANEL_KEY = 'app-debug-panel'
  var MAX_LOGS = 30
  var lastThemeIssue = ''
  var latestSnapshot = null

  function now() {
    return new Date().toLocaleString()
  }

  function text(value) {
    if (value == null) return ''
    if (value instanceof Error) return value.stack || value.message
    if (typeof value === 'string') return value
    try {
      var seen = []
      return JSON.stringify(value, function (_key, item) {
        if (item instanceof Error) return { name: item.name, message: item.message, stack: item.stack }
        if (item && typeof item === 'object') {
          if (seen.indexOf(item) >= 0) return '[Circular]'
          seen.push(item)
        }
        return item
      }, 2)
    } catch (err) {
      return String(value)
    }
  }

  function logs() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    } catch (err) {
      return []
    }
  }

  function saveLog(entry) {
    var list = logs()
    list.unshift(entry)
    list = list.slice(0, MAX_LOGS)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
    } catch (err) {
      // Ignore storage failures.
    }
    return list
  }

  function wantPanel() {
    try {
      sessionStorage.removeItem(PANEL_KEY)
    } catch (err) {
      // Ignore storage failures.
    }
    return false
  }

  function saveSnapshot(data) {
    latestSnapshot = data
    try {
      localStorage.setItem(SNAPSHOT_KEY, text(data))
    } catch (err) {
      // Ignore.
    }
  }

  function css(el, value) {
    el.style.cssText = value
  }

  function ensurePanel() {
    var panel = document.getElementById('app-debug-overlay')
    if (panel) {
      if (document.body && panel.parentNode !== document.body) document.body.appendChild(panel)
      return panel
    }

    panel = document.createElement('div')
    panel.id = 'app-debug-overlay'
    css(panel, [
      'position:fixed',
      'right:16px',
      'bottom:16px',
      'z-index:2147483647',
      'width:min(620px,calc(100vw - 32px))',
      'max-height:min(72vh,640px)',
      'overflow:auto',
      'padding:14px',
      'border:1px solid rgba(34,211,238,.38)',
      'border-radius:12px',
      'background:rgba(2,6,23,.96)',
      'color:#f8fafc',
      'box-shadow:0 24px 60px rgba(0,0,0,.4)',
      'font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace',
      'white-space:pre-wrap',
    ].join(';'))

    ;(document.body || document.documentElement).appendChild(panel)
    return panel
  }

  function makeButton(label, handler) {
    var button = document.createElement('button')
    button.type = 'button'
    button.textContent = label
    css(button, [
      'border:1px solid rgba(255,255,255,.16)',
      'background:rgba(255,255,255,.08)',
      'color:#fff',
      'border-radius:8px',
      'padding:5px 8px',
      'cursor:pointer',
      'font-size:12px',
    ].join(';'))
    button.onclick = handler
    return button
  }

  function renderPanel(title, detail) {
    var panel = ensurePanel()
    var recent = logs()
      .slice(0, 6)
      .map(function (item, index) {
        return [
          '#' + (index + 1) + ' [' + item.time + '] ' + item.type,
          item.message,
          item.extra ? 'extra: ' + text(item.extra) : '',
        ].filter(Boolean).join('\n')
      })
      .join('\n\n')

    panel.innerHTML = ''

    var header = document.createElement('div')
    css(header, 'display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;font-family:system-ui,-apple-system,Segoe UI,sans-serif')

    var heading = document.createElement('strong')
    heading.textContent = title || 'Frontend debug'
    css(heading, 'font-size:15px;color:#a5f3fc')

    var actions = document.createElement('div')
    css(actions, 'display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end')
    actions.appendChild(makeButton('Copy snapshot', function () {
      if (navigator.clipboard) navigator.clipboard.writeText(text(latestSnapshot || snapshot('manual-copy'))).catch(function () {})
    }))
    actions.appendChild(makeButton('Copy', function () {
      if (navigator.clipboard) navigator.clipboard.writeText(panel.innerText || '').catch(function () {})
    }))
    actions.appendChild(makeButton('Clear', function () {
      try {
        localStorage.removeItem(STORAGE_KEY)
        localStorage.removeItem(SNAPSHOT_KEY)
      } catch (err) {
        // Ignore.
      }
      lastThemeIssue = ''
      renderPanel('Frontend debug', 'Logs cleared.')
    }))
    actions.appendChild(makeButton('Light + reload', function () {
      localStorage.setItem('app-theme', 'light')
      try { sessionStorage.setItem(PANEL_KEY, '1') } catch (err) {}
      location.href = location.pathname + '?debug-theme=light&debug-panel=1'
    }))
    actions.appendChild(makeButton('Close', function () {
      panel.remove()
    }))

    header.appendChild(heading)
    header.appendChild(actions)
    panel.appendChild(header)

    if (latestSnapshot) {
      var snapBox = document.createElement('div')
      css(snapBox, [
        'margin:0 0 12px',
        'padding:10px',
        'border:1px solid rgba(34,211,238,.35)',
        'border-radius:10px',
        'background:rgba(8,47,73,.45)',
        'color:#e0f2fe',
      ].join(';'))
      var snapTitle = document.createElement('div')
      snapTitle.textContent = 'CURRENT SNAPSHOT'
      css(snapTitle, 'font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-weight:800;font-size:13px;color:#67e8f9;margin-bottom:6px;letter-spacing:.04em')
      var snapContent = document.createElement('pre')
      snapContent.textContent = text(latestSnapshot)
      css(snapContent, 'margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace')
      snapBox.appendChild(snapTitle)
      snapBox.appendChild(snapContent)
      panel.appendChild(snapBox)
    }

    var body = document.createElement('div')
    body.textContent = [detail || '', recent ? '\nRecent logs:\n' + recent : '\nNo logs.'].join('\n')
    panel.appendChild(body)
    panel.scrollTop = 0
  }

  function report(type, message, extra) {
    var entry = {
      time: now(),
      type: type || 'unknown',
      message: text(message),
      extra: extra || null,
      href: location.href,
      userAgent: navigator.userAgent,
    }
    saveLog(entry)
    renderPanel('Frontend error', entry.message + (entry.extra ? '\n\n' + text(entry.extra) : ''))
  }

  function rgb(value) {
    var match = String(value || '').match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
    if (!match) return null
    return { r: Number(match[1]), g: Number(match[2]), b: Number(match[3]) }
  }

  function isLight(value) {
    var c = rgb(value)
    if (!c) return false
    return (c.r * 299 + c.g * 587 + c.b * 114) / 1000 > 225
  }

  function solidBg(el) {
    var node = el
    while (node && node !== document.documentElement) {
      var bg = getComputedStyle(node).backgroundColor
      if (bg && bg !== 'transparent' && !/rgba\(\s*0,\s*0,\s*0,\s*0\s*\)/.test(bg)) return bg
      node = node.parentElement
    }
    return getComputedStyle(document.body || document.documentElement).backgroundColor
  }

  function setDomTheme(theme) {
    var isDark = theme === 'dark'
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    document.documentElement.classList.toggle('theme-dark', isDark)
    document.documentElement.classList.toggle('theme-light', !isDark)
    document.documentElement.classList.toggle('dark', isDark)
    if (document.body) {
      document.body.classList.toggle('theme-dark', isDark)
      document.body.classList.toggle('theme-light', !isDark)
      document.body.classList.toggle('dark', isDark)
    }
  }

  function applyThemeFromUrl() {
    var params = new URLSearchParams(location.search)
    var requested = params.get('debug-theme')
    if (requested === 'dark') {
      params.set('debug-theme', 'light')
      history.replaceState(null, '', location.pathname + '?' + params.toString())
    }
    localStorage.setItem('app-theme', 'light')
    var theme = 'light'
    setDomTheme(theme)
    return theme
  }

  function describeRect(rect) {
    return {
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      x: Math.round(rect.x),
      y: Math.round(rect.y),
    }
  }

  function describeStyle(el) {
    if (!el) return null
    var style = getComputedStyle(el)
    return {
      display: style.display,
      position: style.position,
      width: style.width,
      height: style.height,
      minWidth: style.minWidth,
      minHeight: style.minHeight,
      overflow: style.overflow,
      opacity: style.opacity,
      visibility: style.visibility,
      transform: style.transform,
    }
  }

  function checkDarkRender(reason) {
    var html = document.documentElement
    var body = document.body
    var app = document.getElementById('app')
    var theme = localStorage.getItem('app-theme')
    var isDark = theme === 'dark' || html.classList.contains('theme-dark') || (body && body.classList.contains('theme-dark'))
    if (!isDark || !app || !body) return

    var rect = app.getBoundingClientRect()
    var center = document.elementFromPoint(Math.floor(window.innerWidth / 2), Math.floor(window.innerHeight / 2))
    var centerBg = center ? solidBg(center) : ''
    var details = {
      reason: reason,
      theme: theme,
      htmlClass: html.className,
      bodyClass: body.className,
      appClass: app.className,
      appChildren: app.children.length,
      appTextLength: (app.innerText || app.textContent || '').trim().length,
      appRect: describeRect(rect),
      htmlRect: describeRect(html.getBoundingClientRect()),
      bodyRect: describeRect(body.getBoundingClientRect()),
      appStyle: describeStyle(app),
      htmlBg: getComputedStyle(html).backgroundColor,
      bodyBg: getComputedStyle(body).backgroundColor,
      appBg: getComputedStyle(app).backgroundColor,
      centerTag: center ? center.tagName + (center.className ? '.' + String(center.className).replace(/\s+/g, '.') : '') : '',
      centerBg: centerBg,
    }

    var issue = ''
    if (reason === 'DOMContentLoaded+300ms' && rect.width < 20 && details.appTextLength > 0) {
      issue = ''
    } else if (rect.width < 20 || rect.height < 20 || app.children.length === 0) {
      issue = '#app is not visibly rendered in dark mode.'
    } else if (isLight(centerBg)) {
      issue = 'Dark mode is enabled, but the center element still has a light background.'
    }

    if (issue && issue !== lastThemeIssue) {
      lastThemeIssue = issue
      saveLog({ time: now(), type: 'theme-render-check', message: issue, extra: details, href: location.href, userAgent: navigator.userAgent })
      renderPanel('Dark render issue', issue + '\n\n' + text(details))
    }
  }

  function snapshot(reason) {
    var html = document.documentElement
    var body = document.body
    var app = document.getElementById('app')
    var active = document.activeElement
    var center = document.elementFromPoint(Math.floor(window.innerWidth / 2), Math.floor(window.innerHeight / 2))
    var rect = app ? describeRect(app.getBoundingClientRect()) : null
    return {
      reason: reason,
      href: location.href,
      theme: localStorage.getItem('app-theme'),
      htmlClass: html ? html.className : '',
      bodyClass: body ? body.className : '',
      appChildren: app ? app.children.length : null,
      appTextLength: app ? (app.innerText || app.textContent || '').trim().length : null,
      appRect: rect,
      htmlRect: html ? describeRect(html.getBoundingClientRect()) : null,
      bodyRect: body ? describeRect(body.getBoundingClientRect()) : null,
      appStyle: app ? describeStyle(app) : null,
      appBg: app ? getComputedStyle(app).backgroundColor : '',
      activeTag: active ? active.tagName + (active.className ? '.' + String(active.className).replace(/\s+/g, '.') : '') : '',
      centerTag: center ? center.tagName + (center.className ? '.' + String(center.className).replace(/\s+/g, '.') : '') : '',
      centerBg: center ? solidBg(center) : '',
      bodyTextSample: body ? (body.innerText || body.textContent || '').trim().slice(0, 240) : '',
    }
  }

  window.__APP_DEBUG_REPORT__ = report
  window.__APP_DEBUG_CHECK__ = checkDarkRender

  window.addEventListener('error', function (event) {
    report('window.error', event.error || event.message, { filename: event.filename, lineno: event.lineno, colno: event.colno })
  })

  window.addEventListener('unhandledrejection', function (event) {
    report('unhandledrejection', event.reason)
  })

  if (wantPanel()) {
    saveSnapshot({ reason: 'before-dom-ready', href: location.href, theme: localStorage.getItem('app-theme') })
    renderPanel('Frontend debug', 'Debug script loaded before Vue. If the app is blank, this panel should remain visible.')
  }

  applyThemeFromUrl()

  document.addEventListener('DOMContentLoaded', function () {
    applyThemeFromUrl()
    if (wantPanel()) {
      saveSnapshot(snapshot('DOMContentLoaded'))
      renderPanel('Frontend debug', 'Snapshot is shown in the CURRENT SNAPSHOT box above.')
      setInterval(function () {
        saveSnapshot(snapshot('interval'))
        renderPanel('Frontend debug', 'Snapshot is shown in the CURRENT SNAPSHOT box above.')
      }, 2000)
    }
    setTimeout(function () { checkDarkRender('DOMContentLoaded+300ms') }, 300)
    setTimeout(function () { checkDarkRender('DOMContentLoaded+1500ms') }, 1500)
    var observer = new MutationObserver(function () {
      setTimeout(function () { checkDarkRender('theme-class-mutation') }, 120)
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] })
    if (document.body) observer.observe(document.body, { attributes: true, attributeFilter: ['class'] })
  })

  window.addEventListener('beforeunload', function () {
    try {
      saveSnapshot(snapshot('beforeunload'))
    } catch (err) {
      // Ignore.
    }
  })
})()
