# AI Invoice Extractor 🧾

Ứng dụng web trực quan và mạnh mẽ giúp trích xuất tự động thông tin từ nhiều hóa đơn dạng **PDF** hoặc **Hình ảnh (PNG, JPG, JPEG)** sang bảng dữ liệu **Excel** bằng Trí tuệ nhân tạo **Gemini 2.5 Flash** của Google.

Ứng dụng được xây dựng hoàn toàn bằng **Python & Streamlit**, có giao diện thân thiện, cơ chế tự động phòng ngừa lỗi (Crash-resistant) và sẵn sàng deploy lên môi trường đám mây (Streamlit Community Cloud).

---

## 🌟 Các Tính Năng Chính
- **Xử lý đa phương thức (Multimodal)**: Đọc được cả file PDF số, PDF scan và ảnh chụp hóa đơn (chụp nghiêng, chụp bằng điện thoại).
- **Trích xuất thông minh & Chính xác**: Tự động nhận diện và số hóa: Số hóa đơn, Ngày lập, Mã số thuế bán, Tên đơn vị bán, Tiền trước thuế, Tiền thuế GTGT, Tổng tiền thanh toán.
- **Trích xuất hàng loạt (Batch Processing)**: Tải lên và xử lý đồng thời nhiều hóa đơn.
- **Tự động phòng ngừa lỗi (Self-Checking)**: File hỏng hoặc không trích xuất được sẽ tự động bị bỏ qua kèm log báo lỗi mà không làm dừng/sập ứng dụng.
- **Xuất Excel nhanh chóng**: Xuất bảng kết quả ra file Excel `.xlsx` chuyên nghiệp được định dạng cột tự động.
- **Bảo mật tuyệt đối**: Gọi API Key thông qua biến môi trường an toàn, không lưu trữ dữ liệu của người dùng.

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Thử Cục Bộ (Local)

### Bước 1: Chuẩn bị mã nguồn
Tải mã nguồn này về máy tính của bạn và mở thư mục dự án lên bằng Terminal/PowerShell.

### Bước 2: Tạo môi trường ảo & Cài đặt thư viện
Chạy các lệnh sau để tạo môi trường ảo Python và cài đặt các thư viện cần thiết:

```bash
# Tạo môi trường ảo (Khuyên dùng)
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows (Command Prompt):
venv\Scripts\activate
# Trên Windows (PowerShell):
.\venv\Scripts\activate
# Trên macOS / Linux:
source venv/bin/activate

# Cài đặt các thư viện từ requirements.txt
pip install -r requirements.txt
```

### Bước 3: Đăng ký Gemini API Key (Miễn phí)
1. Truy cập vào [Google AI Studio](https://aistudio.google.com/).
2. Đăng nhập bằng tài khoản Google.
3. Nhấp vào nút **Get API Key** và tạo một Key mới. Lưu lại mã API Key này.

### Bước 4: Cấu hình API Key cục bộ
Mở thư mục dự án của bạn lên:
1. Tạo một thư mục con tên là `.streamlit` (nếu chưa có).
2. Tạo file tên là `secrets.toml` bên trong thư mục `.streamlit`.
3. Dán nội dung sau vào file (Thay thế giá trị API Key của bạn):
```toml
GEMINI_API_KEY = "DÁN_API_KEY_CỦA_BẠN_VÀO_ĐÂY"
```
*(Lưu ý: File `.streamlit/secrets.toml` đã được thêm vào `.gitignore` nên sẽ không bị đẩy lên GitHub, đảm bảo an toàn tuyệt đối)*.

### Bước 5: Chạy ứng dụng web
Khởi chạy Streamlit cục bộ bằng lệnh:
```bash
streamlit run app.py
```
Ứng dụng sẽ tự động mở trên trình duyệt web của bạn tại địa chỉ mặc định `http://localhost:8501`.

---

## 🌐 Hướng Dẫn Deploy Lên Streamlit Community Cloud (Miễn Phí)

Để đưa ứng dụng này thành một trang web công khai để ai cũng có thể truy cập được qua internet mà không cần cấu hình trên máy local, bạn làm theo các bước sau:

### Phần 1: Đẩy mã nguồn lên GitHub
1. Truy cập vào [GitHub](https://github.com/) và đăng nhập tài khoản.
2. Tạo một repository mới (ở chế độ **Public** hoặc **Private** đều được).
3. Đẩy toàn bộ mã nguồn thư mục dự án của bạn lên repository này bằng Git:
   ```bash
   git init
   git add .
   git commit -m "Initialize project: AI Invoice Extractor"
   git branch -M main
   git remote add origin https://github.com/<TÊN-TÀI-KHOẢN-CỦA-BẠN>/<TÊN-REPO-CỦA-BẠN>.git
   git push -u origin main
   ```

### Phần 2: Kết nối & Deploy trên Streamlit Cloud
1. Truy cập vào [Streamlit Community Cloud](https://share.streamlit.io/) và đăng nhập bằng tài khoản GitHub của bạn.
2. Nhấp vào nút **Create app** (hoặc **New app**) ở góc trên bên phải.
3. Cấu hình các thông số deploy:
   - **Repository**: Chọn Repo GitHub bạn vừa đẩy code lên.
   - **Branch**: Chọn `main`.
   - **Main file path**: Điền `app.py`.
4. **CẤU HÌNH API KEY (Quan trọng)**:
   - Nhấp vào mục **Advanced settings...** ngay trước khi nhấn nút Deploy (hoặc vào **Settings -> Secrets** trên Dashboard sau khi deploy).
   - Ở ô nhập **Secrets**, dán cấu hình sau:
     ```toml
     GEMINI_API_KEY = "AIzaSy..." # Thay bằng API Key thật của bạn
     ```
   - Nhấp **Save**.
5. Nhấp nút **Deploy!**. Streamlit Cloud sẽ tự động khởi tạo môi trường, cài đặt thư viện từ `requirements.txt` và chạy ứng dụng. Sau 1-2 phút, bạn sẽ có một đường link web công khai có dạng `https://<tên-ứng-dụng>.streamlit.app/`.

---

## 🛡️ Thiết kế Robust & Giải quyết Sự cố
- **Kiểm tra định dạng file**: Ứng dụng giới hạn các định dạng file hỗ trợ. Nếu người dùng chọn file sai định dạng, Streamlit sẽ từ chối hoặc trả về thông báo lỗi trực quan.
- **Bắt lỗi API**: Nếu kết nối API bị gián đoạn, API Key bị hết hạn hoặc quá hạn mức (Rate limit), hệ thống sẽ hiển thị cảnh báo đỏ trực quan, không hiển thị lỗi code (Traceback error).
- **Tự cô lập lỗi (Fault Isolation)**: Nếu bạn upload 10 file mà trong đó có 1 file bị hỏng hoặc định dạng lạ, ứng dụng vẫn sẽ trích xuất thành công 9 file còn lại, ghi chú "Thất bại" và lý do lỗi riêng cho file bị hỏng đó vào bảng Excel và nhật ký hiển thị.
