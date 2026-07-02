import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import io
import re
from pydantic import BaseModel, Field
from typing import Optional

# Cấu hình giao diện Streamlit với Layout rộng và tiêu đề đẹp mắt
st.set_page_config(
    page_title="AI Invoice Extractor - Trích xuất Hóa đơn Thông minh",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Định nghĩa Schema cho Dữ liệu Hóa đơn đầu ra (JSON Mode)
# ---------------------------------------------------------
class InvoiceData(BaseModel):
    invoice_number: str = Field(description="Số hóa đơn (invoice number)")
    date: str = Field(description="Ngày hóa đơn (định dạng DD/MM/YYYY)")
    tax_code: str = Field(description="Mã số thuế bên bán / đơn vị phát hành hóa đơn (tax code)")
    vendor_name: str = Field(description="Tên nhà cung cấp / đơn vị phát hành (vendor name)")
    subtotal: float = Field(description="Cộng tiền hàng / trước thuế (subtotal amount)")
    tax_amount: float = Field(description="Tiền thuế GTGT / VAT (tax amount)")
    total_amount: float = Field(description="Tổng tiền thanh toán đã bao gồm thuế (total amount)")

# ---------------------------------------------------------
# Custom CSS giúp nâng cao trải nghiệm giao diện người dùng
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Chỉnh sửa kiểu chữ toàn bộ trang */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Thiết kế thẻ Card cho thông tin tổng quan */
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
    /* Chỉnh sửa nút Tải xuống trông chuyên nghiệp hơn */
    .stDownloadButton button {
        background-color: #0984e3 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.3s ease;
    }
    .stDownloadButton button:hover {
        background-color: #74b9ff !important;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# Tiêu đề chính của ứng dụng
st.title("🧾 Trích xuất Hóa đơn sang Excel bằng AI")
st.markdown("---")

# ---------------------------------------------------------
# Sidebar: Quản lý API Key & Cài đặt mô hình
# ---------------------------------------------------------
st.sidebar.header("⚙️ Cấu hình Hệ thống")

# Lấy API Key từ Streamlit secrets hoặc cho phép người dùng nhập tay nếu chạy dưới local
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("🔑 Đã tự động tải API Key từ Secrets.")
else:
    api_key = st.sidebar.text_input("Nhập Google Gemini API Key:", type="password", help="API Key này được dùng để gọi mô hình Gemini 1.5. Key của bạn sẽ không bị lưu trữ.")
    if api_key:
        st.sidebar.success("🔑 Đã nhận API Key từ người dùng.")
    else:
        st.sidebar.warning("⚠️ Vui lòng cấu hình API Key trong Secrets hoặc nhập tại đây để bắt đầu.")

# Cho phép chọn Model (Danh sách mô hình ổn định được cấu hình thủ công)
model_choice = st.sidebar.selectbox(
    "Chọn mô hình AI:",
    ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
    index=0,
    help="Nên ưu tiên chọn gemini-2.0-flash để có tốc độ nhanh nhất và hạn mức gọi API rộng rãi nhất."
)

# Chỉ hiển thị hướng dẫn cấu hình nếu chưa có API Key tự động trong Secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.sidebar.markdown("""
    ---
    ### 📌 Lưu ý cấu hình Secrets khi Deploy:
    Để không cần nhập API Key mỗi lần mở web, hãy tạo cấu hình biến môi trường trên Streamlit Cloud với key:
    `GEMINI_API_KEY = "key_của_bạn"`
    """)

# ---------------------------------------------------------
# Hàm hỗ trợ làm sạch dữ liệu số liệu
# ---------------------------------------------------------
def clean_numeric_value(val) -> float:
    """Làm sạch các giá trị tiền tệ, loại bỏ ký tự chữ, ký hiệu tệ để chuyển thành float."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    # Chuyển thành chuỗi và xử lý
    s = str(val).strip()
    # Loại bỏ các ký tự tiền tệ như VNĐ, $, đ, VND...
    s = re.sub(r'(?i)(VND|VNĐ|\$|đ|d)', '', s)
    # Loại bỏ khoảng trắng
    s = s.replace(" ", "")
    
    # Xử lý dấu phân cách hàng nghìn và dấu thập phân.
    # Thông thường định dạng VN là 1.000.000,00 và quốc tế là 1,000,000.00
    if ',' in s and '.' in s:
        # Nếu có cả dấu phẩy và chấm, xác định dấu nào xuất hiện cuối cùng để làm dấu thập phân
        if s.rfind(',') > s.rfind('.'):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif ',' in s:
        # Nếu chỉ có dấu phẩy, có thể là phân cách hàng nghìn (kiểu Anh) hoặc dấu thập phân (kiểu Việt)
        # Chúng ta giả định nếu sau dấu phẩy có đúng 2 hoặc 1 chữ số thì đó là thập phân, ngược lại là hàng nghìn
        parts = s.split(',')
        if len(parts[-1]) in [1, 2]:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    
    try:
        return float(s)
    except ValueError:
        return 0.0

# ---------------------------------------------------------
# Hàm xử lý cuộc gọi API đến Gemini
# ---------------------------------------------------------
import time

def extract_invoice_data(file_bytes, mime_type, model_name, api_key_to_use) -> dict:
    """Gửi file hóa đơn qua Gemini API kèm cơ chế Auto-Retry khi dính Rate Limit (429)."""
    # Khởi tạo API Key
    genai.configure(api_key=api_key_to_use)
    
    # Khởi tạo mô hình
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=InvoiceData,
            temperature=0.1
        )
    )
    
    prompt = """
    Bạn là một trợ lý AI chuyên nghiệp về xử lý tài liệu kế toán. Nhiệm vụ của bạn là bóc tách thông tin từ hóa đơn được cung cấp (dưới dạng ảnh hoặc PDF).
    Hãy điền chính xác thông tin vào các trường được định nghĩa trong schema JSON:
    - invoice_number: Số hóa đơn (nếu không thấy, điền 'N/A').
    - date: Ngày hóa đơn dưới định dạng DD/MM/YYYY. Nếu ngày trên hóa đơn ở định dạng khác (ví dụ YYYY-MM-DD), hãy convert về DD/MM/YYYY.
    - tax_code: Mã số thuế bên bán (nếu có, không chứa dấu cách hay ký tự lạ).
    - vendor_name: Tên của công ty/hộ kinh doanh bán hàng.
    - subtotal: Cộng tiền hàng (chưa bao gồm thuế GTGT). Nếu hóa đơn không tách biệt thuế, hãy tính toán hoặc lấy số tiền trước thuế.
    - tax_amount: Tiền thuế GTGT.
    - total_amount: Tổng tiền thanh toán (bao gồm cả thuế).
    
    Lưu ý quan trọng: Chỉ trích xuất thông tin khách quan từ tài liệu. Không tự bịa thông tin.
    """
    
    file_part = {
        "mime_type": mime_type,
        "data": file_bytes
    }
    
    # Cơ chế Auto-Retry (Tối đa 5 lần) khi bị lỗi 429 (Rate limit)
    max_retries = 5
    base_delay = 3.0 # giây
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content([file_part, prompt])
            return json.loads(response.text)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = any(x in err_msg.lower() for x in ["429", "quota", "resourceexhausted", "rate limit"])
            
            if is_rate_limit and attempt < max_retries - 1:
                # Trích xuất thời gian chờ từ thông báo lỗi của Google nếu có (ví dụ: "retry in 3.016s")
                wait_time = base_delay
                match = re.search(r"retry in ([\d\.]+)s", err_msg.lower())
                if match:
                    wait_time = float(match.group(1)) + 0.5 # Cộng thêm 0.5s sai số an toàn
                
                st.toast(f"⏳ Hàng đợi bận (Rate Limit). Tự động thử lại sau {wait_time:.1f} giây...", icon="⚠️")
                time.sleep(wait_time)
                base_delay *= 2 # Nhân đôi thời gian chờ cho lần sau nếu vẫn lỗi
            else:
                # Nếu không phải lỗi Rate limit hoặc đã thử lại quá số lần, quăng lỗi ra ngoài
                raise e

# ---------------------------------------------------------
# Giao diện tải file và xử lý chính
# ---------------------------------------------------------
uploaded_files = st.file_uploader(
    "Tải lên các hóa đơn của bạn (Hỗ trợ PDF, PNG, JPG, JPEG)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"📁 Đã chọn {len(uploaded_files)} file. Sẵn sàng xử lý.")
    
    # Nút bấm kích hoạt tiến trình
    if st.button("🚀 Bắt đầu trích xuất dữ liệu", use_container_width=True):
        if not api_key:
            st.error("❌ Vui lòng cung cấp Gemini API Key tại Sidebar trước khi tiến hành xử lý!")
        else:
            success_results = []
            failed_results = []
            
            # Tạo thanh tiến trình tổng quan
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            status_text.markdown("⚡ **Đang bắt đầu xử lý song song các hóa đơn...**")
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # Giới hạn tối đa 5 luồng xử lý song song để tránh vượt ngưỡng RPM của API
            max_workers = min(5, len(uploaded_files))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Gửi toàn bộ file vào hàng chờ xử lý của Thread Pool
                future_to_filename = {
                    executor.submit(
                        extract_invoice_data, 
                        file.getvalue(), 
                        file.type, 
                        model_choice, 
                        api_key
                    ): file.name for file in uploaded_files
                }
                
                completed = 0
                total_files = len(uploaded_files)
                
                for future in as_completed(future_to_filename):
                    file_name = future_to_filename[future]
                    completed += 1
                    
                    # Cập nhật tiến trình thời gian thực
                    percent_complete = completed / total_files
                    progress_bar.progress(percent_complete)
                    status_text.markdown(f"⏳ **Tiến trình:** Đã hoàn thành `{completed}/{total_files}` file...")
                    
                    try:
                        # Nhận kết quả từ luồng chạy
                        raw_data = future.result()
                        
                        # Làm sạch dữ liệu số liệu
                        subtotal_clean = clean_numeric_value(raw_data.get("subtotal", 0.0))
                        tax_clean = clean_numeric_value(raw_data.get("tax_amount", 0.0))
                        total_clean = clean_numeric_value(raw_data.get("total_amount", 0.0))
                        
                        # Lưu kết quả thành công
                        processed_item = {
                            "Tên file": file_name,
                            "Số hóa đơn": raw_data.get("invoice_number", "N/A"),
                            "Ngày hóa đơn": raw_data.get("date", "N/A"),
                            "Mã số thuế": raw_data.get("tax_code", "N/A"),
                            "Tên nhà cung cấp": raw_data.get("vendor_name", "N/A"),
                            "Cộng tiền hàng (Subtotal)": subtotal_clean,
                            "Tiền thuế GTGT (Tax)": tax_clean,
                            "Tổng cộng (Total)": total_clean
                        }
                        success_results.append(processed_item)
                        
                    except Exception as e:
                        # Ghi nhận lỗi cho file này và tiếp tục chạy các luồng khác (Fault-tolerant)
                        error_msg = str(e)
                        failed_results.append({
                            "Tên file": file_name,
                            "Lỗi chi tiết": error_msg
                        })
                        st.toast(f"❌ Lỗi xử lý file {file_name}!", icon="⚠️")
                        st.warning(f"⚠️ Không thể xử lý file **{file_name}**. Lỗi: {error_msg}")
            
            # Cập nhật thanh tiến trình hoàn thành 100%
            progress_bar.progress(1.0)
            status_text.markdown("✅ **Đã hoàn thành xử lý toàn bộ danh sách tệp tin!**")
            
            # ---------------------------------------------------------
            # Hiển thị kết quả & Cho phép tải về Excel
            # ---------------------------------------------------------
            st.markdown("---")
            st.subheader("📊 Kết quả trích xuất")
            
            # Hiển thị số lượng thống kê
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin:0;color:#2ecc71;'>🎉 Thành công: {len(success_results)} / {len(uploaded_files)}</h3>
                    <p style='margin:5px 0 0 0;color:#7f8c8d;'>Các hóa đơn đã bóc tách thông tin hoàn tất.</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card" style="border-left-color: #e74c3c;">
                    <h3 style='margin:0;color:#e74c3c;'>⚠️ Thất bại: {len(failed_results)}</h3>
                    <p style='margin:5px 0 0 0;color:#7f8c8d;'>Các file bị lỗi hoặc không thể phân tích.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Nếu có kết quả thành công, hiển thị và tạo file Excel
            if success_results:
                df = pd.DataFrame(success_results)
                
                # Định dạng hiển thị dataframe trên Streamlit đẹp hơn
                st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "Cộng tiền hàng (Subtotal)": st.column_config.NumberColumn(format="%.2f"),
                        "Tiền thuế GTGT (Tax)": st.column_config.NumberColumn(format="%.2f"),
                        "Tổng cộng (Total)": st.column_config.NumberColumn(format="%.2f")
                    }
                )
                
                # Xuất ra file Excel trong bộ nhớ đệm (BytesIO) để người dùng tải về trực tiếp
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # Ghi dataframe vào sheet chính
                    df.to_excel(writer, index=False, sheet_name="HoaDonTricXuat")
                    
                    # Tùy biến độ rộng cột tự động trên openpyxl
                    workbook = writer.book
                    worksheet = writer.sheets["HoaDonTricXuat"]
                    for col in worksheet.columns:
                        max_len = max(len(str(cell.value or '')) for cell in col)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
                
                excel_data = excel_buffer.getvalue()
                
                # Cung cấp nút tải về Excel
                st.download_button(
                    label="📥 Tải xuống File Excel (.xlsx)",
                    data=excel_data,
                    file_name="Hoa_don_trich_xuat_AI.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            # Hiển thị bảng lỗi nếu có để admin dễ kiểm tra
            if failed_results:
                with st.expander("🔍 Chi tiết các tệp bị lỗi"):
                    df_failed = pd.DataFrame(failed_results)
                    st.table(df_failed)
else:
    # Trạng thái ban đầu khi chưa tải file
    st.info("💡 Vui lòng kéo thả hoặc tải lên các tệp hóa đơn của bạn ở khung bên trên để bắt đầu trích xuất.")
