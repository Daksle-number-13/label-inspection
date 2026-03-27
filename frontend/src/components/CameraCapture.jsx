import { useRef, useState } from "react";

export default function CameraCapture({ onImageSelected }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);

  function handleChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    onImageSelected(file);
  }

  function handleClick() {
    inputRef.current?.click();
  }

  function handleReset(e) {
    e.stopPropagation();
    setPreview(null);
    onImageSelected(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="camera-input"
        onChange={handleChange}
      />

      {preview ? (
        <div className="camera-area has-image" onClick={handleClick}>
          <img src={preview} alt="라벨 미리보기" className="camera-preview" />
        </div>
      ) : (
        <div className="camera-area" onClick={handleClick}>
          <div className="camera-icon">📷</div>
          <p className="camera-text">
            터치하여 라벨 촬영 또는 이미지 선택
          </p>
        </div>
      )}

      {preview && (
        <button className="btn btn-outline btn-sm" style={{ marginTop: 8 }} onClick={handleReset}>
          다시 촬영
        </button>
      )}
    </div>
  );
}
