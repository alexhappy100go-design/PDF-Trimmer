import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile

st.set_page_config(
    page_title="PDF 批次裁切工具",
    page_icon="✂️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=JetBrains+Mono:wght@500&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans TC', sans-serif; }

/* ── Hero ── */
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

/* ── 拖曳區覆寫 ── */
[data-testid="stFileUploader"] {
    background: #0f1117;
}
[data-testid="stFileUploaderDropzone"] {
    background: #111827 !important;
    border: 2.5px dashed #2d3a55 !important;
    border-radius: 16px !important;
    padding: 3rem 2rem !important;
    transition: border-color 0.2s, background 0.2s;
    cursor: pointer;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #4f8ef7 !important;
    background: #131c2e !important;
}
[data-testid="stFileUploaderDropzone"] > div {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}
/* 拖曳圖示與文字 */
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: #8892a4 !important;
    font-size: 1rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] svg {
    width: 52px !important;
    height: 52px !important;
    color: #4f8ef7 !important;
    margin-bottom: 0.5rem;
}
/* Browse files 按鈕 */
[data-testid="stFileUploaderDropzone"] button {
    background: #4f8ef7 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.4rem !important;
    font-weight: 600 !important;
    margin-top: 0.5rem !important;
    cursor: pointer !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: #3a7de0 !important;
}

/* ── 步驟標題 ── */
.step-label {
    font-size: 0.75rem; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
    color: #4f8ef7; margin-bottom: 0.6rem; margin-top: 1.6rem;
}

/* ── 檔案列表 ── */
.file-row {
    display: flex; align-items: center; justify-content: space-between;
    background: #1a1f2e; border: 1px solid #2a2f3e;
    border-radius: 8px; padding: 0.6rem 1rem;
    margin-bottom: 0.4rem; font-size: 0.88rem; color: #c8d0e0;
}
.file-row .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-row .badge {
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
    background: #2a2f3e; color: #8892a4;
    padding: 2px 8px; border-radius: 4px; margin-left: 8px; white-space: nowrap;
}
.file-row .badge.blue { background: #1e3a5f; color: #4f8ef7; }
.file-row .badge.warn { background: #3d2a00; color: #f5a623; }

.summary-box {
    background: #0d1a0f; border: 1px solid #1e4d2a;
    border-radius: 10px; padding: 1rem 1.2rem;
    color: #3ecf8e; font-size: 0.9rem; margin: 1rem 0;
}

/* ── 主要按鈕 ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #4f8ef7, #3a7de0) !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    padding: 0.7rem !important;
    letter-spacing: 0.3px;
    transition: opacity 0.2s;
}
[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.88 !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div style="font-size:2.6rem;margin-bottom:0.4rem">✂️</div>
  <h1>PDF 批次裁切工具</h1>
  <p>拖曳或選取多個 PDF，設定保留頁數，一鍵打包下載</p>
</div>
""", unsafe_allow_html=True)

# ── STEP 1：拖曳上傳 ──────────────────────────────────────
st.markdown('<div class="step-label">Step 1 — 拖曳 PDF 到下方區域，或點擊選取檔案</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    label=" ",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    help="支援同時拖入多個 PDF，或按住 Ctrl / Cmd 多選",
)

if uploaded_files:
    # 讀取檔案資訊
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
            "file": f, "data": data,
            "pages": pages,
            "size_kb": round(len(data) / 1024, 1),
            "status": status,
        })

    total_files = len(file_infos)
    valid_files = [f for f in file_infos if f["status"] == "ok"]
    max_pages   = max((f["pages"] for f in valid_files), default=1)

    # 檔案清單
    with st.expander(f"📋 已載入 {total_files} 個檔案（點此展開）", expanded=total_files <= 12):
        rows_html = ""
        for info in file_infos:
            name = info["file"].name
            if info["status"] == "error":
                badge = '<span class="badge warn">⚠ 無法讀取</span>'
            else:
                badge = (f'<span class="badge blue">{info["pages"]} 頁</span>'
                         f'<span class="badge">{info["size_kb"]} KB</span>')
            rows_html += f'<div class="file-row"><span class="name">📄 {name}</span>{badge}</div>'
        st.markdown(rows_html, unsafe_allow_html=True)

    # ── STEP 2：設定頁數 ──────────────────────────────────
    st.markdown('<div class="step-label">Step 2 — 設定保留頁數</div>', unsafe_allow_html=True)

    col_slider, col_metric = st.columns([4, 1])
    with col_slider:
        if max_pages == 1:
            keep_pages = 1
            st.info("上傳的 PDF 只有 1 頁，將保留完整內容。")
        else:
            keep_pages = st.slider(
                "保留頁數（拖動調整）",
                min_value=1,
                max_value=max_pages,
                value=min(20, max_pages),
            )
    with col_metric:
        st.metric("保留前", f"{keep_pages} 頁")

    will_trim   = [f for f in valid_files if f["pages"] > keep_pages]
    will_keep   = [f for f in valid_files if f["pages"] <= keep_pages]
    error_files = [f for f in file_infos if f["status"] == "error"]

    c1, c2, c3 = st.columns(3)
    c1.metric("✂️ 會裁切",    f"{len(will_trim)} 個")
    c2.metric("📄 不需裁切",  f"{len(will_keep)} 個")
    c3.metric("⚠️ 無法處理", f"{len(error_files)} 個")

    # ── STEP 3：執行 ─────────────────────────────────────
    st.markdown('<div class="step-label">Step 3 — 裁切並下載</div>', unsafe_allow_html=True)

    if st.button("✂️ 開始批次裁切，打包下載 ZIP", use_container_width=True, type="primary"):
        progress = st.progress(0, text="準備中...")
        results  = []

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, info in enumerate(valid_files):
                fname = info["file"].name
                progress.progress(idx / len(valid_files), text=f"處理中：{fname}")
                try:
                    reader      = PdfReader(io.BytesIO(info["data"]))
                    actual_keep = min(keep_pages, info["pages"])
                    writer      = PdfWriter()
                    for i in range(actual_keep):
                        writer.add_page(reader.pages[i])
                    out_buf = io.BytesIO()
                    writer.write(out_buf)
                    stem     = fname.replace(".pdf", "")
                    out_name = f"{stem}_前{actual_keep}頁.pdf"
                    zf.writestr(out_name, out_buf.getvalue())
                    results.append({"ok": True, "kept": actual_keep, "original": info["pages"]})
                except Exception as e:
                    results.append({"ok": False, "err": str(e)})

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
    # 空狀態提示
    st.markdown("""
    <div style="text-align:center;padding:1rem 0;color:#4a5060;font-size:0.88rem">
      💡 支援 Windows / Mac · 可同時拖入 20~30 個檔案 · 檔案不會儲存於伺服器
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#3a4050;font-size:0.8rem">PDF 批次裁切工具 · Python + Streamlit</p>',
    unsafe_allow_html=True,
)
