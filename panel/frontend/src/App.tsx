import { useState, useEffect, useRef } from "react";
import { api, Timer, TimerCreate } from "./api";
import { wsClient } from "./ws";

function formatTime(seconds: number): string {
  if (seconds <= 0) return "REFILL";

  if (seconds <= 60) {
    return `${seconds}`;
  }

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs
    .toString()
    .padStart(2, "0")}`;
}

function TimerCard({
  timer,
  onAdjust,
  onDelete,
  onRestart,
}: {
  timer: Timer;
  onAdjust: (id: string, seconds: number) => void;
  onDelete: (id: string) => void;
  onRestart: (id: string) => void;
}) {
  // Client-side local countdown
  const [localRemaining, setLocalRemaining] = useState(timer.remaining_seconds);
  const lastSyncTime = useRef(Date.now());
  const lastSyncRemaining = useRef(timer.remaining_seconds);
  const animationFrameRef = useRef<number | null>(null);

  // Sync local time when update received from WebSocket
  useEffect(() => {
    lastSyncTime.current = Date.now();
    lastSyncRemaining.current = timer.remaining_seconds;
    setLocalRemaining(timer.remaining_seconds);
  }, [timer.remaining_seconds]);

  // Client-side countdown using requestAnimationFrame for smoothness
  useEffect(() => {
    if (timer.status !== "active") {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    let lastUpdate = Date.now();

    const updateCountdown = () => {
      const now = Date.now();

      // Update display every 250ms
      if (now - lastUpdate >= 250) {
        const elapsed = Math.floor((now - lastSyncTime.current) / 1000);
        const calculated = lastSyncRemaining.current - elapsed;

        if (calculated >= 0) {
          setLocalRemaining(calculated);
        } else {
          setLocalRemaining(0);
        }

        lastUpdate = now;
      }

      animationFrameRef.current = requestAnimationFrame(updateCountdown);
    };

    animationFrameRef.current = requestAnimationFrame(updateCountdown);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [timer.status]);

  return (
    <div className="timer-card">
      <h3>{timer.name}</h3>
      <div className="timer-time">{formatTime(localRemaining)}</div>
      {timer.status === "active" && (
        <>
          <div className="timer-controls">
            <button
              className="btn btn-primary"
              onClick={() => onAdjust(timer.id, 1)}
            >
              +1s
            </button>
            <button
              className="btn btn-primary"
              onClick={() => onAdjust(timer.id, -1)}
            >
              -1s
            </button>
            <button
              className="btn btn-danger"
              onClick={() => onDelete(timer.id)}
            >
              Delete
            </button>
          </div>
        </>
      )}
      {timer.status === "completed" && (
        <>
          <div className="status-badge completed">🎯 Finished</div>
          <div className="timer-controls">
            <button
              className="btn btn-success"
              onClick={() => onRestart(timer.id)}
            >
              🔄 Restart
            </button>
            <button
              className="btn btn-danger"
              onClick={() => onDelete(timer.id)}
            >
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function App() {
  const [timers, setTimers] = useState<Timer[]>([]);
  const [error, setError] = useState<string>("");
  const [formData, setFormData] = useState<TimerCreate>({
    name: "",
    minutes: 5,
    seconds: 0,
  });

  // Load initial data
  useEffect(() => {
    loadTimers();
  }, []);

  // Connect WebSocket
  useEffect(() => {
    wsClient.connect();

    wsClient.onMessage((updatedTimers) => {
      setTimers(updatedTimers);
    });

    return () => {
      wsClient.disconnect();
    };
  }, []);

  const loadTimers = async () => {
    try {
      const data = await api.getTimers();
      setTimers(data);
      setError("");
    } catch (err) {
      setError("Failed to load timers");
      console.error(err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError("Please enter timer name");
      return;
    }

    if (formData.minutes === 0 && formData.seconds === 0) {
      setError("Time cannot be 0");
      return;
    }

    try {
      await api.createTimer(formData);
      setFormData({ name: "", minutes: 5, seconds: 0 });
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to create timer");
    }
  };

  const handleAdjust = async (id: string, seconds: number) => {
    try {
      await api.adjustTimer(id, seconds);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to adjust timer");
    }
  };

  const handleRestart = async (id: string) => {
    try {
      await api.restartTimer(id);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to restart timer");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this timer?")) {
      return;
    }

    try {
      await api.deleteTimer(id);
      setError("");
    } catch (err: any) {
      setError(err.message || "Failed to delete timer");
    }
  };

  // Display active and completed timers
  const displayTimers = Array.isArray(timers)
    ? timers.filter((t) => t.status === "active" || t.status === "completed")
    : [];

  return (
    <div className="container">
      <div className="header">
        <h1>WOS Refill Timer Panel</h1>
        <p>Refill Timer Panel</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="create-form">
        <h2>New Timer</h2>
        <form onSubmit={handleCreate}>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              placeholder="Anna, Howe"
              maxLength={50}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Minutes</label>
              <input
                type="number"
                value={formData.minutes}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    minutes: parseInt(e.target.value) || 0,
                  })
                }
                min="0"
                max="59"
              />
            </div>

            <div className="form-group">
              <label>Seconds</label>
              <input
                type="number"
                value={formData.seconds}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    seconds: parseInt(e.target.value) || 0,
                  })
                }
                min="0"
                max="59"
              />
            </div>
          </div>

          <button type="submit" className="btn btn-create">
            ✨ Create Timer
          </button>
        </form>
      </div>

      {displayTimers.length > 0 ? (
        <div className="timers-grid">
          {displayTimers.map((timer) => (
            <TimerCard
              key={timer.id}
              timer={timer}
              onAdjust={handleAdjust}
              onDelete={handleDelete}
              onRestart={handleRestart}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <p>No active timers</p>
          <p>👇 New timers will appear here</p>
        </div>
      )}
    </div>
  );
}

export default App;
