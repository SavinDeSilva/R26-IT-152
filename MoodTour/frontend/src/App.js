import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = "http://127.0.0.1:5002";
const CATEGORY_OPTIONS = ["nature", "beach", "cultural", "adventure", "wildlife"];
const TRAVELER_TYPES = ["solo", "couple", "family", "group"];

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [health, setHealth] = useState("checking...");
  const [emotion, setEmotion] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [budget, setBudget] = useState(30000);
  const [days, setDays] = useState(2);
  const [travelerType, setTravelerType] = useState("solo");
  const [preferences, setPreferences] = useState(["nature", "beach"]);
  const [suggestedPlaces, setSuggestedPlaces] = useState([]);
  const [selectedPlaces, setSelectedPlaces] = useState([]);
  const [itineraryData, setItineraryData] = useState(null);
  const [loadingEmotion, setLoadingEmotion] = useState(false);
  const [loadingItinerary, setLoadingItinerary] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let stream;
    async function setupCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setCameraReady(true);
        }
      } catch (e) {
        setError("Camera access failed. Allow webcam permission in your browser.");
      }
    }
    setupCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status || "running"))
      .catch(() => setHealth("offline"));
  }, []);

  const formattedConfidence = useMemo(() => {
    if (confidence === null || confidence === undefined) return "-";
    return `${(Number(confidence) * 100).toFixed(1)}%`;
  }, [confidence]);

  function captureBase64Frame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      throw new Error("Camera not initialized.");
    }
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.9);
  }

  async function onDetectEmotion() {
    setError("");
    setLoadingEmotion(true);
    try {
      const image_base64 = captureBase64Frame();
      const res = await fetch(`${API_BASE}/detect-emotion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Emotion detection failed.");
      setEmotion(data.emotion || "");
      setConfidence(data.confidence);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoadingEmotion(false);
    }
  }

  async function onGenerateItinerary(useSelected = false) {
    setError("");
    setLoadingItinerary(true);
    try {
      const res = await fetch(`${API_BASE}/generate-itinerary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          emotion: emotion || "neutral",
          budget: Number(budget),
          days: Number(days),
          traveler_type: travelerType,
          attraction_preferences: preferences,
          selected_places: useSelected ? selectedPlaces : [],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Itinerary generation failed.");
      setItineraryData(data);
      setSuggestedPlaces(data.suggested_places || []);
      if (!useSelected) setSelectedPlaces([]);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoadingItinerary(false);
    }
  }

  function togglePreference(cat) {
    setPreferences((prev) =>
      prev.includes(cat) ? prev.filter((x) => x !== cat) : [...prev, cat]
    );
  }

  function toggleSelectedPlace(name) {
    setSelectedPlaces((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  }

  return (
    <div className="app">
      <header className="hero glass clean">
        <h1>MoodTour Smart Tourism Platform</h1>
        <p>
          Emotion-aware itinerary planning with safe tourism recommendations for Sri Lanka
        </p>
        <span className={`health ${health === "running" ? "ok" : "bad"}`}>API: {health}</span>
      </header>

      <main className="grid">
        <section className="glass card webcam-card clean">
          <h2>Webcam Preview</h2>
          <div className="video-wrap">
            <video ref={videoRef} playsInline muted />
            {!cameraReady && <div className="overlay">Connecting camera...</div>}
          </div>
          <button className="btn primary" onClick={onDetectEmotion} disabled={loadingEmotion}>
            {loadingEmotion ? "Detecting..." : "Detect Emotion"}
          </button>
          <canvas ref={canvasRef} className="hidden" />
        </section>

        <section className="glass card detect-card clean">
          <h2>Detected Emotion</h2>
          <div className="metric">
            <label>Emotion</label>
            <div className="value">{emotion || "-"}</div>
          </div>
          <div className="metric">
            <label>Confidence</label>
            <div className="value">{formattedConfidence}</div>
          </div>
        </section>

        <section className="glass card form-card clean">
          <h2>Trip Inputs</h2>
          <div className="form-grid">
            <label>
              Budget (LKR)
              <input
                type="number"
                value={budget}
                min={1000}
                onChange={(e) => setBudget(e.target.value)}
              />
            </label>
            <label>
              Travel Days
              <input
                type="number"
                value={days}
                min={1}
                max={31}
                onChange={(e) => setDays(e.target.value)}
              />
            </label>
            <label>
              Traveler Type
              <select value={travelerType} onChange={(e) => setTravelerType(e.target.value)}>
                {TRAVELER_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <h3>Attraction Preferences</h3>
          <div className="chips">
            {CATEGORY_OPTIONS.map((cat) => (
              <button
                key={cat}
                type="button"
                className={`chip ${preferences.includes(cat) ? "selected" : ""}`}
                onClick={() => togglePreference(cat)}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="action-row">
            <button className="btn accent" onClick={() => onGenerateItinerary(false)} disabled={loadingItinerary}>
              {loadingItinerary ? "Generating..." : "Generate Suggestions + Itinerary"}
            </button>
            <button
              className="btn neutral"
              onClick={() => onGenerateItinerary(true)}
              disabled={loadingItinerary || selectedPlaces.length === 0}
            >
              Generate from Selected Places
            </button>
          </div>
          <p className="hint">
            Step 1: Generate suggestions. Step 2: pick places below. Step 3: generate from selected places.
          </p>
        </section>

        <section className="glass card select-card clean">
          <h2>Choose from Suggested Places</h2>
          {!suggestedPlaces.length ? (
            <p className="muted">Suggestions will appear here after first generation.</p>
          ) : (
            <div className="suggest-grid">
              {suggestedPlaces.map((p) => {
                const isPicked = selectedPlaces.includes(p.name);
                return (
                  <button
                    key={p.name}
                    type="button"
                    className={`suggest-card ${isPicked ? "picked" : ""}`}
                    onClick={() => toggleSelectedPlace(p.name)}
                  >
                    <div className="top">
                      <strong>{p.name}</strong>
                      <span>#{p.rank}</span>
                    </div>
                    <div className="meta">{p.category} · {p.region}</div>
                    <div className="meta">Safety {p.safety_score}/10 · LKR {p.estimated_cost}</div>
                  </button>
                );
              })}
            </div>
          )}
          <div className="selection-status">{selectedPlaces.length} place(s) selected</div>
        </section>
      </main>

      {error && <div className="glass error">{error}</div>}

      <section className="glass card itinerary-section clean">
        <h2>Itinerary (Clear Day-by-Day Plan)</h2>
        {!itineraryData ? (
          <p className="muted">Generate itinerary to view day plans.</p>
        ) : (
          <>
            <div className="summary-grid">
              <div className="summary-item">
                <label>Safety Score</label>
                <strong>{itineraryData.safety_score ?? "-"}</strong>
              </div>
              <div className="summary-item">
                <label>Estimated Budget</label>
                <strong>LKR {itineraryData.estimated_budget ?? "-"}</strong>
              </div>
              <div className="summary-item">
                <label>Destinations</label>
                <strong>{(itineraryData.recommended_places || []).length}</strong>
              </div>
            </div>

            <div className="timeline">
              {((itineraryData.itinerary_days && itineraryData.itinerary_days.length > 0)
                ? itineraryData.itinerary_days
                : Object.entries(itineraryData.itinerary || {}).map(([day, stops], idx) => ({
                    day: idx + 1,
                    title: day.toUpperCase(),
                    place: "-",
                    activity: (stops || []).join(" | "),
                    region: "-",
                    estimated_cost: "-",
                    safety_score: "-",
                  }))
              ).map((d) => (
                <div className="timeline-item" key={d.day || d.title}>
                  <div className="dot" />
                  <div className="timeline-card">
                    <h4>{d.title || `DAY ${d.day}`}</h4>
                    <p><strong>Place:</strong> {d.place || "-"}</p>
                    <p><strong>Activity:</strong> {d.activity || "-"}</p>
                    <p>
                      <strong>Region:</strong> {d.region} · <strong>Cost:</strong> LKR {d.estimated_cost} ·{" "}
                      <strong>Safety:</strong> {d.safety_score}/10
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default App;
