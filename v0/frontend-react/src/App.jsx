import { useState, useEffect, useRef } from 'react';
import { Chessboard } from 'react-chessboard';
import './App.css';

function App() {
  const [gameData, setGameData] = useState(null);
  const [currentPly, setCurrentPly] = useState(0);
  const [status, setStatus] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [boardPosition, setBoardPosition] = useState('start');
  const playIntervalRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('pgn', file);

    setStatus('Uploading and analyzing...');

    try {
      const res = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      setGameData(data);
      setCurrentPly(0);
      setStatus('Analysis complete!');
    } catch (err) {
      setStatus(`Error: ${err.message}`);
      console.error(err);
    }
  };

  const positions = gameData?.engine?.positions || [];
  const currentPosition = positions[currentPly];
  const currentFen = currentPosition?.fen || 'start';

  // Format evaluation for display
  const formatEval = (evalData) => {
    if (!evalData) return 'N/A';
    if (evalData.mate !== null) {
      return `M${evalData.mate}`;
    }
    if (evalData.cp !== null) {
      const pawns = (evalData.cp / 100).toFixed(2);
      return pawns >= 0 ? `+${pawns}` : pawns;
    }
    return 'N/A';
  };

  const currentEval = formatEval(currentPosition?.eval);

  // Check if current ply is a critical moment
  const criticalMoments = gameData?.insights?.top_turning_points || [];
  const isCriticalMoment = criticalMoments.some(tp => tp.ply === currentPly);
  const criticalMomentData = criticalMoments.find(tp => tp.ply === currentPly);

  // Update board position when ply changes
  useEffect(() => {
    console.log('Current Ply:', currentPly);
    console.log('Current FEN:', currentFen);
    setBoardPosition(currentFen);
  }, [currentPly, currentFen]);

  // Navigation functions
  const goToStart = () => {
    setCurrentPly(0);
    setIsPlaying(false);
  };

  const goToPrev = () => {
    setCurrentPly((prev) => Math.max(0, prev - 1));
  };

  const goToNext = () => {
    setCurrentPly((prev) => Math.min(positions.length - 1, prev + 1));
  };

  const goToEnd = () => {
    setCurrentPly(positions.length - 1);
    setIsPlaying(false);
  };

  const togglePlay = () => {
    setIsPlaying((prev) => !prev);
  };

  // Auto-play effect
  useEffect(() => {
    if (isPlaying) {
      playIntervalRef.current = setInterval(() => {
        setCurrentPly((prev) => {
          if (prev >= positions.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 800); // 800ms between moves
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    }

    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, [isPlaying, positions.length]);

  return (
    <div className="app">
      <h1>Chess Analyzer v0</h1>

      <div className="upload-section">
        <input type="file" accept=".pgn" onChange={handleFileUpload} />
        {status && <p className="status">{status}</p>}
      </div>

      {gameData && (
        <div className="board-section">
          <div className="board-container">
            <div style={{ width: '450px' }}>
              <Chessboard
                key={`${currentPly}-${boardPosition}`}
                position={boardPosition}
                boardWidth={450}
                animationDuration={0}
                arePiecesDraggable={false}
              />
            </div>

            <div className="controls">
              <button onClick={goToStart} disabled={currentPly === 0}>⏮ Start</button>
              <button onClick={goToPrev} disabled={currentPly === 0}>◀ Prev</button>
              <button onClick={togglePlay}>
                {isPlaying ? '⏸ Pause' : '▶ Play'}
              </button>
              <button onClick={goToNext} disabled={currentPly >= positions.length - 1}>Next ▶</button>
              <button onClick={goToEnd} disabled={currentPly >= positions.length - 1}>End ⏭</button>
            </div>

            <div className="info">
              <p><strong>Ply:</strong> {currentPly} / {positions.length - 1}</p>
              {currentPosition?.move && (
                <p><strong>Move:</strong> {currentPosition.move.san}</p>
              )}
            </div>
          </div>

          <div className="game-info">
            <div className="eval-display">
              <h3>Engine Evaluation</h3>
              <div className="eval-value">{currentEval}</div>
              <p className="eval-label">White's perspective</p>
            </div>

            {isCriticalMoment && criticalMomentData && (
              <div className="critical-moment">
                <div className="critical-header">
                  <span className="star">⭐</span>
                  <h3>Critical Moment!</h3>
                </div>
                <p><strong>Move:</strong> {criticalMomentData.played?.san}</p>
                <p><strong>Eval before:</strong> {formatEval({ cp: criticalMomentData.eval_before_cp, mate: null })}</p>
                <p><strong>Eval after:</strong> {formatEval({ cp: criticalMomentData.eval_after_cp, mate: null })}</p>
                <p><strong>Delta:</strong> {(criticalMomentData.delta_cp_white_pov / 100).toFixed(2)} pawns</p>
                <p><strong>Best move was:</strong> {criticalMomentData.best_move_uci}</p>
              </div>
            )}

            <div className="game-details">
              <h3>Game Info</h3>
              <p>White: {gameData.engine.headers.White}</p>
              <p>Black: {gameData.engine.headers.Black}</p>
              <p>Result: {gameData.engine.headers.Result}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
