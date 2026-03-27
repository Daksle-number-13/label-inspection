import { useState } from "react";
import { sendAlert } from "../services/api";

export default function NotificationModal({ defects, inspector, productInfo, onClose }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function handleSend() {
    setSending(true);
    setError("");
    try {
      const result = await sendAlert({ defects, inspector, productInfo });
      if (result.success) {
        setSent(true);
      } else {
        setError(result.message || "발송 실패");
      }
    } catch (e) {
      setError("네트워크 오류 — 발송 실패");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">❌ 불량 처리 — 파트장 알림</div>

        {sent ? (
          <div>
            <div className="modal-body" style={{ color: "#16a34a", fontWeight: 600 }}>
              ✅ 카카오 알림톡 발송 완료!<br />
              파트장에게 {defects.length}건 불량 내용이 전송되었습니다.
            </div>
            <button className="btn btn-primary" onClick={onClose}>닫기</button>
          </div>
        ) : (
          <div>
            <div className="modal-body">
              <strong>불량 항목 {defects.length}건</strong>을 파트장에게<br />
              카카오 알림톡으로 발송합니다.
              <ul style={{ marginTop: 10, paddingLeft: 16 }}>
                {defects.map((d, i) => (
                  <li key={i} style={{ marginBottom: 4 }}>
                    <strong>{d.field}</strong>: 기준[{d.expected}] / 실제[{d.found || "미확인"}]
                  </li>
                ))}
              </ul>
            </div>

            {error && (
              <div style={{
                color: "#dc2626", fontSize: ".88rem",
                marginBottom: 12, padding: "8px 12px",
                background: "#fef2f2", borderRadius: 8
              }}>
                ⚠ {error}
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-outline" onClick={onClose} disabled={sending}>
                취소
              </button>
              <button className="btn btn-danger" onClick={handleSend} disabled={sending}>
                {sending ? <><span className="spinner" />발송 중...</> : "알림톡 발송"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
