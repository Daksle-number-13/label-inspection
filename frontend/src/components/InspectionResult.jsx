export default function InspectionResult({ result }) {
  const { overall, summary, results, defects } = result;

  return (
    <div>
      {/* 판정 배너 */}
      <div className={`result-banner ${overall}`}>
        <span className="result-banner-icon">{overall === "pass" ? "✅" : "❌"}</span>
        <div>
          <div>{overall === "pass" ? "합격 (PASS)" : "불량 (FAIL)"}</div>
          <div style={{ fontSize: ".85rem", fontWeight: 400, opacity: .85 }}>
            {summary.inspector} · {summary.product_info || "제품정보 미입력"}
          </div>
        </div>
      </div>

      {/* 요약 수치 */}
      <div className="summary-grid">
        <div className="summary-item">
          <div className="summary-num">{summary.total}</div>
          <div className="summary-label">전체 항목</div>
        </div>
        <div className="summary-item pass">
          <div className="summary-num">{summary.pass}</div>
          <div className="summary-label">합격</div>
        </div>
        <div className="summary-item fail">
          <div className="summary-num">{summary.fail}</div>
          <div className="summary-label">불량</div>
        </div>
      </div>

      {/* 항목별 결과 */}
      <div className="card">
        <div className="card-title">항목별 대조 결과</div>
        {results.map((item, i) => (
          <div key={i} className={`result-row ${item.status}`}>
            <div className="result-field">{item.field}</div>
            <div className="result-values">
              <div className="result-expected">
                기준: <span>{item.expected || "—"}</span>
              </div>
              <div className={`result-found ${item.status === "pass" ? "match" : "mismatch"}`}>
                {item.status === "pass"
                  ? `✓ ${item.expected}`
                  : `✗ ${item.found || "미확인"}`}
              </div>
              {item.context && item.status === "fail" && (
                <div style={{ fontSize: ".78rem", color: "#6b7280", marginTop: 2 }}>
                  인식: "{item.context}"
                </div>
              )}
            </div>
            <span className={`badge badge-${item.status}`}>
              {item.status === "pass" ? "OK" : "NG"}
            </span>
          </div>
        ))}
      </div>

      {/* OCR 원본 텍스트 */}
      <details className="card" style={{ cursor: "pointer" }}>
        <summary className="card-title" style={{ cursor: "pointer", marginBottom: 0 }}>
          OCR 인식 원본 텍스트 보기
        </summary>
        <pre style={{
          marginTop: 10,
          fontSize: ".82rem",
          color: "#374151",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
          background: "#f9fafb",
          padding: 10,
          borderRadius: 8,
          lineHeight: 1.6
        }}>
          {result.ocr?.full_text || "(텍스트 없음)"}
        </pre>
      </details>
    </div>
  );
}
