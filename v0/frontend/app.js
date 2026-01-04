const statusEl = document.getElementById("status");
const rawEl = document.getElementById("raw");
const gameInfoEl = document.getElementById("gameInfo");
const turningPointsEl = document.getElementById("turningPoints");

document.getElementById("analyzeBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("pgnFile");
  if (!fileInput.files.length) {
    statusEl.textContent = "Pick a PGN file first.";
    return;
  }

  const file = fileInput.files[0];
  const form = new FormData();
  form.append("pgn", file);

  statusEl.textContent = "Uploading + analyzing…";
  rawEl.textContent = "";
  turningPointsEl.textContent = "";

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText);
    }

    const data = await res.json();
    rawEl.textContent = JSON.stringify(data, null, 2);

    // Small "nice" summary
    const headers = data.engine?.headers || {};
    gameInfoEl.textContent =
      `White: ${headers.White || "?"}\n` +
      `Black: ${headers.Black || "?"}\n` +
      `Result: ${headers.Result || "?"}\n` +
      `Run ID: ${data.run_id}\n` +
      `Positions: ${data.engine?.positions?.length || 0}`;

    const tps = data.insights?.top_turning_points || [];
    turningPointsEl.textContent = tps.map((tp, i) => {
      return (
        `#${i + 1} ply ${tp.ply} (${tp.played?.san})\n` +
        `  eval before: ${tp.eval_before_cp} cp\n` +
        `  eval after:  ${tp.eval_after_cp} cp\n` +
        `  delta:       ${tp.delta_cp_white_pov} cp\n` +
        `  best:        ${tp.best_move_uci}\n`
      );
    }).join("\n");

    statusEl.textContent = "Done.";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Error: " + e.message;
  }
});
