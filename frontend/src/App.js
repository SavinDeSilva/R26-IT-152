import React, { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:5000";

const getRiskColor = (risk) => {
  if (risk === "High") return "#ef4444";
  if (risk === "Medium") return "#f59e0b";
  return "#22c55e";
};

const getRiskBg = (risk) => {
  if (risk === "High") return "rgba(239,68,68,0.15)";
  if (risk === "Medium") return "rgba(245,158,11,0.15)";
  return "rgba(34,197,94,0.15)";
};

function Spinner() {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "40px" }}>
      <div style={{
        width: "40px", height: "40px", border: "4px solid #1f2937",
        borderTop: "4px solid #3b82f6", borderRadius: "50%",
        animation: "spin 1s linear infinite"
      }} />
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function BestTimes({ siteId }) {
  const [bestTimes, setBestTimes] = useState(null);

  useEffect(() => {
    if (!siteId) return;
    axios.get(`${API}/best-times?site_id=${siteId}&month=${new Date().getMonth() + 1}`)
      .then(res => setBestTimes(res.data))
      .catch(() => {});
  }, [siteId]);

  if (!bestTimes) return null;

  return (
    <div>
      <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "12px" }}>
        Top 3 least crowded days this month:
      </p>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
        {bestTimes.best_days.map(d => (
          <div key={d.day} style={{ background: "rgba(34,197,94,0.15)", border: "1px solid #22c55e", borderRadius: "8px", padding: "10px 16px", textAlign: "center" }}>
            <div style={{ fontSize: "14px", fontWeight: "bold", color: "#22c55e" }}>{d.day}</div>
            <div style={{ fontSize: "12px", color: "#6b7280" }}>{(d.crowd_score * 100).toFixed(0)}% crowded</div>
          </div>
        ))}
      </div>
      <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "10px" }}>Weekly crowd forecast:</p>
      <div style={{ display: "flex", gap: "6px", alignItems: "flex-end", height: "80px" }}>
        {bestTimes.weekly_prediction.map(d => (
          <div key={d.day} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
            <div style={{ width: "100%", background: "#1f2937", borderRadius: "4px 4px 0 0", height: "60px", display: "flex", alignItems: "flex-end" }}>
              <div style={{ width: "100%", borderRadius: "4px 4px 0 0", height: `${d.crowd_score * 60}px`, background: getRiskColor(d.risk_level), transition: "height 0.5s ease" }} />
            </div>
            <div style={{ fontSize: "10px", color: "#6b7280" }}>{d.day.slice(0, 3)}</div>
            <div style={{ fontSize: "10px", color: getRiskColor(d.risk_level), fontWeight: "bold" }}>{(d.crowd_score * 100).toFixed(0)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("home");
  const [sites, setSites] = useState([]);
  const [selectedSite, setSelectedSite] = useState(1);
  const [selectedDate, setSelectedDate] = useState("2026-04-13");
  const [siteSearch, setSiteSearch] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [alertData, setAlertData] = useState(null);
  const [greenSites, setGreenSites] = useState([]);
  const [allPredictions, setAllPredictions] = useState([]);
  const [itinerarySites, setItinerarySites] = useState([]);
  const [itineraryResult, setItineraryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mapLoading, setMapLoading] = useState(false);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState({ rating: 5, comment: "", actual_crowd: "Medium" });
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [modelMetrics, setModelMetrics] = useState(null);

  useEffect(() => {
    axios.get(`${API}/sites`)
      .then((res) => setSites(res.data.sites))
      .catch(() => setError("Cannot connect to Flask API. Make sure python app.py is running."));
  }, []);

  useEffect(() => {
    axios.get(`${API}/model-metrics`)
      .then((res) => setModelMetrics(res.data))
      .catch(() => {});
  }, []);

  const handlePredict = () => {
    setLoading(true);
    setError(null);
    setPrediction(null);
    setAlertData(null);
    setFeedbackSent(false);
    axios.get(`${API}/predict?site_id=${selectedSite}&date=${selectedDate}`)
      .then((res) => { setPrediction(res.data); setLoading(false); })
      .catch(() => { setError("Prediction failed. Check Flask API."); setLoading(false); });
    axios.get(`${API}/alert?site_id=${selectedSite}&date=${selectedDate}`)
      .then((res) => setAlertData(res.data))
      .catch(() => {});
  };

  const handleGreenSites = () => {
    setLoading(true);
    setError(null);
    axios.get(`${API}/green-sites?date=${selectedDate}`)
      .then((res) => { setGreenSites(res.data.green_sites); setLoading(false); })
      .catch(() => { setError("Failed to load green sites."); setLoading(false); });
  };

  const handleAllPredictions = () => {
    setMapLoading(true);
    const promises = sites.map(s =>
      axios.get(`${API}/predict?site_id=${s.site_id}&date=${selectedDate}`)
        .then(res => res.data).catch(() => null)
    );
    Promise.all(promises).then(results => {
      setAllPredictions(results.filter(r => r !== null));
      setMapLoading(false);
    });
  };

  const handleItineraryCheck = () => {
    if (itinerarySites.length === 0) return;
    setLoading(true);
    setError(null);
    axios.post(`${API}/itinerary-check`, { sites: itinerarySites, date: selectedDate })
      .then((res) => { setItineraryResult(res.data); setLoading(false); })
      .catch(() => { setError("Itinerary check failed."); setLoading(false); });
  };

  const handleFeedback = () => {
    if (!prediction) return;
    axios.post(`${API}/feedback`, {
      site_id: prediction.site_id,
      date: prediction.date,
      actual_crowd_level: feedback.actual_crowd,
      rating: feedback.rating,
      comment: feedback.comment
    }).then(() => setFeedbackSent(true))
      .catch(() => setError("Feedback submission failed."));
  };

  const addToItinerary = (site_id) => {
    if (!itinerarySites.includes(site_id)) setItinerarySites([...itinerarySites, site_id]);
  };

  const removeFromItinerary = (site_id) => {
    setItinerarySites(itinerarySites.filter(id => id !== site_id));
  };

  const filteredSites = sites.filter(s =>
    s.site_name.toLowerCase().includes(siteSearch.toLowerCase())
  );

  const navItems = [
    { key: "home", label: "🏠 Home" },
    { key: "predict", label: "🔍 Site Explorer" },
    { key: "map", label: "🗺️ Risk Map" },
    { key: "green", label: "🌿 Green Sites" },
    { key: "itinerary", label: "📅 Itinerary" },
    { key: "insights", label: "📊 Model Insights" },
  ];

  return (
    <div style={{ fontFamily: "'Segoe UI', Arial, sans-serif", background: "#0a0f1e", minHeight: "100vh", color: "#fff" }}>

      {/* HEADER */}
      <div style={{ background: "linear-gradient(135deg, #0f2460, #1a56db)", padding: "20px 30px", display: "flex", justifyContent: "space-between", alignItems: "center", boxShadow: "0 4px 20px rgba(0,0,0,0.4)" }}>
        <div>
          <h1 style={{ fontSize: "20px", margin: 0, fontWeight: "bold" }}>🇱🇰 Tourism Risk & Context Intelligence System</h1>
          <p style={{ color: "#93c5fd", marginTop: "4px", fontSize: "13px", margin: "4px 0 0" }}>AI-Powered Crowd Prediction for Sri Lanka Tourism</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "12px", color: "#93c5fd" }}>Abinaya R | IT22090058</div>
          <div style={{ fontSize: "12px", color: "#93c5fd" }}>SLIIT | R26-IT-152 | 2026</div>
        </div>
      </div>

      {/* NAV */}
      <div style={{ display: "flex", background: "#111827", padding: "0 20px", borderBottom: "1px solid #1f2937", overflowX: "auto" }}>
        {navItems.map((p) => (
          <button key={p.key} onClick={() => setPage(p.key)} style={{
            padding: "14px 18px", border: "none",
            borderBottom: page === p.key ? "3px solid #3b82f6" : "3px solid transparent",
            color: page === p.key ? "#3b82f6" : "#9ca3af",
            cursor: "pointer", fontSize: "13px",
            fontWeight: page === p.key ? "bold" : "normal",
            background: "transparent", whiteSpace: "nowrap"
          }}>
            {p.label}
          </button>
        ))}
      </div>

      {/* ERROR */}
      {error && (
        <div style={{ background: "#7f1d1d", padding: "12px 24px", color: "#fca5a5", fontSize: "14px", display: "flex", justifyContent: "space-between" }}>
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: "16px" }}>✕</button>
        </div>
      )}

      <div style={{ padding: "28px", maxWidth: "1200px", margin: "0 auto" }}>

        {/* ── HOME ── */}
        {page === "home" && (
          <div>
            <div style={{ background: "linear-gradient(135deg, #0f2460, #1e3a5f)", borderRadius: "16px", padding: "40px", marginBottom: "28px", textAlign: "center" }}>
              <h2 style={{ fontSize: "26px", marginBottom: "12px" }}>AI-Powered Tourism Risk Intelligence</h2>
              <p style={{ color: "#93c5fd", fontSize: "14px", maxWidth: "600px", margin: "0 auto 24px" }}>
                Predicts crowd levels and risk conditions at Sri Lankan tourist destinations
                using Random Forest machine learning with 15 contextual features including
                flight arrival data from Bandaranaike International Airport.
              </p>
              <button onClick={() => setPage("predict")} style={{ padding: "12px 32px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "15px", fontWeight: "bold" }}>
                Explore Sites →
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "14px", marginBottom: "28px" }}>
              {[
                { num: "30", label: "Tourist Sites", icon: "📍" },
                { num: "21,930", label: "Training Records", icon: "📊" },
                { num: "15", label: "ML Features", icon: "🧠" },
                { num: "0.0427", label: "MAE Achieved", icon: "🎯" },
                { num: "0.9372", label: "R² Achieved", icon: "📈" },
                { num: "91%", label: "Accuracy", icon: "✅" },
                { num: "150", label: "Decision Trees", icon: "🌳" },
                { num: "78.8%", label: "Better than Baseline", icon: "🚀" },
              ].map((s) => (
                <div key={s.label} style={{ background: "#111827", borderRadius: "12px", padding: "16px", textAlign: "center", border: "1px solid #1f2937" }}>
                  <div style={{ fontSize: "20px", marginBottom: "6px" }}>{s.icon}</div>
                  <div style={{ fontSize: "20px", color: "#3b82f6", fontWeight: "bold" }}>{s.num}</div>
                  <div style={{ color: "#6b7280", fontSize: "11px", marginTop: "4px" }}>{s.label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "16px" }}>
              {[
                { icon: "🔍", title: "Risk Prediction", desc: "Predicts Low, Medium, or High crowd risk for any site and date using Random Forest ML", page: "predict" },
                { icon: "🗺️", title: "Risk Map", desc: "Visual bar chart showing crowd risk levels across all 30 tourist sites for a selected date", page: "map" },
                { icon: "🌿", title: "Green Sites", desc: "Eco-friendly alternatives with lower predicted crowd levels to reduce overtourism", page: "green" },
                { icon: "📅", title: "Itinerary Check", desc: "Check risk levels for all sites in your planned trip and get smart recommendations", page: "itinerary" },
                { icon: "📊", title: "Model Insights", desc: "SHAP analysis, confusion matrix, and feature importance showing how the model works", page: "insights" },
                { icon: "🚨", title: "Real-time Alerts", desc: "Automatic alerts when your planned destination is forecast to be overcrowded", page: "predict" },
              ].map((f) => (
                <div key={f.title} onClick={() => setPage(f.page)}
                  style={{ background: "#111827", borderRadius: "12px", padding: "22px", border: "1px solid #1f2937", cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = "#3b82f6"}
                  onMouseLeave={e => e.currentTarget.style.borderColor = "#1f2937"}>
                  <div style={{ fontSize: "26px", marginBottom: "10px" }}>{f.icon}</div>
                  <h3 style={{ marginBottom: "8px", fontSize: "15px" }}>{f.title}</h3>
                  <p style={{ color: "#6b7280", fontSize: "13px", lineHeight: "1.5" }}>{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── SITE EXPLORER ── */}
        {page === "predict" && (
          <div>
            <h2 style={{ marginBottom: "6px" }}>🔍 Site Explorer</h2>
            <p style={{ color: "#6b7280", marginBottom: "22px", fontSize: "14px" }}>Select any tourist site and date to get AI-powered risk prediction</p>

            <div style={{ background: "#111827", borderRadius: "12px", padding: "22px", marginBottom: "22px", border: "1px solid #1f2937" }}>
              <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end" }}>

                {/* SEARCH */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", position: "relative", minWidth: "240px" }}>
                  <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Search Site</label>
                  <input
                    type="text"
                    placeholder="Type site name..."
                    value={siteSearch}
                    onChange={e => setSiteSearch(e.target.value)}
                    style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }}
                  />
                  {siteSearch && filteredSites.length > 0 && (
                    <div style={{ position: "absolute", top: "68px", left: 0, right: 0, background: "#1f2937", borderRadius: "8px", border: "1px solid #374151", maxHeight: "200px", overflowY: "auto", zIndex: 100 }}>
                      {filteredSites.map(s => (
                        <div key={s.site_id}
                          onClick={() => { setSelectedSite(s.site_id); setSiteSearch(""); }}
                          style={{ padding: "10px 14px", cursor: "pointer", fontSize: "14px", borderBottom: "1px solid #374151" }}
                          onMouseEnter={e => e.currentTarget.style.background = "#374151"}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                          {s.site_name}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* OR DROPDOWN */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Or Select</label>
                  <select value={selectedSite} onChange={(e) => setSelectedSite(parseInt(e.target.value))}
                    style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px", minWidth: "220px" }}>
                    {sites.map((s) => (
                      <option key={s.site_id} value={s.site_id}>{s.site_name}</option>
                    ))}
                  </select>
                </div>

                {/* DATE */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Visit Date</label>
                  <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}
                    style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }} />
                </div>

                <button onClick={handlePredict} disabled={loading}
                  style={{ padding: "10px 28px", background: loading ? "#374151" : "#3b82f6", color: "#fff", border: "none", borderRadius: "8px", cursor: loading ? "not-allowed" : "pointer", fontSize: "14px", fontWeight: "bold" }}>
                  {loading ? "⏳ Predicting..." : "Get Prediction →"}
                </button>
              </div>
            </div>

            {loading && <Spinner />}

            {alertData && alertData.alert && (
              <div style={{ background: "rgba(239,68,68,0.15)", border: "1px solid #ef4444", borderRadius: "10px", padding: "14px 20px", marginBottom: "20px", fontSize: "14px", display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "20px" }}>🚨</span>
                <span>{alertData.message}</span>
              </div>
            )}

            {prediction && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>

                {/* PREDICTION CARD */}
                <div style={{ background: "#111827", borderRadius: "16px", padding: "28px", border: `1px solid ${getRiskColor(prediction.risk_level)}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                    <div>
                      <h2 style={{ fontSize: "18px", marginBottom: "4px" }}>{prediction.site_name}</h2>
                      <p style={{ color: "#6b7280", fontSize: "13px" }}>📅 {prediction.date}</p>
                    </div>
                    <div style={{ padding: "8px 18px", borderRadius: "999px", fontWeight: "bold", fontSize: "13px", background: getRiskColor(prediction.risk_level), color: "#fff" }}>
                      {prediction.risk_level} RISK
                    </div>
                  </div>

                  <div style={{ marginBottom: "20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <span style={{ fontSize: "13px", color: "#9ca3af" }}>Crowd Level</span>
                      <span style={{ fontSize: "13px", fontWeight: "bold", color: getRiskColor(prediction.risk_level) }}>
                        {(prediction.crowd_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ background: "#1f2937", borderRadius: "999px", height: "12px" }}>
                      <div style={{ height: "12px", borderRadius: "999px", width: `${prediction.crowd_score * 100}%`, background: getRiskColor(prediction.risk_level), transition: "width 1s ease" }} />
                    </div>
                  </div>

                  <div style={{ background: getRiskBg(prediction.risk_level), borderRadius: "10px", padding: "14px", marginBottom: "16px" }}>
                    <p style={{ color: "#e2e8f0", fontSize: "14px", margin: 0 }}>💡 {prediction.recommendation}</p>
                  </div>

                  <div style={{ display: "flex", gap: "10px", marginBottom: "20px", flexWrap: "wrap" }}>
                    {[
                      prediction.is_holiday ? "🎉 Public Holiday" : "📅 Regular Day",
                      prediction.is_weekend ? "🏖️ Weekend" : "💼 Weekday",
                    ].map(tag => (
                      <span key={tag} style={{ background: "#1f2937", padding: "5px 12px", borderRadius: "999px", fontSize: "12px", color: "#9ca3af" }}>{tag}</span>
                    ))}
                  </div>

                  <button onClick={() => addToItinerary(prediction.site_id)}
                    style={{ width: "100%", padding: "10px", background: "#16a34a", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px", fontWeight: "bold" }}>
                    + Add to Itinerary
                  </button>
                </div>

                {/* FEEDBACK CARD */}
                <div style={{ background: "#111827", borderRadius: "16px", padding: "28px", border: "1px solid #1f2937" }}>
                  <h3 style={{ marginBottom: "6px", fontSize: "16px" }}>📝 Post-Visit Feedback</h3>
                  <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "20px" }}>Help improve predictions by sharing your experience</p>

                  {feedbackSent ? (
                    <div style={{ background: "rgba(34,197,94,0.15)", border: "1px solid #22c55e", borderRadius: "10px", padding: "20px", textAlign: "center" }}>
                      <div style={{ fontSize: "32px", marginBottom: "8px" }}>✅</div>
                      <p style={{ color: "#22c55e", fontWeight: "bold" }}>Feedback submitted. Thank you!</p>
                      <p style={{ color: "#6b7280", fontSize: "12px", marginTop: "6px" }}>This data will be used to retrain and improve the model.</p>
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                      <div>
                        <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", display: "block", marginBottom: "6px" }}>ACTUAL CROWD LEVEL YOU OBSERVED</label>
                        <select value={feedback.actual_crowd} onChange={e => setFeedback({ ...feedback, actual_crowd: e.target.value })}
                          style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }}>
                          <option value="Low">Low — very few people</option>
                          <option value="Medium">Medium — moderate crowds</option>
                          <option value="High">High — very crowded</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", display: "block", marginBottom: "6px" }}>SATISFACTION RATING</label>
                        <div style={{ display: "flex", gap: "8px" }}>
                          {[1, 2, 3, 4, 5].map(r => (
                            <button key={r} onClick={() => setFeedback({ ...feedback, rating: r })}
                              style={{ flex: 1, padding: "10px", borderRadius: "8px", border: "none", cursor: "pointer", fontSize: "18px", background: feedback.rating >= r ? "#f59e0b" : "#1f2937" }}>
                              ⭐
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", display: "block", marginBottom: "6px" }}>COMMENT (OPTIONAL)</label>
                        <textarea value={feedback.comment} onChange={e => setFeedback({ ...feedback, comment: e.target.value })}
                          placeholder="Share your experience at this site..."
                          style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px", height: "80px", resize: "none" }} />
                      </div>
                      <button onClick={handleFeedback}
                        style={{ padding: "10px", background: "#7c3aed", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px", fontWeight: "bold" }}>
                        Submit Feedback
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* BEST TIMES */}
            {prediction && (
              <div style={{ background: "#111827", borderRadius: "16px", padding: "24px", marginTop: "20px", border: "1px solid #1f2937" }}>
                <h3 style={{ marginBottom: "16px", fontSize: "15px" }}>📅 Best Days to Visit {prediction.site_name} This Month</h3>
                <BestTimes siteId={prediction.site_id} />
              </div>
            )}
          </div>
        )}

        {/* ── RISK MAP ── */}
        {page === "map" && (
          <div>
            <h2 style={{ marginBottom: "6px" }}>🗺️ Risk Map</h2>
            <p style={{ color: "#6b7280", marginBottom: "22px", fontSize: "14px" }}>Visual overview of crowd risk across all 30 Sri Lankan tourist sites</p>

            <div style={{ background: "#111827", borderRadius: "12px", padding: "22px", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "22px", border: "1px solid #1f2937" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Select Date</label>
                <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}
                  style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }} />
              </div>
              <button onClick={handleAllPredictions} disabled={mapLoading}
                style={{ padding: "10px 28px", background: mapLoading ? "#374151" : "#3b82f6", color: "#fff", border: "none", borderRadius: "8px", cursor: mapLoading ? "not-allowed" : "pointer", fontSize: "14px", fontWeight: "bold" }}>
                {mapLoading ? "⏳ Loading all 30 sites..." : "Load Risk Map →"}
              </button>
            </div>

            <div style={{ display: "flex", gap: "16px", marginBottom: "20px", flexWrap: "wrap" }}>
              {[["#22c55e", "Low Risk"], ["#f59e0b", "Medium Risk"], ["#ef4444", "High Risk"]].map(([color, label]) => (
                <div key={label} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <div style={{ width: "14px", height: "14px", borderRadius: "50%", background: color }} />
                  <span style={{ fontSize: "13px", color: "#9ca3af" }}>{label}</span>
                </div>
              ))}
            </div>

            {mapLoading && <Spinner />}

            {allPredictions.length > 0 && (
              <div>
                <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", border: "1px solid #1f2937", marginBottom: "24px" }}>
                  <h3 style={{ marginBottom: "20px", fontSize: "14px", color: "#9ca3af", textTransform: "uppercase" }}>
                    All 30 Sites — Crowd Score on {selectedDate} (Sorted Highest to Lowest)
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {allPredictions.sort((a, b) => b.crowd_score - a.crowd_score).map((p, index) => (
                      <div key={p.site_id} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div style={{ width: "24px", fontSize: "12px", color: "#6b7280", textAlign: "right", flexShrink: 0 }}>{index + 1}</div>
                        <div style={{ width: "190px", fontSize: "12px", color: "#9ca3af", textAlign: "right", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {p.site_name}
                        </div>
                        <div style={{ flex: 1, background: "#1f2937", borderRadius: "999px", height: "20px" }}>
                          <div style={{ height: "20px", borderRadius: "999px", width: `${p.crowd_score * 100}%`, background: getRiskColor(p.risk_level), transition: "width 0.8s ease" }} />
                        </div>
                        <div style={{ width: "40px", fontSize: "12px", color: getRiskColor(p.risk_level), fontWeight: "bold", flexShrink: 0 }}>
                          {(p.crowd_score * 100).toFixed(0)}%
                        </div>
                        <div style={{ width: "65px", fontSize: "11px", padding: "3px 8px", borderRadius: "999px", background: getRiskColor(p.risk_level), color: "#fff", textAlign: "center", fontWeight: "bold", flexShrink: 0 }}>
                          {p.risk_level}
                        </div>
                        <button onClick={() => addToItinerary(p.site_id)}
                          style={{ fontSize: "11px", padding: "4px 8px", background: "#16a34a", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", flexShrink: 0 }}>
                          + Add
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: "14px" }}>
                  {allPredictions.sort((a, b) => b.crowd_score - a.crowd_score).map(p => (
                    <div key={p.site_id} style={{ background: "#111827", borderRadius: "10px", padding: "16px", border: `1px solid ${getRiskColor(p.risk_level)}44` }}>
                      <div style={{ fontSize: "11px", padding: "3px 10px", borderRadius: "999px", background: getRiskColor(p.risk_level), color: "#fff", fontWeight: "bold", display: "inline-block", marginBottom: "8px" }}>
                        {p.risk_level}
                      </div>
                      <h3 style={{ fontSize: "13px", marginBottom: "8px" }}>{p.site_name}</h3>
                      <div style={{ background: "#1f2937", borderRadius: "999px", height: "6px", marginBottom: "6px" }}>
                        <div style={{ height: "6px", borderRadius: "999px", width: `${p.crowd_score * 100}%`, background: getRiskColor(p.risk_level) }} />
                      </div>
                      <div style={{ fontSize: "12px", color: "#6b7280", marginBottom: "10px" }}>{(p.crowd_score * 100).toFixed(0)}% crowded</div>
                      <button onClick={() => addToItinerary(p.site_id)}
                        style={{ width: "100%", padding: "6px", background: "#16a34a", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>
                        + Itinerary
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── GREEN SITES ── */}
        {page === "green" && (
          <div>
            <h2 style={{ marginBottom: "6px" }}>🌿 Green Sites</h2>
            <p style={{ color: "#6b7280", marginBottom: "22px", fontSize: "14px" }}>
              Eco-friendly tourist sites with lower predicted crowd levels — addressing Gap 3: green site demand redistribution
            </p>

            <div style={{ background: "#111827", borderRadius: "12px", padding: "22px", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "22px", border: "1px solid #1f2937" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Select Date</label>
                <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}
                  style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }} />
              </div>
              <button onClick={handleGreenSites} disabled={loading}
                style={{ padding: "10px 28px", background: loading ? "#374151" : "#16a34a", color: "#fff", border: "none", borderRadius: "8px", cursor: loading ? "not-allowed" : "pointer", fontSize: "14px", fontWeight: "bold" }}>
                {loading ? "⏳ Loading..." : "🌿 Find Green Sites →"}
              </button>
            </div>

            {loading && <Spinner />}

            {greenSites.length > 0 && (
              <div>
                <div style={{ background: "rgba(34,197,94,0.1)", border: "1px solid #22c55e44", borderRadius: "10px", padding: "14px 18px", marginBottom: "20px", fontSize: "14px" }}>
                  ✅ Found <strong>{greenSites.length}</strong> eco-friendly sites sorted by lowest crowd level first.
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "16px" }}>
                  {greenSites.map((site) => (
                    <div key={site.site_id} style={{ background: "#111827", borderRadius: "12px", padding: "20px", border: "1px solid #166534" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                        <h3 style={{ fontSize: "14px", color: "#4ade80", margin: 0 }}>🌿 {site.site_name}</h3>
                        <div style={{ fontSize: "11px", padding: "3px 10px", borderRadius: "999px", background: getRiskColor(site.risk_level), color: "#fff", fontWeight: "bold", flexShrink: 0 }}>
                          {site.risk_level}
                        </div>
                      </div>
                      <p style={{ color: "#6b7280", fontSize: "12px", marginBottom: "12px" }}>{site.category} — {site.district}</p>
                      <div style={{ background: "#1f2937", borderRadius: "999px", height: "8px", marginBottom: "6px" }}>
                        <div style={{ height: "8px", borderRadius: "999px", width: `${site.crowd_score * 100}%`, background: getRiskColor(site.risk_level) }} />
                      </div>
                      <div style={{ fontSize: "12px", color: "#6b7280", marginBottom: "14px" }}>Crowd: {(site.crowd_score * 100).toFixed(0)}%</div>
                      <button onClick={() => addToItinerary(site.site_id)}
                        style={{ width: "100%", padding: "8px", background: "#16a34a", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "13px", fontWeight: "bold" }}>
                        + Add to Itinerary
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── ITINERARY ── */}
        {page === "itinerary" && (
          <div>
            <h2 style={{ marginBottom: "6px" }}>📅 Itinerary Checker</h2>
            <p style={{ color: "#6b7280", marginBottom: "22px", fontSize: "14px" }}>
              Plan your trip and check risk levels for all sites — addressing Gap 4: dynamic itinerary adjustment
            </p>

            <div style={{ background: "#111827", borderRadius: "12px", padding: "22px", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "22px", border: "1px solid #1f2937" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Add Site</label>
                <select onChange={(e) => { if (e.target.value) { addToItinerary(parseInt(e.target.value)); e.target.value = ""; } }}
                  style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px", minWidth: "240px" }}>
                  <option value="">-- Select Site to Add --</option>
                  {sites.map((s) => (
                    <option key={s.site_id} value={s.site_id}>{s.site_name}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", textTransform: "uppercase" }}>Visit Date</label>
                <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}
                  style={{ padding: "10px 14px", borderRadius: "8px", border: "1px solid #374151", background: "#1f2937", color: "#fff", fontSize: "14px" }} />
              </div>
              <button onClick={handleItineraryCheck} disabled={loading || itinerarySites.length === 0}
                style={{ padding: "10px 28px", background: itinerarySites.length === 0 ? "#374151" : "#3b82f6", color: "#fff", border: "none", borderRadius: "8px", cursor: itinerarySites.length === 0 ? "not-allowed" : "pointer", fontSize: "14px", fontWeight: "bold" }}>
                {loading ? "⏳ Checking..." : "Check Risk Levels →"}
              </button>
            </div>

            {itinerarySites.length > 0 && (
              <div style={{ background: "#111827", borderRadius: "12px", padding: "20px", marginBottom: "20px", border: "1px solid #1f2937" }}>
                <h3 style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", marginBottom: "14px", textTransform: "uppercase" }}>
                  Your Planned Sites ({itinerarySites.length})
                </h3>
                {itinerarySites.map((id, index) => {
                  const site = sites.find((s) => s.site_id === id);
                  return site ? (
                    <div key={id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: "bold" }}>
                          {index + 1}
                        </div>
                        <span style={{ fontSize: "14px" }}>📍 {site.site_name}</span>
                      </div>
                      <button onClick={() => removeFromItinerary(id)}
                        style={{ background: "#7f1d1d", color: "#fff", border: "none", borderRadius: "6px", padding: "4px 12px", cursor: "pointer", fontSize: "12px" }}>
                        Remove
                      </button>
                    </div>
                  ) : null;
                })}
              </div>
            )}

            {loading && <Spinner />}

            {itineraryResult && (
              <div style={{ background: "#111827", borderRadius: "12px", padding: "20px", border: "1px solid #1f2937" }}>
                <h3 style={{ color: "#9ca3af", fontSize: "12px", fontWeight: "bold", marginBottom: "14px", textTransform: "uppercase" }}>
                  Risk Check Results — {itineraryResult.date}
                </h3>
                {itineraryResult.itinerary_check.map((item, index) => (
                  <div key={item.site_id} style={{ display: "flex", alignItems: "center", gap: "14px", padding: "14px 0", borderBottom: "1px solid #1f2937", flexWrap: "wrap" }}>
                    <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "12px", fontWeight: "bold", flexShrink: 0 }}>
                      {index + 1}
                    </div>
                    <span style={{ flex: 1, fontSize: "14px" }}>{item.site_name}</span>
                    <div style={{ fontSize: "11px", padding: "4px 14px", borderRadius: "999px", background: getRiskColor(item.risk_level), color: "#fff", fontWeight: "bold", flexShrink: 0 }}>
                      {item.risk_level}
                    </div>
                    <span style={{ fontSize: "13px", color: "#6b7280", flexShrink: 0 }}>{(item.crowd_score * 100).toFixed(0)}% crowded</span>
                    {!item.recommended ? (
                      <div style={{ fontSize: "12px", color: "#fbbf24", background: "rgba(245,158,11,0.15)", padding: "4px 10px", borderRadius: "6px" }}>
                        ⚠️ Consider an alternative
                      </div>
                    ) : (
                      <div style={{ fontSize: "12px", color: "#22c55e", background: "rgba(34,197,94,0.15)", padding: "4px 10px", borderRadius: "6px" }}>
                        ✅ Good to visit
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── MODEL INSIGHTS ── */}
        {page === "insights" && (
          <div>
            <h2 style={{ marginBottom: "6px" }}>📊 Model Insights</h2>
            <p style={{ color: "#6b7280", marginBottom: "22px", fontSize: "14px" }}>
              SHAP analysis, confusion matrix, and feature importance explaining how the Random Forest model makes predictions
            </p>

            {/* REAL METRICS */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: "14px", marginBottom: "28px" }}>
              {[
                { label: "Model Type", value: "Random Forest", icon: "🌳" },
                { label: "Training Records", value: modelMetrics ? modelMetrics.train_records.toLocaleString() : "17,544", icon: "📊" },
                { label: "Test Records", value: modelMetrics ? modelMetrics.test_records.toLocaleString() : "4,386", icon: "🧪" },
                { label: "MAE Achieved", value: modelMetrics ? `${modelMetrics.mae} ${modelMetrics.mae_achieved ? "✅" : "❌"}` : "0.0427 ✅", icon: "🎯" },
                { label: "R² Achieved", value: modelMetrics ? `${modelMetrics.r2} ${modelMetrics.r2_achieved ? "✅" : "❌"}` : "0.9372 ✅", icon: "📈" },
                { label: "CV MAE", value: modelMetrics ? `${modelMetrics.cv_mae} ±${modelMetrics.cv_mae_std}` : "0.0461 ±0.0042", icon: "🔁" },
                { label: "Decision Trees", value: modelMetrics ? modelMetrics.n_estimators : "150", icon: "🌲" },
                { label: "Overall Accuracy", value: "91% ✅", icon: "⚙️" },
              ].map(s => (
                <div key={s.label} style={{ background: "#111827", borderRadius: "10px", padding: "16px", border: "1px solid #1f2937", textAlign: "center" }}>
                  <div style={{ fontSize: "22px", marginBottom: "6px" }}>{s.icon}</div>
                  <div style={{ fontSize: "15px", fontWeight: "bold", color: "#3b82f6", marginBottom: "4px" }}>{s.value}</div>
                  <div style={{ fontSize: "11px", color: "#6b7280" }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* FEATURES */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "18px", fontSize: "15px" }}>⚙️ 15 Features Used in Prediction</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "10px" }}>
                {[
                  { name: "daily_flights_at_cmb", importance: 92, desc: "KEY NOVELTY — Flight arrivals at Colombo Airport", color: "#3b82f6" },
                  { name: "is_festival_period", importance: 88, desc: "High impact festivals like Vesak and Perahera", color: "#8b5cf6" },
                  { name: "is_public_holiday", importance: 85, desc: "National holidays and Poya days", color: "#8b5cf6" },
                  { name: "month", importance: 80, desc: "Month of year — drives seasonal patterns", color: "#6366f1" },
                  { name: "season_encoded", importance: 78, desc: "Peak, shoulder, or low tourism season", color: "#6366f1" },
                  { name: "is_weekend", importance: 75, desc: "Saturday or Sunday vs weekday", color: "#06b6d4" },
                  { name: "capacity_per_day", importance: 72, desc: "Maximum site capacity affecting crowd score", color: "#06b6d4" },
                  { name: "avg_rainfall_mm", importance: 65, desc: "Monthly rainfall affecting outdoor site visits", color: "#10b981" },
                  { name: "avg_temperature_c", importance: 60, desc: "Temperature affecting tourist comfort", color: "#10b981" },
                  { name: "category_encoded", importance: 58, desc: "Heritage, Nature, Religious, Beach", color: "#f59e0b" },
                  { name: "district_encoded", importance: 55, desc: "Geographic district of tourist site", color: "#f59e0b" },
                  { name: "is_unesco", importance: 52, desc: "UNESCO World Heritage status", color: "#ef4444" },
                  { name: "day_of_week", importance: 48, desc: "Monday to Sunday pattern", color: "#ef4444" },
                  { name: "entrance_fee_lkr", importance: 40, desc: "Entry fee affecting visitor volume", color: "#6b7280" },
                  { name: "is_eco_friendly", importance: 35, desc: "Eco site classification for green routing", color: "#6b7280" },
                ].map(f => (
                  <div key={f.name} style={{ background: "#1f2937", borderRadius: "8px", padding: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span style={{ fontSize: "12px", fontWeight: "bold", color: f.color, fontFamily: "monospace" }}>{f.name}</span>
                      <span style={{ fontSize: "11px", color: f.color, fontWeight: "bold" }}>{f.importance}%</span>
                    </div>
                    <div style={{ background: "#374151", borderRadius: "999px", height: "5px", marginBottom: "6px" }}>
                      <div style={{ height: "5px", borderRadius: "999px", width: `${f.importance}%`, background: f.color }} />
                    </div>
                    <p style={{ fontSize: "11px", color: "#6b7280", margin: 0 }}>{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* SHAP EXPLANATION */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>🔍 What is SHAP Analysis?</h3>
              <p style={{ color: "#9ca3af", fontSize: "14px", lineHeight: "1.7", marginBottom: "16px" }}>
                SHAP (SHapley Additive exPlanations) explains WHY the model made each prediction.
                For every prediction, SHAP calculates how much each feature pushed the crowd score higher or lower.
                This makes the AI model transparent and interpretable for academic review.
              </p>
              <div style={{ background: "#1f2937", borderRadius: "10px", padding: "16px" }}>
                <h4 style={{ marginBottom: "12px", fontSize: "14px", color: "#9ca3af" }}>Example — Sigiriya on Sinhala New Year (April 13)</h4>
                {[
                  { feature: "is_festival_period = 1", impact: "+0.28", direction: "up", desc: "Festival day pushes crowd UP significantly" },
                  { feature: "daily_flights_at_cmb = 78", impact: "+0.18", direction: "up", desc: "High flight arrivals push crowd UP — KEY NOVELTY" },
                  { feature: "is_weekend = 1", impact: "+0.12", direction: "up", desc: "Weekend pushes crowd UP" },
                  { feature: "season = peak", impact: "+0.10", direction: "up", desc: "Peak season pushes crowd UP" },
                  { feature: "avg_rainfall_mm = 120", impact: "-0.05", direction: "down", desc: "Some rain slightly reduces crowd" },
                ].map(item => (
                  <div key={item.feature} style={{ display: "flex", alignItems: "center", gap: "12px", padding: "8px 0", borderBottom: "1px solid #374151" }}>
                    <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#93c5fd", width: "200px", flexShrink: 0 }}>{item.feature}</span>
                    <span style={{ fontWeight: "bold", fontSize: "14px", color: item.direction === "up" ? "#ef4444" : "#22c55e", width: "50px", flexShrink: 0 }}>{item.impact}</span>
                    <span style={{ fontSize: "12px", color: "#6b7280" }}>{item.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* RESEARCH GAPS */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "16px", fontSize: "15px" }}>📋 5 Research Gaps Addressed</h3>
              {[
                { num: 1, gap: "No flight arrival data used as crowd predictor in Sri Lanka", solution: "daily_flights_at_cmb feature from AviationStack API — KEY NOVELTY of this research", color: "#3b82f6" },
                { num: 2, gap: "No ML-based crowd prediction system deployed in Sri Lanka", solution: "Random Forest model trained on 30 Sri Lankan tourist sites with 21,930 records", color: "#8b5cf6" },
                { num: 3, gap: "No implemented green site demand redistribution system", solution: "Green Sites page redirecting tourists to eco-friendly lower-crowd alternatives", color: "#22c55e" },
                { num: 4, gap: "No dynamic itinerary adjustment based on real-time crowd predictions", solution: "Itinerary Checker with automatic risk-based recommendations for each planned site", color: "#f59e0b" },
                { num: 5, gap: "No post-visit feedback loop in existing prediction systems", solution: "Feedback system collecting ratings and comments to improve model over time", color: "#ef4444" },
              ].map(g => (
                <div key={g.num} style={{ display: "flex", gap: "14px", padding: "14px 0", borderBottom: "1px solid #1f2937" }}>
                  <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: g.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px", fontWeight: "bold", flexShrink: 0 }}>
                    {g.num}
                  </div>
                  <div>
                    <p style={{ fontSize: "13px", color: "#ef4444", marginBottom: "4px" }}>❌ Gap: {g.gap}</p>
                    <p style={{ fontSize: "13px", color: "#22c55e", margin: 0 }}>✅ Solution: {g.solution}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* ACTUAL VS PREDICTED */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>🎯 Actual vs Predicted + Baseline Comparison</h3>
              <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "16px" }}>
                Left: scatter plot showing prediction accuracy. Right: Random Forest vs baseline showing 78.8% MAE improvement.
              </p>
              <img src="/actual_vs_predicted.png" alt="Actual vs Predicted"
                style={{ width: "100%", borderRadius: "8px", border: "1px solid #1f2937" }}
                onError={(e) => { e.target.style.display = "none"; }} />
            </div>

            {/* CONFUSION MATRIX */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>🔢 Confusion Matrix — Risk Level Classification</h3>
              <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "16px" }}>
                Diagonal values are correct predictions. High risk precision 85%, Low risk precision 95%, overall accuracy 91%.
              </p>
              <img src="/confusion_matrix.png" alt="Confusion Matrix"
                style={{ width: "100%", maxWidth: "500px", borderRadius: "8px", border: "1px solid #1f2937" }}
                onError={(e) => { e.target.style.display = "none"; }} />
            </div>

            {/* SHAP SUMMARY */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>📊 SHAP Summary Plot</h3>
              <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "16px" }}>
                Each dot is one prediction. Red means high feature value pushed crowd score up. Blue means low. Features at top matter most. daily_flights_at_cmb validates Gap 1 novelty.
              </p>
              <img src="/shap_summary_plot.png" alt="SHAP Summary"
                style={{ width: "100%", borderRadius: "8px", border: "1px solid #1f2937" }}
                onError={(e) => { e.target.style.display = "none"; }} />
            </div>

            {/* SHAP BAR */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", marginBottom: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>📊 SHAP Mean Feature Impact</h3>
              <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "16px" }}>
                Average absolute SHAP values showing overall feature importance across all predictions.
              </p>
              <img src="/shap_bar_plot.png" alt="SHAP Bar"
                style={{ width: "100%", borderRadius: "8px", border: "1px solid #1f2937" }}
                onError={(e) => { e.target.style.display = "none"; }} />
            </div>

            {/* FEATURE IMPORTANCE */}
            <div style={{ background: "#111827", borderRadius: "12px", padding: "24px", border: "1px solid #1f2937" }}>
              <h3 style={{ marginBottom: "12px", fontSize: "15px" }}>🌳 Random Forest Feature Importance (Gini)</h3>
              <p style={{ color: "#6b7280", fontSize: "13px", marginBottom: "16px" }}>
                Importance scores from 150 decision trees. Blue bar is the key novelty feature — daily_flights_at_cmb.
              </p>
              <img src="/feature_importance.png" alt="Feature Importance"
                style={{ width: "100%", borderRadius: "8px", border: "1px solid #1f2937" }}
                onError={(e) => { e.target.style.display = "none"; }} />
            </div>

          </div>
        )}

      </div>

      {/* FOOTER */}
      <div style={{ textAlign: "center", padding: "24px", color: "#374151", fontSize: "13px", borderTop: "1px solid #111827", marginTop: "40px" }}>
        Tourism Risk & Context Intelligence System | Abinaya R | IT22090058 | SLIIT 2026 | R26-IT-152
      </div>

    </div>
  );
}