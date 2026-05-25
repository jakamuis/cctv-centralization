import React from 'react'
import React, { Suspense } from 'react'

// We dynamically import the template app to avoid Vite/postcss processing
// of the template package at build time. The template contains its own
// build setup and Tailwind imports which can conflict with this app.
// We'll also lazy-load the template's styles where safe. The template's
// full index.css imports Tailwind directives which interfere with our build,
// so we only load sanitized CSS we've added to templateStyles.
const TemplateApp = React.lazy(() => import('../template/templatecctv/src/app/App'))

export default function TemplateDashboard() {
  return (
    <Suspense fallback={<div className="p-6">Loading dashboard template…</div>}>
      <TemplateApp />
    </Suspense>
  )
}
