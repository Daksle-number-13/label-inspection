import { useState, useEffect } from "react";
import { getStandards, refreshStandards } from "../services/api";

export default function SettingsPage() {
  const [standards, setStandards] = useState([]);
  const [cacheInfo, setCacheInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    load(false);
  }, []);

  async function load(forceRefresh) {
    setLoading(true);
    try {
      const fn = forceRefresh ? refreshStandards : getStandards;
      const data = await fn();
      setStandards(data.standards || []);
      setCacheInfo(data.cache || null);
      if (forceRefresh) showToast(`기준값 갱신 완료 (${data.standards?.length ?? 0}개 항목)`);
    } catch (e) {
      showToast("기준값 로드 실패 — 서버 연결을 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  }

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  function formatTime(ts) {
    if (!ts) return "—";
    return new Date(ts * 1000).toLocaleString("ko-KR");
  }

  return (
    <div>
      {/* 캐시 상태 */}
      {cacheInfo && (
        <div className="card">
          <div className="card-title">기준값 캐시 상태</div>
          <div style={{ fontSize: ".88rem", color: "#374151", lineHeight: 1.8 }}>
            <div>항목 수: <strong>{cacheInfo.count}개</strong></div>
            <div>갱신 시각: <strong>{formatTime(cacheInfo.loaded_at)}</strong></div>
            <div>
              캐시 상태:{" "}
              <strong style={{ color: cacheInfo.valid ? "#16a34a" : "#dc2626" }}>
                {cacheInfo.valid ? `유효 (${cacheInfo.ttl_remaining}초 후 만료)` : "만료됨"}
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* 갱신 버튼 */}
      <button
        className="btn btn-primary"
        style={{ marginBottom: 14 }}
        onClick={() => load(true)}
        disabled={loading}
      >
        {loading
          ? <><span className="spinner" /> 갱신 중...</>
          : "🔄 기준값 갱신 (클라우디아크)"}
      </button>

      {/* 기준값 목록 */}
      <div className="card">
        <div className="card-title">현재 기준값 목록</div>
        {standards.length === 0 ? (
          <div className="empty-state" style={{ padding: "24px 0" }}>
            {loading
              ? "로드 중..."
              : "기준값이 없습니다.\n위 버튼을 눌러 클라우디아크에서 불러오세요."}
          </div>
        ) : (
          standards.map((std, i) => (
            <div key={i} className="standard-row">
              <span className="std-field">{std.field}</span>
              <span className="std-value">{std.expected || "—"}</span>
              {std.notes && <span className="std-notes">{std.notes}</span>}
            </div>
          ))
        )}
      </div>

      {/* 사용 안내 */}
      <div className="card" style={{ background: "#eff6ff", border: "1px solid #bfdbfe" }}>
        <div className="card-title" style={{ color: "#1e40af" }}>엑셀 파일 형식 안내</div>
        <div style={{ fontSize: ".85rem", color: "#1e3a8a", lineHeight: 1.8 }}>
          클라우디아크 공유링크의 엑셀 파일은<br />
          아래 컬럼 형식을 따라주세요:<br />
          <br />
          <strong>A열</strong>: 검사항목 (예: 제품코드)<br />
          <strong>B열</strong>: 기준값 (예: ABC-1234)<br />
          <strong>C열</strong>: 비고 (선택)<br />
          <br />
          1행은 헤더로 자동 인식하여 건너뜁니다.
        </div>
      </div>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
