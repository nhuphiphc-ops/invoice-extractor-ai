import streamlit as st
import google.generativeai as genai
import pandas as pd
from pydantic import BaseModel, Field
from typing import Optional
import os
import io
import json
from PIL import Image

# ==============================================================================
# 1. CẤU HÌNH TRANG & GIAO DIỆN (THEME & STYLING)
# ==============================================================================
st.set_page_config(
    page_title="AI Invoice Extractor - Trích Xuất Hóa Đơn Tự Động",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS để giao diện trông chuyên nghiệp và hiện đại hơn
st.markdown("""
<style>
    /* Chỉnh sửa tổng thể */
    .main-title {
        font-size: 2.6rem;
        color: #1E3A8A;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
        text-align: center;
    }
    /* Tùy chỉnh các khối thông báo */
    .stAlert {
        border-radius: 8px;
    }
    /* Chỉnh sửa bảng preview */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. XÁC THỰC API KEY BẢO MẬT
# ==============================================================================
def get_api_key():
    """
    Lấy API Key từ Streamlit Secrets hoặc Biến môi trường hệ thống.
    Đảm bảo an toàn bảo mật, không lộ Key lên mã nguồn.
    """
    # 1. Tìm trong Streamlit Secrets (Dùng khi deploy lên Streamlit Cloud)
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    
    # 2. Tìm trong biến môi trường hệ thống
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key
        
    return None

api_key = get_api_key()

# ==============================================================================
# 3. ĐỊNH NGHĨA PYDANTIC SCHEMA CHO TRÍCH XUẤT DỮ LIỆU CÓ CẤU TRÚC
# ==============================================================================
class InvoiceExtraction(BaseModel):
    invoice_number: Optional[str] = Field(None, description="Số hóa đơn (Invoice number/No.). Nếu không tìm thấy, trả về null.")
    invoice_date: Optional[str] = Field(None, description="Ngày lập hóa đơn (Invoice date). Định dạng chuẩn DD/MM/YYYY. Nếu không tìm thấy, trả về null.")
    seller_tax_code: Optional[str] = Field(None, description="Mã số thuế của bên bán / đơn vị cung cấp (Seller's Tax Code/MST). Nếu không tìm thấy, trả về null.")
    seller_name: Optional[str] = Field(None, description="Tên công ty / đơn vị bán hàng (Seller's Name). Nếu không tìm thấy, trả về null.")
    total_before_tax: Optional[float] = Field(None, description="Tổng tiền hàng chưa thuế / giá trị trước thuế (Total before tax/Subtotal). Trả về dạng số float. Nếu không tìm thấy, trả về null.")
    tax_amount: Optional[float] = Field(None, description="Tiền thuế GTGT / VAT (Tax amount). Trả về dạng số float. Nếu không tìm thấy, trả về null.")
    total_amount: Optional[float] = Field(None, description="Tổng cộng tiền thanh toán đã bao gồm thuế (Total payment amount/Total after tax). Trả về dạng số float. Nếu không tìm thấy, trả về null.")

# ==============================================================================
# 4. LOGIC XỬ LÝ BACKEND (GỌI GEMINI API & CƠ CHẾ SELF-CHECKING)
# ==============================================================================
def extract_invoice_data(api_key, file_bytes, mime_type, file_name):
    """
    Gửi file nhị phân sang Gemini API để phân tích cấu trúc và trích xuất dữ liệu.
    Bọc trong khối try-except cục bộ để tự cô lập lỗi của từng file (Crash-resistant).
    """
    try:
        # Cấu hình API Key cho thư viện
        genai.configure(api_key=api_key)
        
        # Khởi tạo mô hình Gemini 2.5 Flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Đóng gói file thành format đầu vào của Gemini Multimodal API
        file_part = {
            "mime_type": mime_type,
            "data": file_bytes
        }
        
        prompt = (
            "Bạn là một trợ lý AI chuyên nghiệp về kế toán và xử lý tài liệu tại Việt Nam.\n"
            "Hãy đọc và phân tích kỹ tài liệu hóa đơn được cung cấp (dạng PDF hoặc hình ảnh).\n"
            "Trích xuất chính xác các thông tin cần thiết theo đúng cấu trúc yêu cầu.\n"
            "Lưu ý quan trọng:\n"
            "1. Đối với các trường số tiền (total_before_tax, tax_amount, total_amount), "
            "hãy chuyển đổi về dạng số thập phân thuần túy (float), loại bỏ mọi dấu phân cách hàng nghìn (ví dụ: dấu chấm hay phẩy) và đơn vị tiền tệ VND.\n"
            "Ví dụ: '1.500.000 đ' -> 1500000.0\n"
            "2. Đảm bảo mã số thuế người bán (seller_tax_code) là một chuỗi số viết liền, bao gồm cả chi nhánh phụ nếu có (ví dụ: '0101234567-001').\n"
            "3. Nếu thông tin nào không tồn tại trong hóa đơn, hãy trả về null."
        )
        
        # Gọi API với cấu hình Structured Output thông qua response_schema
        response = model.generate_content(
            [prompt, file_part],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=InvoiceExtraction,
                temperature=0.1  # Giảm tính ngẫu nhiên để tăng độ chính xác trích xuất
            )
        )
        
        # Chuyển đổi chuỗi JSON phản hồi thành Python dict
        result_json = json.loads(response.text)
        result_json["file_name"] = file_name
        result_json["status"] = "Thành công"
        result_json["error_message"] = ""
        
        return result_json

    except Exception as e:
        # Nếu có bất kỳ lỗi nào xảy ra trong quá trình gọi API hoặc parse dữ liệu,
        # ghi nhận lỗi cho file đó và trả về dict rỗng để không làm hỏng toàn bộ quy trình.
        return {
            "file_name": file_name,
            "invoice_number": None,
            "invoice_date": None,
            "seller_tax_code": None,
            "seller_name": None,
            "total_before_tax": None,
            "tax_amount": None,
            "total_amount": None,
            "status": "Thất bại",
            "error_message": f"Lỗi xử lý: {str(e)}"
        }

# ==============================================================================
# 5. GIAO DIỆN CHÍNH CỦA ỨNG DỤNG (FRONTEND)
# ==============================================================================

# Sidebar hướng dẫn cấu hình & thông tin dự án
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/000000/invoice.png", width=120)
    st.markdown("### 📑 Hướng Dẫn Sử Dụng")
    st.markdown(
        """
        1. **Tải lên hóa đơn**: Nhấn nút browse hoặc kéo thả các file hóa đơn dạng **PDF** hoặc **ảnh (PNG, JPG, JPEG)** vào khung tải lên.
        2. **Trích xuất dữ liệu**: Nhấn nút **Bắt đầu trích xuất**. Hệ thống sẽ gọi Gemini AI xử lý song song từng file.
        3. **Xem kết quả**: Kiểm tra bảng dữ liệu tổng hợp trực tiếp trên web.
        4. **Xuất Excel**: Tải file Excel chứa toàn bộ thông tin đã trích xuất về máy.
        """
    )
    st.markdown("---")
    st.markdown("### 🔒 Bảo Mật Thông Tin")
    st.info(
        "API Key được quản lý an toàn qua biến môi trường (Streamlit Secrets). "
        "Dữ liệu hóa đơn của bạn chỉ được xử lý qua API và không được lưu trữ lại trên máy chủ."
    )
    st.markdown("---")
    st.markdown("⚡ *Powered by Gemini 2.5 Flash*")

# Phần tiêu đề chính
st.markdown("<h1 class='main-title'>🧾 AI Invoice Extractor</h1>", unsafe_allowed_html=True)
st.markdown("<p class='subtitle'>Trích xuất hóa đơn PDF & Ảnh sang Excel tự động bằng Trí tuệ nhân tạo Gemini</p>", unsafe_allowed_html=True)

# Kiểm tra trạng thái cấu hình API Key
if not api_key:
    st.warning("⚠️ **Hệ thống chưa được cấu hình API Key!**")
    st.markdown(
        """
        **Hướng dẫn thiết lập nhanh:**
        - **Khi chạy local**: Tạo file `.streamlit/secrets.toml` trong thư mục gốc của dự án và dán nội dung sau:
          ```toml
          GEMINI_API_KEY = "Nhập_API_Key_Gemini_Của_Bạn_Vào_Đây"
          ```
        - **Khi deploy lên Streamlit Cloud**: Vào cài đặt ứng dụng (App settings) -> mục **Secrets** và dán:
          ```toml
          GEMINI_API_KEY = "Nhập_API_Key_Gemini_Của_Bạn_Vào_Đây"
          ```
        """
    )
    # Cho phép người dùng nhập key tạm thời trực tiếp trên giao diện để dùng thử nếu muốn
    temp_key = st.text_input("Hoặc nhập tạm thời API Key của bạn tại đây để trải nghiệm ngay:", type="password")
    if temp_key:
        api_key = temp_key
        st.success("Đã ghi nhận API Key tạm thời!")

# Nếu đã có API Key, tiếp tục hiển thị ứng dụng
if api_key:
    # 1. Khung upload file hóa đơn
    uploaded_files = st.file_uploader(
        "Tải lên các file hóa đơn (Hỗ trợ PDF, PNG, JPG, JPEG) - Có thể chọn nhiều file cùng lúc",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.write(f"📂 Đã chọn **{len(uploaded_files)}** file để xử lý.")
        
        # Nút bấm bắt đầu trích xuất
        if st.button("🚀 Bắt đầu trích xuất dữ liệu", use_container_width=True):
            results = []
            
            # Khởi tạo thanh tiến trình và trạng thái
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Vòng lặp xử lý từng file
            for idx, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.name
                status_text.markdown(f"⏳ Đang xử lý file ({idx + 1}/{len(uploaded_files)}): `{file_name}`...")
                
                # Đọc dữ liệu nhị phân của file
                file_bytes = uploaded_file.read()
                
                # Xác định Mime Type của file dựa trên đuôi mở rộng
                file_extension = file_name.split('.')[-1].lower()
                if file_extension == 'pdf':
                    mime_type = 'application/pdf'
                elif file_extension in ['png', 'jpg', 'jpeg']:
                    mime_type = f'image/{file_extension if file_extension != "jpg" else "jpeg"}'
                else:
                    mime_type = 'application/octet-stream'
                
                # Tự kiểm tra định dạng và dữ liệu rỗng (Self-Checking)
                if len(file_bytes) == 0:
                    results.append({
                        "file_name": file_name,
                        "invoice_number": None,
                        "invoice_date": None,
                        "seller_tax_code": None,
                        "seller_name": None,
                        "total_before_tax": None,
                        "tax_amount": None,
                        "total_amount": None,
                        "status": "Thất bại",
                        "error_message": "Lỗi: File trống (dung lượng 0 bytes)."
                    })
                else:
                    # Gọi hàm trích xuất dữ liệu từ Backend
                    extracted_data = extract_invoice_data(api_key, file_bytes, mime_type, file_name)
                    results.append(extracted_data)
                
                # Cập nhật thanh tiến trình
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress)
            
            status_text.success("🎉 Đã hoàn thành xử lý toàn bộ các hóa đơn!")
            
            # 2. Xử lý hiển thị kết quả bằng Pandas
            df = pd.DataFrame(results)
            
            # Sắp xếp lại thứ tự cột cho hợp lý
            cols_order = [
                "file_name", "invoice_number", "invoice_date", 
                "seller_tax_code", "seller_name", "total_before_tax", 
                "tax_amount", "total_amount", "status", "error_message"
            ]
            df = df[cols_order]
            
            # Việt hóa tiêu đề các cột để hiển thị trên bảng
            df_display = df.rename(columns={
                "file_name": "Tên File",
                "invoice_number": "Số Hóa Đơn",
                "invoice_date": "Ngày Lập",
                "seller_tax_code": "Mã Số Thuế Bán",
                "seller_name": "Đơn Vị Bán",
                "total_before_tax": "Tiền Trước Thuế",
                "tax_amount": "Tiền Thuế GTGT",
                "total_amount": "Tổng Thanh Toán",
                "status": "Trạng Thái",
                "error_message": "Chi Tiết Lỗi"
            })
            
            # Hiển thị thống kê tổng quan
            success_count = sum(1 for r in results if r["status"] == "Thành công")
            fail_count = len(results) - success_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tổng số file", len(results))
            with col2:
                st.metric("Thành công ✅", success_count)
            with col3:
                st.metric("Thất bại ❌", fail_count)
            
            # Hiển thị bảng kết quả Preview
            st.markdown("### 📊 Xem trước kết quả trích xuất")
            st.dataframe(df_display, use_container_width=True)
            
            # 3. Tạo file Excel xuất ra bằng thư viện openpyxl qua Pandas
            # Lưu file Excel vào bộ nhớ đệm (BytesIO) để phục vụ việc download trực tiếp
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Đẩy dataframe gốc vào sheet Excel
                df.to_excel(writer, index=False, sheet_name="HoaDonTricXuat")
                
                # Tùy biến định dạng cho file Excel (tự động giãn độ rộng cột)
                workbook = writer.book
                worksheet = writer.sheets["HoaDonTricXuat"]
                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
            excel_data = excel_buffer.getvalue()
            
            # Nút tải xuống Excel
            st.download_button(
                label="📥 Tải xuống kết quả Excel (.xlsx)",
                data=excel_data,
                file_name="ket_qua_trich_xuat_hoa_don.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Hiển thị báo cáo lỗi chi tiết nếu có file xử lý thất bại
            if fail_count > 0:
                st.markdown("### ⚠️ Nhật ký lỗi chi tiết")
                for r in results:
                    if r["status"] == "Thất bại":
                        st.error(f"**File:** `{r['file_name']}` | **Lỗi:** {r['error_message']}")
