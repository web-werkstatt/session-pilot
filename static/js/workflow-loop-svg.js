function renderWorkflowLoopSvg(container, data, onStepClick) {
    if (!container) return;

    var steps = Array.isArray(data && data.steps) ? data.steps : [];
    var size = 420;
    var center = 210;
    var radius = 136;
    var nodeRadius = 34;
    var startAngle = -90;

    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + size + ' ' + size);
    svg.setAttribute('class', 'workflow-loop-svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Workflow Loop');

    var defs = document.createElementNS(ns, 'defs');
    var marker = document.createElementNS(ns, 'marker');
    marker.setAttribute('id', 'workflowLoopArrow');
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '10');
    marker.setAttribute('refX', '7');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    var arrow = document.createElementNS(ns, 'path');
    arrow.setAttribute('d', 'M0,0 L0,6 L8,3 z');
    arrow.setAttribute('fill', 'currentColor');
    marker.appendChild(arrow);
    defs.appendChild(marker);
    svg.appendChild(defs);

    var positions = steps.map(function(step, index) {
        var angle = (startAngle + (360 / Math.max(steps.length, 1)) * index) * (Math.PI / 180);
        return {
            x: center + Math.cos(angle) * radius,
            y: center + Math.sin(angle) * radius
        };
    });

    steps.forEach(function(step, index) {
        var current = positions[index];
        var next = positions[(index + 1) % positions.length];
        var line = document.createElementNS(ns, 'line');
        line.setAttribute('x1', current.x);
        line.setAttribute('y1', current.y);
        line.setAttribute('x2', next.x);
        line.setAttribute('y2', next.y);
        line.setAttribute('class', 'workflow-loop-connector step-status-' + escapeHtml(step.status || 'pending'));
        line.setAttribute('marker-end', 'url(#workflowLoopArrow)');
        svg.appendChild(line);
    });

    var centerRing = document.createElementNS(ns, 'circle');
    centerRing.setAttribute('cx', center);
    centerRing.setAttribute('cy', center);
    centerRing.setAttribute('r', '74');
    centerRing.setAttribute('class', 'workflow-loop-center-ring');
    svg.appendChild(centerRing);

    var centerLabel = document.createElementNS(ns, 'text');
    centerLabel.setAttribute('x', center);
    centerLabel.setAttribute('y', center - 8);
    centerLabel.setAttribute('text-anchor', 'middle');
    centerLabel.setAttribute('class', 'workflow-loop-center-label');
    centerLabel.textContent = workflowLoopCurrentStepLabel(data);
    svg.appendChild(centerLabel);

    steps.forEach(function(step, index) {
        var point = positions[index];
        var group = document.createElementNS(ns, 'g');
        group.setAttribute('class', 'workflow-loop-node');
        group.setAttribute('tabindex', '0');
        group.setAttribute('role', 'button');
        group.setAttribute('aria-label', step.label + ': ' + (step.cta_label || ''));

        var title = document.createElementNS(ns, 'title');
        title.textContent = step.label + ' · ' + (step.cta_label || '');
        group.appendChild(title);

        var desc = document.createElementNS(ns, 'desc');
        desc.textContent = workflowLoopNodeDescription(step);
        group.appendChild(desc);

        var circle = document.createElementNS(ns, 'circle');
        circle.setAttribute('cx', point.x);
        circle.setAttribute('cy', point.y);
        circle.setAttribute('r', nodeRadius);
        circle.setAttribute('class', 'workflow-loop-node-circle step-status-' + escapeHtml(step.status || 'pending'));
        group.appendChild(circle);

        var number = document.createElementNS(ns, 'text');
        number.setAttribute('x', point.x);
        number.setAttribute('y', point.y + 4);
        number.setAttribute('text-anchor', 'middle');
        number.setAttribute('class', 'workflow-loop-node-number');
        number.textContent = String(step.number || index + 1);
        group.appendChild(number);

        var label = document.createElementNS(ns, 'text');
        label.setAttribute('x', point.x);
        label.setAttribute('y', point.y + nodeRadius + 18);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('class', 'workflow-loop-node-label');
        label.textContent = step.label;
        group.appendChild(label);

        group.addEventListener('click', function() {
            if (typeof onStepClick === 'function') onStepClick(step);
        });
        group.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                if (typeof onStepClick === 'function') onStepClick(step);
            }
        });

        svg.appendChild(group);
    });

    container.innerHTML = '';
    container.appendChild(svg);
}

function workflowLoopCurrentStepLabel(data) {
    var current = String((data && data.current_step) || '');
    // Bevorzugt das Label direkt aus workflow.steps (Single Source of Truth),
    // sonst Fallback-Map fuer Legacy-Aufrufer.
    var steps = (data && data.steps) || [];
    for (var i = 0; i < steps.length; i++) {
        if (steps[i].id === current) return steps[i].label || 'Workflow';
    }
    var fallback = {
        gate_prompt: 'Prompt',
        gate_checks: 'Checks',
        ready: 'Bereit',
        running: 'Session',
        close: 'Abschluss'
    };
    return fallback[current] || 'Workflow';
}

function workflowLoopNodeDescription(step) {
    var statusMap = {
        done: 'erledigt',
        active: 'aktiv',
        pending: 'ausstehend',
        attention: 'braucht Aufmerksamkeit',
        blocked: 'blockiert'
    };
    return (step.label || 'Schritt') + ', Status: ' + (statusMap[step.status] || step.status || 'ausstehend') + '.';
}
