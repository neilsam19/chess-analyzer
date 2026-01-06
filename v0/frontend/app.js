const statusEl = document.getElementById("status");
const rawEl = document.getElementById("raw");
const gameInfoEl = document.getElementById("gameInfo");
const turningPointsEl = document.getElementById("turningPoints");
const boardSectionEl = document.getElementById("boardSection");

// Global state
let board = null;
let gameData = null;
let currentPly = 0;

// Initialize board (will be created after first analysis)
function initBoard() {
  board = Chessboard('board', {
    draggable: false,
    position: 'start'
  });
}

// Update board to show position at current ply
function updateBoard() {
  if (!gameData || !board) return;

  const positions = gameData.engine?.positions || [];
  if (currentPly >= 0 && currentPly < positions.length) {
    const pos = positions[currentPly];
    board.position(pos.fen);
  }
}

// Display game data
function displayGame(data) {
  gameData = data;
  currentPly = 0;

  // Show board section
  boardSectionEl.style.display = 'block';

  // Initialize board if not already done
  if (!board) {
    initBoard();
  }

  // Update board to initial position
  updateBoard();

  // Display game info
  const headers = data.engine?.headers || {};
  gameInfoEl.textContent =
    `White: ${headers.White || "?"}\n` +
    `Black: ${headers.Black || "?"}\n` +
    `Result: ${headers.Result || "?"}\n` +
    `Run ID: ${data.run_id}\n` +
    `Positions: ${data.engine?.positions?.length || 0}\n` +
    `Current Ply: ${currentPly}`;

  // Display turning points
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
}

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

    // Display the game with board
    displayGame(data);

    statusEl.textContent = "Done.";
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Error: " + e.message;
  }
});
