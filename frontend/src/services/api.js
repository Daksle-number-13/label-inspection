import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

const client = axios.create({ baseURL: BASE_URL });

/** 라벨 이미지 검사 */
export async function inspectLabel({ file, inspector, productInfo, sendAlert }) {
  const form = new FormData();
  form.append("file", file);
  form.append("inspector", inspector || "검사자");
  form.append("product_info", productInfo || "");
  form.append("send_alert", sendAlert ? "true" : "false");
  const { data } = await client.post("/inspect/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/** 불량 알림톡 수동 발송 */
export async function sendAlert({ defects, inspector, productInfo }) {
  const { data } = await client.post("/inspect/alert", {
    defects,
    inspector,
    product_info: productInfo,
  });
  return data;
}

/** 기준값 목록 조회 */
export async function getStandards() {
  const { data } = await client.get("/standards/");
  return data;
}

/** 기준값 강제 갱신 */
export async function refreshStandards() {
  const { data } = await client.post("/standards/refresh");
  return data;
}

/** 헬스 체크 */
export async function healthCheck() {
  const { data } = await client.get("/health");
  return data;
}
