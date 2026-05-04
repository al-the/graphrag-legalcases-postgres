import React from "react";

const SOURCES = [
  { name: "Hansard Malaysia", desc: "Parliamentary debates (Dewan Rakyat & Dewan Negara)", flag: "🇲🇾" },
  { name: "Bursa Malaysia", desc: "Annual reports & financial disclosures", flag: "📈" },
  { name: "DOSM", desc: "Department of Statistics Malaysia publications", flag: "📊" },
  { name: "Bank Negara Malaysia", desc: "Monetary policy & financial regulations", flag: "🏦" },
  { name: "OECD", desc: "Malaysia-related policy & economic reports", flag: "🌐" },
  { name: "FATF", desc: "Anti-money laundering evaluation reports", flag: "🔒" },
];

const FEATURES = [
  {
    icon: "🔗",
    title: "Knowledge Graph",
    desc: "Entities, relationships, and communities extracted from every document using Microsoft GraphRAG.",
  },
  {
    icon: "🔍",
    title: "Semantic Search",
    desc: "Vector-powered search across all document chunks with pgvector and OpenAI embeddings.",
  },
  {
    icon: "📄",
    title: "Paste Any PDF URL",
    desc: "Drop a URL from any Malaysian agency or international body — we download, OCR, and index it automatically.",
  },
  {
    icon: "🤖",
    title: "Agentic Ingestion",
    desc: "LangGraph workflows automate bulk ingestion: discover → OCR → extract entities → update graph.",
  },
];

export function LandingPage({ onLogin, onRegister }: { onLogin: () => void; onRegister: () => void }) {
  return (
    <div style={styles.page}>
      {/* Hero */}
      <section style={styles.hero}>
        <h1 style={styles.heroTitle}>Malaysian Knowledge Graph</h1>
        <p style={styles.heroSub}>
          A unified knowledge graph over Malaysian parliamentary, financial, statistical, and regulatory documents — powered by GraphRAG.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <button onClick={onRegister} style={styles.primaryBtn}>Get Started</button>
          <button onClick={onLogin} style={styles.secondaryBtn}>Sign In</button>
        </div>
      </section>

      {/* Sources */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Document Sources</h2>
        <div style={styles.grid}>
          {SOURCES.map((s) => (
            <div key={s.name} style={styles.card}>
              <span style={{ fontSize: 28 }}>{s.flag}</span>
              <h3 style={styles.cardTitle}>{s.name}</h3>
              <p style={styles.cardDesc}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section style={styles.section}>
        <h2 style={styles.sectionTitle}>Features</h2>
        <div style={styles.grid}>
          {FEATURES.map((f) => (
            <div key={f.title} style={styles.card}>
              <span style={{ fontSize: 28 }}>{f.icon}</span>
              <h3 style={styles.cardTitle}>{f.title}</h3>
              <p style={styles.cardDesc}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section style={{ ...styles.section, maxWidth: 700, margin: "0 auto 80px" }}>
        <h2 style={styles.sectionTitle}>How to Add a Document</h2>
        <ol style={styles.steps}>
          <li style={styles.step}>Sign up and log in.</li>
          <li style={styles.step}>Go to <strong>Documents</strong> and paste any public PDF URL.</li>
          <li style={styles.step}>The system downloads the PDF, runs OCR (marker-pdf / Azure DI / Google Doc AI), and extracts entities.</li>
          <li style={styles.step}>Open <strong>Graph Explorer</strong> to visualise and explore the knowledge graph.</li>
        </ol>
      </section>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { background: "#0f172a", color: "#e2e8f0", minHeight: "100vh", fontFamily: "system-ui, sans-serif" },
  hero: { textAlign: "center", padding: "80px 24px 60px" },
  heroTitle: { fontSize: 48, fontWeight: 800, margin: "0 0 16px", background: "linear-gradient(135deg,#818cf8,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" },
  heroSub: { fontSize: 18, color: "#94a3b8", maxWidth: 600, margin: "0 auto 32px" },
  primaryBtn: { padding: "12px 28px", borderRadius: 10, border: "none", background: "#6366f1", color: "#fff", fontWeight: 700, fontSize: 16, cursor: "pointer" },
  secondaryBtn: { padding: "12px 28px", borderRadius: 10, border: "1px solid #334155", background: "transparent", color: "#e2e8f0", fontWeight: 600, fontSize: 16, cursor: "pointer" },
  section: { padding: "40px 24px" },
  sectionTitle: { textAlign: "center", fontSize: 28, fontWeight: 700, marginBottom: 32, color: "#f1f5f9" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 20, maxWidth: 1100, margin: "0 auto" },
  card: { background: "#1e293b", borderRadius: 12, padding: 24, display: "flex", flexDirection: "column", gap: 8 },
  cardTitle: { margin: 0, fontSize: 16, fontWeight: 700 },
  cardDesc: { margin: 0, fontSize: 13, color: "#94a3b8", lineHeight: 1.5 },
  steps: { paddingLeft: 24 },
  step: { fontSize: 15, lineHeight: 1.7, color: "#94a3b8" },
};
