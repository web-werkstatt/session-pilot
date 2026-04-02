/* Copilot Landing Page */

document.addEventListener("DOMContentLoaded", loadCopilotStats);

async function loadCopilotStats() {
    try {
        const data = await api.get("/api/copilot/stats");
        renderRecentProjects(data.recent_projects || []);
        renderActivePlans(data.active_plans || []);
    } catch (e) {
        console.error("Copilot stats error:", e);
    }
}

function renderRecentProjects(projects) {
    const container = document.getElementById("recentProjectsList");
    if (!projects.length) {
        container.innerHTML = '<div class="kpi-detail" style="opacity:0.5;">Noch keine Projekte mit Plans.</div>';
        return;
    }

    container.innerHTML = projects.map(p => {
        const name = escapeHtml(p.project_name);
        const ago = p.last_activity ? formatTimeAgo(p.last_activity) : "";
        const pills = [
            p.active_plans ? `<span class="stat-pill stat-pill-active">${p.active_plans} active</span>` : "",
            p.done_plans ? `<span class="stat-pill stat-pill-done">${p.done_plans} done</span>` : "",
            `<span class="stat-pill stat-pill-total">${p.plan_count}</span>`,
        ].filter(Boolean).join("");
        return `<div class="recent-project-item" onclick="filterPlans('${escapeHtml(p.project_name)}')">
            <span class="rp-name">${name}</span>
            <span class="rp-meta">${ago}</span>
            <span class="rp-pills">${pills}</span>
        </div>`;
    }).join("");
}

function renderActivePlans(plans) {
    const container = document.getElementById("activePlansList");
    const empty = document.getElementById("emptyState");

    if (!plans.length) {
        container.style.display = "none";
        empty.style.display = "";
        return;
    }

    container.style.display = "";
    empty.style.display = "none";

    container.innerHTML = plans.map(p => {
        const title = escapeHtml(p.title || "Untitled");
        const project = p.project_name ? escapeHtml(p.project_name) : "—";
        const ago = p.updated_at ? formatTimeAgo(p.updated_at) : "";
        const statusCls = `status-${p.status}`;
        const badgeCls = `badge-${p.status}`;
        return `<a href="/copilot?plan_id=${p.id}" class="plan-card-link">
            <div class="plan-card ${statusCls}">
                <div class="plan-card-top">
                    <span class="plan-project"><i data-lucide="folder" class="icon icon-xs"></i> ${project}</span>
                    <span class="plan-date">${ago}</span>
                </div>
                <div class="plan-card-title">${title}</div>
                <div class="plan-card-footer">
                    <span class="badge-status ${badgeCls}">${p.status}</span>
                    <span class="plan-card-copilot-btn"><i data-lucide="bot" class="icon icon-xs"></i> Board</span>
                </div>
            </div>
        </a>`;
    }).join("");

    if (typeof lucide !== "undefined") lucide.createIcons();
}

function filterPlans(projectName) {
    // Scroll zu Plans und highlight matching
    const cards = document.querySelectorAll("#activePlansList .plan-card-link");
    let found = false;
    cards.forEach(c => {
        const proj = c.querySelector(".plan-project")?.textContent?.trim() || "";
        if (proj.includes(projectName)) {
            c.style.display = "";
            if (!found) {
                c.scrollIntoView({ behavior: "smooth", block: "center" });
                found = true;
            }
        } else {
            c.style.display = "none";
        }
    });

    // Show reset button
    if (!document.getElementById("resetFilter")) {
        const section = document.querySelector("#activePlansList").parentElement;
        const title = section.querySelector(".copilot-section-title");
        const btn = document.createElement("button");
        btn.id = "resetFilter";
        btn.className = "btn btn-secondary btn-sm";
        btn.style.marginLeft = "auto";
        btn.textContent = "Alle zeigen";
        btn.onclick = () => {
            cards.forEach(c => c.style.display = "");
            btn.remove();
        };
        title.appendChild(btn);
    }
}
