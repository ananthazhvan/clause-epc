/* CLAUSE icon set - one intentional mark per surface.
   Rules: 24-grid, stroke 1.6, round caps, no fills, max 3 paths.
   Drawn to read at 18px on paper. */
"use strict";
function _svg(inner) {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + inner + "</svg>";
}
const ICONS = {
  // the ledger core with its five sources - the hub is the thesis
  hub: _svg('<circle cx="12" cy="12" r="2.2"/><circle cx="12" cy="4.6" r="1.3"/><circle cx="19.1" cy="9.7" r="1.3"/><circle cx="16.4" cy="18.1" r="1.3"/><circle cx="7.6" cy="18.1" r="1.3"/><circle cx="4.9" cy="9.7" r="1.3"/><path d="M12 9.8V6M13.9 10.8l3.9-2M13.4 13.9l2.3 3.1M10.6 13.9l-2.3 3.1M10.1 10.8l-3.9-2"/>'),
  // four panes: everything visible from one desk
  overview: _svg('<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>'),
  clock: _svg('<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.4 2"/>'),
  // three bars, longest first: a queue ordered by severity
  queue: _svg('<path d="M5 7h14M5 12h10M5 17h6"/>'),
  // spec beside submittal - the two-column comparison
  review: _svg('<rect x="3.5" y="5" width="7.5" height="14" rx="1"/><rect x="13" y="5" width="7.5" height="14" rx="1"/><path d="M6 9h2.5M6 12h2.5M15.5 9h2.5M15.5 12h2.5"/>'),
  graph: _svg('<circle cx="6" cy="17" r="2.1"/><circle cx="12" cy="6.6" r="2.1"/><circle cx="18" cy="17" r="2.1"/><path d="M7.1 15.2l3.8-6.7M13.1 8.5l3.8 6.7M8.2 17h7.6"/>'),
  lint: _svg('<path d="M12 4.5l8 14H4z"/><path d="M12 10.5v3.6M12 16.6v.4"/>'),
  external: _svg('<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c3.2 2.7 3.2 14.3 0 17-3.2-2.7-3.2-14.3 0-17z"/>'),
  // one change, expanding rings of consequence
  blast: _svg('<circle cx="6.5" cy="17.5" r="1.6"/><path d="M11.5 17.5A5 5 0 0 0 6.5 12.5"/><path d="M15.5 17.5A9 9 0 0 0 6.5 8.5"/><path d="M19.5 17.5A13 13 0 0 0 6.5 4.5"/>'),
  // a gauge: how much headroom is left
  margins: _svg('<path d="M4.5 16a7.5 7.5 0 0 1 15 0"/><path d="M12 16l4-4"/><path d="M4.5 19.5h15"/>'),
  vendors: _svg('<path d="M12 3.5l7 2.5v5.4c0 4.5-3 7.6-7 9.1-4-1.5-7-4.6-7-9.1V6z"/><path d="M9 11.8l2.2 2.2 3.8-4.2"/>'),
  paperwork: _svg('<path d="M7 3.5h7l4 4V20.5H7z"/><path d="M14 3.5V8h4M9.5 12h5M9.5 15.5h5"/>'),
  cx: _svg('<rect x="5.5" y="4.5" width="13" height="16" rx="1.5"/><rect x="9" y="3" width="6" height="3" rx="1"/><path d="M9 13.5l2 2 4-4.5"/>'),
  ncr: _svg('<path d="M6 21V4"/><path d="M6 5h11l-2.5 3.5L17 12H6"/>'),
  settings: _svg('<path d="M5 8h14M5 16h14"/><circle cx="10" cy="8" r="2"/><circle cx="15" cy="16" r="2"/>'),
  upload: _svg('<path d="M12 15V5.5M8.5 8.5L12 5l3.5 3.5"/><path d="M5 15v3.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V15"/>'),
  // the spine: one entity, its connections fanned out
  link: _svg('<circle cx="6.5" cy="12" r="2"/><circle cx="17.5" cy="6.5" r="2"/><circle cx="17.5" cy="17.5" r="2"/><path d="M8.4 11.1l7.2-3.7M8.4 12.9l7.2 3.7"/>'),
  x: _svg('<path d="M6 6l12 12M18 6L6 18"/>'),
  doc: _svg('<path d="M6.5 3.5h8l3 3v14h-11z"/><path d="M14.5 3.5V7h3"/>'),
  chip: _svg('<rect x="6" y="6" width="12" height="12" rx="1.5"/><path d="M9.5 2.5v3M14.5 2.5v3M9.5 18.5v3M14.5 18.5v3M2.5 9.5h3M2.5 14.5h3M18.5 9.5h3M18.5 14.5h3"/>'),
  facility: _svg('<path d="M3.5 20.5h17"/><rect x="5" y="13" width="3.6" height="7.5"/><rect x="10.2" y="9" width="3.6" height="11.5"/><rect x="15.4" y="5" width="3.6" height="15.5"/>'),
  copilot: _svg('<path d="M4.5 5h15v10.5H10l-4.5 4v-4h-1z"/><path d="M8.5 9h7M8.5 11.5h4.5"/>'),
};
