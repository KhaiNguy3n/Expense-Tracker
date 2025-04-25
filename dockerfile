FROM python:3.11-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các gói phụ thuộc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ code vào container
COPY . .

# Biến môi trường để Flask không chạy ở chế độ debug trong môi trường production
ENV FLASK_ENV=production
ENV FLASK_APP=run.py

# Port mặc định của Flask
EXPOSE 5000

# Tạo thư mục cho ảnh hồ sơ nếu chưa tồn tại
RUN mkdir -p expenses_tracker/static/profile_pics

# Khởi động ứng dụng
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]