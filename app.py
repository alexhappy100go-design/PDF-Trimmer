import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile

# ── 頁面設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="PDF 批次裁切工具",
    page_icon="✂️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }

.hero {
    background: linear-gradient(135deg, #1a1f2e 0%, #0f1117 100%);
    border: 1px solid #2a2f3e;
    border-radius: 16px;
    padding: 2rem 2rem 1.6rem;
    margin-bottom: 1.8rem;
    text-align: center;
}
.hero h1 { font-size: 1.9rem; font-weight: 700; color: #f0f4ff; margin: 0 0 0.4rem; }
.hero p  { color: #8892a4; font-size: 0.92rem; margin: 0; }

.step-label {
    font-size: 0.75rem; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
    color: #4f8ef7; margin-bottom: 0.4rem;
}

.file-row {
    display: flex; align-items: center; justify-content: space-between;
    background: #1a1f2e; border: 1px solid #2a2f3e;
    border-radius: 8px; padding: 0.6rem 1rem;
    margin-bottom: 0.4rem; font-size: 0.88rem; color: #c8d0e0;
}
.file-row .name  { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-row .badge {
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
    background: #2a2f3e; color: #8892a4;
    padding: 2px 8px; border-radius: 4px; margin-left: 8px; white-space: nowrap;
}
.file-row .badge.blue  { background: #1e3a5f; color: #4f8ef7; }
.file-row .badge.green { background: #0d3028; color: #3ecf8e; }
.file-row .badge.warn  { background: #3d2a00; color: #f5a623; }

.summary-box {
    background: #0d1a0f; border: 1px solid #1e4d2a;
    border-radius: 10px; padding: 1rem 1.2rem;
    color: #3ecf8e; font-size: 0.9rem; margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div style="font-size:2.5rem;margin-bottom:0.4rem">✂️</div>
  <h1>PDF 批次裁切工具</h1>
  <p>一次上傳多個 PDF，統一裁切頁數，打包 ZIP 下載</p>
</div>
""", unsafe_allow_html=True)

# ── STEP 1：上傳 ──────────────────────────────────────────
st.markdown('<div class="step-label">Step 1 — 上傳 PDF（可多選）</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    label="拖曳或點擊上傳，支援同時選取多個 PDF",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    file_infos = []
    for f in uploaded_files:
        data = f.read()
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
            status = "ok"
        except Exception:
            pages = 0
            status = "error"
        file_infos.append({
            "file": f,
            "data": data,
            "pages": pages,
            "size_kb": round(len(data) / 1024, 1),
            "status": status,
        })

    total_files = len(file_infos)
    valid_files = [f for f in file_infos if f["status"] == "ok"]
    max_pages = max((f["pages"] for f in valid_files), default=1)

    with st.expander(f"📋 查看檔案清單（{total_files} 個）", expanded=total_files <= 10):
        rows_html = ""
        for info in file_infos:
            name = info["file"].name
            if info["status"] == "error":
                badge = '<span class="badge warn">⚠ 無法讀取</span>'
            else:
                badge = f'<span class="badge blue">{info["pages"]} 頁</span><span class="badge">{info["size_kb"]} KB</span>'
            rows_html += f'<div class="file-row"><span class="name">📄 {name}</span>{badge}</div>'
        st.markdown(rows_html, unsafe_allow_html=True)

    # ── STEP 2：設定頁數 ──────────────────────────────────
    st.markdown('<div class="step-label" style="margin-top:1.5rem">Step 2 — 設定保留頁數</div>', unsafe_allow_html=True)

    col_slider, col_info = st.columns([3, 1])
    with col_slider:
        keep_pages = st.slider(
            "保留頁數",
            min_value=1,
            max_value=max_pages,
            value=min(20, max_pages),
            label_visibility="collapsed",
        )
    with col_info:
        st.metric("保留前", f"{keep_pages} 頁")

    will_trim   = [f for f in valid_files if f["pages"] > keep_pages]
    will_keep   = [f for f in valid_files if f["pages"] <= keep_pages]
    error_files = [f for f in file_infos if f["status"] == "error"]

    col1, col2, col3 = st.columns(3)
    col1.metric("✂️ 會裁切", f"{len(will_trim)} 個")
    col2.metric("📄 不需裁切", f"{len(will_keep)} 個")
    col3.metric("⚠️ 無法處理", f"{len(error_files)} 個")

    # ── STEP 3：裁切並下載 ────────────────────────────────
    st.markdown('<div class="step-label" style="margin-top:1.5rem">Step 3 — 裁切並下載</div>', unsafe_allow_html=True)

    if st.button("✂️ 開始批次裁切，打包下載 ZIP", use_container_width=True, type="primary"):
        progress = st.progress(0, text="準備中...")
        results = []

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, info in enumerate(valid_files):
                fname = info["file"].name
                progress.progress(idx / len(valid_files), text=f"處理中：{fname}")
                try:
                    reader = PdfReader(io.BytesIO(info["data"]))
                    actual_keep = min(keep_pages, info["pages"])
                    writer = PdfWriter()
                    for i in range(actual_keep):
                        writer.add_page(reader.pages[i])
                    out_buf = io.BytesIO()
                    writer.write(out_buf)
                    stem = fname.replace(".pdf", "")
                    out_name = f"{stem}_前{actual_keep}頁.pdf"
                    zf.writestr(out_name, out_buf.getvalue())
                    results.append({"name": fname, "out": out_name,
                                    "original": info["pages"], "kept": actual_keep, "ok": True})
                except Exception as e:
                    results.append({"name": fname, "ok": False, "err": str(e)})

        progress.progress(1.0, text="完成！")
        zip_buffer.seek(0)

        ok_count  = sum(1 for r in results if r["ok"])
        err_count = sum(1 for r in results if not r["ok"])

        st.markdown(f"""
        <div class="summary-box">
          ✅ 裁切完成！成功 <strong>{ok_count}</strong> 個
          {"，失敗 <strong>" + str(err_count) + "</strong> 個" if err_count else ""}
        </div>
        """, unsafe_allow_html=True)

        st.download_button(
            label=f"⬇️ 下載全部（trimmed_pdfs.zip，共 {ok_count} 個檔案）",
            data=zip_buffer,
            file_name="trimmed_pdfs.zip",
            mime="application/zip",
            use_container_width=True,
        )

else:
    st.info("📂 請上傳一或多個 PDF 檔案（可按住 Ctrl / Cmd 多選，或直接框選多個檔案拖入）")

st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#4a5060;font-size:0.8rem">PDF 批次裁切工具 · Python + Streamlit · 檔案不會儲存於伺服器</p>',
    unsafe_allow_html=True,
)
