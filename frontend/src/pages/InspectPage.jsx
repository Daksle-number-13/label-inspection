import { useState } from "react";
import CameraCapture from "../components/CameraCapture";
import InspectionResult from "../components/InspectionResult";
import NotificationModal from "../components/NotificationModal";
import { inspectLabel } from "../services/api";

const STEPS = { CAPTURE: "capture", LOADING: "loading", RESULT: "result" };

export default function InspectPage() {
  const [step, setStep] = useState(STEPS.CAPTURE);
  const [imageFile, setImageFile] = useState(null);
  const [inspector, setInspector] = useState("");
  const [productInfo, setProductInfo] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);

  async function handleInspect() {
    if (!imageFile) {
      setError("라벨 이미지를 먼저 선택해 주세요.");
      return;
    }
    setError("");
    setStep(STEPS.LOADING);
    try {
      const data = await inspectLabel({
        file: imageFile,
        inspector: inspector || "검사자",
        productInfo,
        sendAlert: false,
      });
      setResult(data);
      setStep(STEPS.RESULT);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "검사 중 오류 발생";
      setError(msg);
      setStep(STEPS.CAPTURE);
    }
  }

  function handleReset() {
    setStep(STEPS.CAPTURE);
    setImageFile(null);
    setResult(null);
    setError("");
  }

  return (
    <div>
      {step === STEPS.CAPTURE && (
        <>
          {/* 검사자 정보 */}
          <div className="card">
            <div className="card-title">검사 정보</div>
            <div className="form-group">
              <label className="form-label">검사자 이름</label>
              <input
                className="form-input"
                placeholder="홍길동"
                value={inspector}
                onChange={(e) => setInspector(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">제품 정보 메모 (선택)</label>
              <input
                className="form-input"
                placeholder="예: 제품코드, 로트번호 등"
                value={productInfo}
                onChange={(e) => setProductInfo(e.target.value)}
              />
            </div>
          </div>

          {/* 카메라 */}
          <div className="card">
            <div className="card-title">라벨 이미지</div>
            <CameraCapture onImageSelected={setImageFile} />
          </div>

          {error && (
            <div style={{
              color: "#dc2626", fontSize: ".88rem", marginBottom: 12,
              padding: "10px 14px", background: "#fef2f2", borderRadius: 8
            }}>
              ⚠ {error}
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleInspect}
            disabled={!imageFile}
          >
            검사 시작
          </button>
        </>
      )}

      {step === STEPS.LOADING && (
        <div className="empty-state">
          <div style={{ fontSize: "2.5rem", marginBottom: 12 }}>🔍</div>
          <div style={{ fontWeight: 600, fontSize: "1rem", marginBottom: 8 }}>
            AI 검사 중...
          </div>
          <div>라벨 텍스트 인식 및 기준값 대조 중입니다.<br />잠시만 기다려 주세요.</div>
        </div>
      )}

      {step === STEPS.RESULT && result && (
        <>
          <InspectionResult result={result} />

          {/* 불량 처리 버튼 */}
          {result.overall === "fail" && (
            <button
              className="btn btn-danger"
              style={{ marginBottom: 10 }}
              onClick={() => setShowModal(true)}
            >
              불량 처리 — 파트장 알림 발송
            </button>
          )}

          <button className="btn btn-outline" onClick={handleReset}>
            새 검사 시작
          </button>

          {showModal && (
            <NotificationModal
              defects={result.defects}
              inspector={result.summary.inspector}
              productInfo={result.summary.product_info}
              onClose={() => setShowModal(false)}
            />
          )}
        </>
      )}
    </div>
  );
}
