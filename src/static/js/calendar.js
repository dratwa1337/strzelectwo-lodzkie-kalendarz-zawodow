// ── State ──
let calendar;

// ── Multi-select helpers ──
const multiSelects = document.querySelectorAll('.multi-select');

function getSelectedValues(filterName) {
    const el = document.querySelector(`.multi-select[data-filter="${filterName}"]`);
    if (!el) return [];
    return Array.from(el.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
}

function getFilterParams() {
    const params = new URLSearchParams();
    for (const name of ['name', 'organizer', 'location', 'discipline', 'weapon']) {
        for (const val of getSelectedValues(name)) {
            params.append(name, val);
        }
    }
    return params;
}

function updateToggleLabel(ms) {
    const checked = ms.querySelectorAll('input[type="checkbox"]:checked');
    const toggle = ms.querySelector('.ms-toggle');
    const badge = ms.querySelector('.ms-badge');

    const filterName = ms.dataset.filter;
    const defaults = {
        name: 'Wszystkie',
        organizer: 'Wszyscy',
        location: 'Wszystkie',
        discipline: 'Wszystkie',
        weapon: 'Wszystkie',
    };

    if (checked.length === 0) {
        toggle.firstChild.textContent = defaults[filterName] + ' ';
        badge.textContent = '';
        badge.classList.remove('visible');
    } else if (checked.length === 1) {
        toggle.firstChild.textContent = checked[0].parentElement.textContent.trim() + ' ';
        badge.textContent = '';
        badge.classList.remove('visible');
    } else {
        toggle.firstChild.textContent = checked.length + ' wybrano ';
        badge.textContent = checked.length;
        badge.classList.add('visible');
    }
}

// ── Refresh calendar events ──
function refetchEvents() {
    calendar.refetchEvents();
}

function updateStats(events) {
    const el = document.getElementById('stats');
    el.innerHTML = `Wyświetlanych zawodów: <strong>${events.length}</strong>`;
}

// ── HTML escaping ──
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function resetFilters() {
    multiSelects.forEach(ms => {
        ms.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        updateToggleLabel(ms);
    });
    refetchEvents();
}

// ── Event popover ──
function showPopover(info) {
    const ev = info.event;
    const props = ev.extendedProps;

    document.getElementById('popover-title').textContent = ev.title;

    const startStr = ev.start ? ev.start.toLocaleDateString('pl-PL', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    }) : '';
    const endStr = ev.end ? ev.end.toLocaleDateString('pl-PL', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    }) : '';

    let dateDisplay = startStr;
    if (endStr && endStr !== startStr) {
        dateDisplay = `${startStr} — ${endStr}`;
    }

    let html = '';
    if (props.name && props.name !== 'zawody klubowe') html += popoverRow('Zawody', props.name);
    html += popoverRow('Data', dateDisplay);
    if (props.location) html += popoverRow('Miejsce', props.location);
    if (props.organizer) html += popoverRow('Organizator', props.organizer);
    if (props.disciplines) html += popoverRow('Dyscypliny', props.disciplines);
    if (props.weaponTypes) html += popoverRow('Broń', props.weaponTypes);
    if (props.result) html += popoverRow('Wynik', props.result === 'w' ? '✅ wyniki' : props.result);

    document.getElementById('popover-body').innerHTML = html;

    // Position near the clicked element
    const popover = document.getElementById('popover');
    const rect = info.el.getBoundingClientRect();
    let top = rect.bottom + 8;
    let left = rect.left;

    // Keep within viewport
    if (top + 300 > window.innerHeight) top = rect.top - 300;
    if (left + 320 > window.innerWidth) left = window.innerWidth - 340;
    if (left < 10) left = 10;

    popover.style.top = top + 'px';
    popover.style.left = left + 'px';
    popover.style.display = 'block';
    document.getElementById('popover-overlay').style.display = 'block';
}

function popoverRow(label, value) {
    return `<div class="popover-row"><span class="label">${escapeHtml(label)}</span><span class="value">${escapeHtml(value)}</span></div>`;
}

function closePopover() {
    document.getElementById('popover').style.display = 'none';
    document.getElementById('popover-overlay').style.display = 'none';
}

// ── Init FullCalendar ──
document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        locale: 'pl',
        initialView: 'dayGridMonth',
        initialDate: '2026-03-01',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth',
        },
        buttonText: {
            today: 'Dziś',
            month: 'Miesiąc',
            list: 'Lista',
        },
        height: 'auto',
        events: function(info, successCallback, failureCallback) {
            fetch('/api/events?' + getFilterParams().toString())
                .then(resp => resp.json())
                .then(data => successCallback(data))
                .catch(err => failureCallback(err));
        },
        eventsSet: function(events) {
            updateStats(events);
        },
        eventClick: showPopover,
        eventDidMount: function(info) {
            info.el.style.cursor = 'pointer';
        },
    });
    calendar.render();

    // Multi-select: toggle dropdowns
    multiSelects.forEach(ms => {
        const toggle = ms.querySelector('.ms-toggle');
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            // Close all others
            multiSelects.forEach(other => {
                if (other !== ms) other.classList.remove('open');
            });
            ms.classList.toggle('open');
        });

        // Checkbox change → update label + refetch
        ms.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', () => {
                updateToggleLabel(ms);
                refetchEvents();
            });
        });
    });

    // Close dropdowns on outside click
    document.addEventListener('click', () => {
        multiSelects.forEach(ms => ms.classList.remove('open'));
    });

    // Prevent dropdown panel clicks from closing
    document.querySelectorAll('.ms-dropdown').forEach(dd => {
        dd.addEventListener('click', e => e.stopPropagation());
    });
});
