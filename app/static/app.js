const state = {
  comparison: null,
  vision: null,
  timelineHandle: null,
  timelineIndex: 0,
};

const PHASE_TO_LANES = {
  north_south: ["north", "south"],
  east_west: ["east", "west"],
};

const elements = {
  presetSelect: document.getElementById("presetSelect"),
  runScenarioBtn: document.getElementById("runScenarioBtn"),
  sampleVisionBtn: document.getElementById("sampleVisionBtn"),
  uploadVisionBtn: document.getElementById("uploadVisionBtn"),
  videoUpload: document.getElementById("videoUpload"),
  healthStatus: document.getElementById("healthStatus"),
  scenarioName: document.getElementById("scenarioName"),
  statusMessage: document.getElementById("statusMessage"),
  waitReduction: document.getElementById("waitReduction"),
  throughputImprovement: document.getElementById("throughputImprovement"),
  queueReduction: document.getElementById("queueReduction"),
  co2Reduction: document.getElementById("co2Reduction"),
  waitDetail: document.getElementById("waitDetail"),
  throughputDetail: document.getElementById("throughputDetail"),
  queueDetail: document.getElementById("queueDetail"),
  co2Detail: document.getElementById("co2Detail"),
  decisionList: document.getElementById("decisionList"),
  visionSummary: document.getElementById("visionSummary"),
  junctionCanvas: document.getElementById("junctionCanvas"),
  comparisonChart: document.getElementById("comparisonChart"),
  queueChart: document.getElementById("queueChart"),
  visionChart: document.getElementById("visionChart"),
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json();
}

function setStatus(message) {
  elements.statusMessage.textContent = message;
}

async function checkHealth() {
  try {
    const data = await fetchJson("/api/health");
    elements.healthStatus.textContent = `${data.status} (${data.app})`;
  } catch (error) {
    elements.healthStatus.textContent = "Offline";
    setStatus(`Health check failed: ${error.message}`);
  }
}

async function loadPresets() {
  const presets = await fetchJson("/api/simulate/presets");
  elements.presetSelect.innerHTML = "";
  presets.forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset.preset_id;
    option.textContent = `${preset.name} - ${preset.description}`;
    elements.presetSelect.appendChild(option);
  });
  elements.presetSelect.value = presets[0]?.preset_id || "";
}

function formatSignedPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function formatNumber(value, digits = 2) {
  return Number(value || 0).toFixed(digits);
}

function laneColor(lane) {
  return {
    north: "#7c9cff",
    south: "#62e197",
    east: "#f7c66a",
    west: "#ff7a90",
  }[lane];
}

function drawBarChart(canvas, labels, datasetA, datasetB, legendA, legendB, suffix = "") {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#071018";
  ctx.fillRect(0, 0, width, height);

  const margin = { top: 40, right: 30, bottom: 60, left: 60 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const maxValue = Math.max(...datasetA, ...datasetB, 1);
  const groupWidth = plotWidth / labels.length;
  const barWidth = Math.min(50, groupWidth * 0.28);

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i += 1) {
    const y = margin.top + (plotHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(width - margin.right, y);
    ctx.stroke();
  }

  labels.forEach((label, index) => {
    const centerX = margin.left + groupWidth * index + groupWidth / 2;
    const aHeight = (datasetA[index] / maxValue) * plotHeight;
    const bHeight = (datasetB[index] / maxValue) * plotHeight;
    const xA = centerX - barWidth - 6;
    const xB = centerX + 6;
    const yA = margin.top + plotHeight - aHeight;
    const yB = margin.top + plotHeight - bHeight;

    ctx.fillStyle = "rgba(124, 156, 255, 0.8)";
    ctx.fillRect(xA, yA, barWidth, aHeight);
    ctx.fillStyle = "rgba(57, 211, 198, 0.8)";
    ctx.fillRect(xB, yB, barWidth, bHeight);

    ctx.fillStyle = "#eaf1ff";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(label, centerX, height - 26);
    ctx.fillStyle = "#97a7c6";
    ctx.fillText(`${datasetA[index].toFixed(1)}${suffix}`, xA + barWidth / 2, yA - 8);
    ctx.fillText(`${datasetB[index].toFixed(1)}${suffix}`, xB + barWidth / 2, yB - 8);
  });

  ctx.fillStyle = "rgba(124, 156, 255, 0.8)";
  ctx.fillRect(margin.left, 12, 16, 16);
  ctx.fillStyle = "#eaf1ff";
  ctx.textAlign = "left";
  ctx.fillText(legendA, margin.left + 24, 25);
  ctx.fillStyle = "rgba(57, 211, 198, 0.8)";
  ctx.fillRect(margin.left + 120, 12, 16, 16);
  ctx.fillStyle = "#eaf1ff";
  ctx.fillText(legendB, margin.left + 144, 25);
}

function drawLineChart(canvas, seriesA, seriesB, labelA, labelB) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#071018";
  ctx.fillRect(0, 0, width, height);

  const margin = { top: 30, right: 24, bottom: 44, left: 50 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const allValues = [...seriesA.map((p) => Object.values(p.queue_lengths).reduce((a, b) => a + b, 0)), ...seriesB.map((p) => Object.values(p.queue_lengths).reduce((a, b) => a + b, 0))];
  const maxValue = Math.max(...allValues, 1);
  const maxLength = Math.max(seriesA.length, seriesB.length, 2);

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  for (let i = 0; i <= 5; i += 1) {
    const y = margin.top + (plotHeight / 5) * i;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(width - margin.right, y);
    ctx.stroke();
  }

  function plotSeries(series, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.beginPath();
    series.forEach((point, index) => {
      const totalQueue = Object.values(point.queue_lengths).reduce((a, b) => a + b, 0);
      const x = margin.left + (index / (maxLength - 1)) * plotWidth;
      const y = margin.top + plotHeight - (totalQueue / maxValue) * plotHeight;
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
  }

  plotSeries(seriesA, "rgba(124, 156, 255, 0.95)");
  plotSeries(seriesB, "rgba(57, 211, 198, 0.95)");

  ctx.fillStyle = "rgba(124, 156, 255, 0.8)";
  ctx.fillRect(margin.left, 10, 16, 16);
  ctx.fillStyle = "#eaf1ff";
  ctx.fillText(labelA, margin.left + 24, 23);
  ctx.fillStyle = "rgba(57, 211, 198, 0.8)";
  ctx.fillRect(margin.left + 120, 10, 16, 16);
  ctx.fillStyle = "#eaf1ff";
  ctx.fillText(labelB, margin.left + 144, 23);
}

function drawVisionChart(vision) {
  if (!vision) return;
  const lanes = Object.keys(vision.summary.average_counts);
  const counts = lanes.map((lane) => vision.summary.average_counts[lane]);
  const densities = lanes.map((lane) => vision.summary.average_density[lane] * 10);
  drawBarChart(
    elements.visionChart,
    lanes.map((lane) => lane.toUpperCase()),
    counts,
    densities,
    "Avg tracked vehicles",
    "Density x10",
    ""
  );
}

function updateMetricCards(comparison) {
  const { baseline, adaptive, improvements } = comparison;
  elements.waitReduction.textContent = formatSignedPercent(improvements.wait_time_reduction_pct);
  elements.waitDetail.textContent = `Baseline ${formatNumber(baseline.metrics.average_wait_s)}s vs adaptive ${formatNumber(adaptive.metrics.average_wait_s)}s`;

  elements.throughputImprovement.textContent = formatSignedPercent(improvements.throughput_improvement_pct);
  elements.throughputDetail.textContent = `Baseline ${baseline.metrics.throughput} vehicles vs adaptive ${adaptive.metrics.throughput}`;

  elements.queueReduction.textContent = formatSignedPercent(improvements.max_queue_reduction_pct);
  elements.queueDetail.textContent = `Baseline ${baseline.metrics.max_total_queue} vehicles vs adaptive ${adaptive.metrics.max_total_queue}`;

  elements.co2Reduction.textContent = formatSignedPercent(improvements.co2_reduction_pct);
  elements.co2Detail.textContent = `Baseline ${formatNumber(baseline.metrics.estimated_co2_kg)}kg vs adaptive ${formatNumber(adaptive.metrics.estimated_co2_kg)}kg`;
}

function renderDecisionLog(decisions) {
  elements.decisionList.innerHTML = "";
  decisions.slice(0, 10).forEach((decision) => {
    const item = document.createElement("article");
    item.className = "decision-item";
    item.innerHTML = `
      <h3>t=${decision.t}s - ${decision.selected_phase}</h3>
      <p><strong>${decision.green_duration_s}s green.</strong> ${decision.reason}</p>
    `;
    elements.decisionList.appendChild(item);
  });
}

function renderVisionSummary(vision) {
  if (!vision) {
    elements.visionSummary.innerHTML = "<p>Run a video analysis to see lane counts and density.</p>";
    return;
  }
  const avgDensity = Object.values(vision.summary.average_density).reduce((sum, value) => sum + value, 0) / Math.max(Object.keys(vision.summary.average_density).length, 1);
  const totalPeak = Object.values(vision.summary.peak_counts).reduce((sum, value) => sum + value, 0);
  elements.visionSummary.innerHTML = `
    <div class="vision-kpi">
      <span>Video</span>
      <strong>${vision.video_name}</strong>
    </div>
    <div class="vision-kpi">
      <span>Frames analyzed</span>
      <strong>${vision.summary.frames_analyzed}</strong>
    </div>
    <div class="vision-kpi">
      <span>Average density</span>
      <strong>${avgDensity.toFixed(2)}</strong>
    </div>
    <div class="vision-kpi">
      <span>Total peak count</span>
      <strong>${totalPeak}</strong>
    </div>
  `;
}

function renderIntersection(frame) {
  const canvas = elements.junctionCanvas;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  ctx.fillStyle = "#06111a";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#29303d";
  ctx.fillRect(380, 0, 200, height);
  ctx.fillRect(0, 170, width, 200);

  ctx.strokeStyle = "rgba(255,255,255,0.16)";
  ctx.setLineDash([14, 10]);
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(480, 0);
  ctx.lineTo(480, 170);
  ctx.moveTo(480, 370);
  ctx.lineTo(480, height);
  ctx.moveTo(0, 270);
  ctx.lineTo(380, 270);
  ctx.moveTo(580, 270);
  ctx.lineTo(width, 270);
  ctx.stroke();
  ctx.setLineDash([]);

  const queue = frame?.queue_lengths || { north: 0, south: 0, east: 0, west: 0 };
  const phase = frame?.phase;
  const stage = frame?.stage || "idle";
  const greenLanes = stage === "green" && phase ? PHASE_TO_LANES[phase] || [] : [];
  const amberLanes = stage === "transition" && phase ? PHASE_TO_LANES[phase] || [] : [];

  const barScale = 8;
  drawLaneBar(ctx, "north", 425, 150 - queue.north * barScale, 110, queue.north * barScale, queue.north);
  drawLaneBar(ctx, "south", 425, 390, 110, queue.south * barScale, queue.south);
  drawLaneBar(ctx, "west", 150 - queue.west * barScale, 215, queue.west * barScale, 110, queue.west);
  drawLaneBar(ctx, "east", 640, 215, queue.east * barScale, 110, queue.east);

  drawSignal(ctx, 450, 190, greenLanes.includes("north"), amberLanes.includes("north"));
  drawSignal(ctx, 510, 350, greenLanes.includes("south"), amberLanes.includes("south"));
  drawSignal(ctx, 610, 240, greenLanes.includes("east"), amberLanes.includes("east"));
  drawSignal(ctx, 350, 300, greenLanes.includes("west"), amberLanes.includes("west"));

  ctx.fillStyle = "#eaf1ff";
  ctx.font = "bold 22px sans-serif";
  ctx.fillText(`Phase: ${phase || "idle"}`, 24, 34);
  ctx.font = "16px sans-serif";
  ctx.fillStyle = "#97a7c6";
  ctx.fillText(`Stage: ${stage}`, 24, 60);
  ctx.fillText(`t = ${frame?.t ?? 0}s`, 24, 84);
  ctx.fillText(`Throughput: ${frame?.throughput ?? 0}`, 24, 108);
  ctx.fillText(`Avg wait: ${(frame?.avg_wait_s ?? 0).toFixed(2)}s`, 24, 132);
}

function drawLaneBar(ctx, lane, x, y, width, height, value) {
  ctx.fillStyle = laneColor(lane);
  ctx.globalAlpha = 0.85;
  ctx.fillRect(x, y, width, height);
  ctx.globalAlpha = 1;
  ctx.strokeStyle = "rgba(255,255,255,0.18)";
  ctx.strokeRect(x, y, width, height);
  ctx.fillStyle = "#eaf1ff";
  ctx.font = "bold 16px sans-serif";
  ctx.fillText(`${lane.toUpperCase()} ${value}`, x + 8, y + 24);
}

function drawSignal(ctx, x, y, isGreen, isAmber) {
  ctx.fillStyle = "#0f1723";
  ctx.fillRect(x, y, 32, 76);
  const colors = isGreen ? ["#4a566f", "#4a566f", "#62e197"] : isAmber ? ["#4a566f", "#f7c66a", "#4a566f"] : ["#ff7a90", "#4a566f", "#4a566f"];
  colors.forEach((color, index) => {
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(x + 16, y + 14 + index * 24, 8, 0, Math.PI * 2);
    ctx.fill();
  });
}

function animateAdaptiveTimeline() {
  if (!state.comparison) return;
  const timeline = state.comparison.adaptive.timeline;
  if (!timeline || timeline.length === 0) return;
  if (state.timelineHandle) clearInterval(state.timelineHandle);
  state.timelineIndex = 0;
  renderIntersection(timeline[0]);
  state.timelineHandle = setInterval(() => {
    renderIntersection(timeline[state.timelineIndex]);
    state.timelineIndex = (state.timelineIndex + 1) % timeline.length;
  }, 350);
}

async function runScenario() {
  const presetId = elements.presetSelect.value;
  setStatus(`Running scenario: ${presetId}`);
  const comparison = await fetchJson(`/api/simulate/run?preset_id=${encodeURIComponent(presetId)}`, {
    method: "POST",
  });
  state.comparison = comparison;
  elements.scenarioName.textContent = comparison.scenario_name;
  setStatus(`Loaded ${comparison.scenario_name}`);

  updateMetricCards(comparison);
  renderDecisionLog(comparison.adaptive.decisions);
  drawBarChart(
    elements.comparisonChart,
    ["Avg wait", "Throughput", "Max queue", "CO2"],
    [
      comparison.baseline.metrics.average_wait_s,
      comparison.baseline.metrics.throughput,
      comparison.baseline.metrics.max_total_queue,
      comparison.baseline.metrics.estimated_co2_kg,
    ],
    [
      comparison.adaptive.metrics.average_wait_s,
      comparison.adaptive.metrics.throughput,
      comparison.adaptive.metrics.max_total_queue,
      comparison.adaptive.metrics.estimated_co2_kg,
    ],
    "Baseline",
    "Adaptive"
  );
  drawLineChart(
    elements.queueChart,
    comparison.baseline.timeline,
    comparison.adaptive.timeline,
    "Baseline total queue",
    "Adaptive total queue"
  );
  animateAdaptiveTimeline();
}

async function analyzeBundledVideo() {
  setStatus("Analyzing bundled demo video...");
  const vision = await fetchJson("/api/vision/analyze-sample", { method: "POST" });
  state.vision = vision;
  renderVisionSummary(vision);
  drawVisionChart(vision);
  setStatus(`Analyzed ${vision.video_name}`);
}

async function analyzeUploadedVideo() {
  const file = elements.videoUpload.files?.[0];
  if (!file) {
    setStatus("Please choose a video file before uploading.");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  setStatus(`Uploading ${file.name} for analysis...`);
  const response = await fetch("/api/vision/analyze-upload", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Video analysis failed");
  }
  const vision = await response.json();
  state.vision = vision;
  renderVisionSummary(vision);
  drawVisionChart(vision);
  setStatus(`Analyzed ${vision.video_name}`);
}

async function init() {
  try {
    await checkHealth();
    await loadPresets();
    await runScenario();
    await analyzeBundledVideo();
  } catch (error) {
    setStatus(`Initialization failed: ${error.message}`);
  }
}

elements.runScenarioBtn.addEventListener("click", async () => {
  try {
    await runScenario();
  } catch (error) {
    setStatus(`Scenario run failed: ${error.message}`);
  }
});

elements.sampleVisionBtn.addEventListener("click", async () => {
  try {
    await analyzeBundledVideo();
  } catch (error) {
    setStatus(`Vision analysis failed: ${error.message}`);
  }
});

elements.uploadVisionBtn.addEventListener("click", async () => {
  try {
    await analyzeUploadedVideo();
  } catch (error) {
    setStatus(`Upload analysis failed: ${error.message}`);
  }
});

init();
