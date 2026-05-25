# Migration Plan: Integrate templatecctv into frontend

Summary
-------
This document describes the incremental plan to replace the current dashboard (AppLayout)
with the provided template located at frontend/src/template/templatecctv.

Goals
- Replace dashboard with template incrementally and safely
- Reuse existing components and logic where possible
- Avoid importing the template's Tailwind/PostCSS entrypoints directly

Phases
------

1) Safe CSS extraction (completed partly)
   - Extract plain CSS and variables from the template into frontend/src/templateStyles/
   - Files created: fonts-import.css, theme-sanitized.css, sidebar-sanitized.css,
     button-sanitized.css
   - Import only these sanitized files from frontend/src/App.jsx

2) Lazy mount the template App (completed)
   - Use React.lazy to mount the template App only when dashboard route is active
   - Keeps Vite/PostCSS from processing template Tailwind directives at build time

3) Component adapter layer (next)
   - Create wrapper/adapters for template components that need our data:
     - TemplateSidebarWrapper -> adapt our sites/branches/cameras to template Sidebar props
     - TemplateBrandWrapper -> map branding and user/logout actions
   - Implement them under frontend/src/components/ as small adapters

4) Incremental component replacement (recommended order)
   - Sidebar (replace Sidebar.jsx with TemplateSidebarWrapper) — lowest-impact UI change
   - SitesExplorer -> map to template explorer layout/styling
   - CameraDetailPanel -> adopt template card styles
   - PreviewPanel -> migrate grid styles, keep playback components
   - Playback pages/components: keep logic, apply template styles

5) CSS tokens and Tailwind reconciliation
   - Keep using sanitized CSS variables for colors/spacings
   - If necessary, add missing variables in theme-sanitized.css
   - Avoid merging full template tailwind.config unless willing to refactor build

6) Testing
   - Start dev server and navigate: login -> dashboard -> discovery -> playback
   - Verify layout, sidebar interactions, playback stability
   - Fix style conflicts and missing variables

7) Cleanup and finalize
   - Remove unused template imports and temporary wrapper code
   - Consolidate template styles into a smaller set
   - Document which template components were used and any deviations

Rollback plan
-------------
- Because changes are incremental and isolated, rollback is simple:
  - Revert the commit that imports TemplateDashboard and sanitized CSS to restore previous App.jsx
  - Restore Sidebar and other components if replaced

Files to create next (implementation tasks)
- frontend/src/components/TemplateSidebarWrapper.jsx
- frontend/src/components/TemplateBrandWrapper.jsx
- frontend/src/templateStyles/badge-sanitized.css
- frontend/src/templateStyles/card-sanitized.css

Testing commands
- From project root: cd frontend && npm run dev

Notes
- Do NOT import template/src/styles/index.css, globals.css or tailwind.css directly because they
  contain @import directives that reference node modules and Tailwind directives which break Vite/PostCSS.

Contact
- If you want me to proceed, tell me which component to implement first (Sidebar recommended).
