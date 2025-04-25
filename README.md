# Thông tin sinh viên  
Nguyễn Văn Thành   
Lê Hữu Hưng  
Nguyễn Khải  




# Expense Tracker

Expense Tracker là ứng dụng web được phát triển để giúp người dùng theo dõi tình hình tài chính cá nhân. Với giao diện thân thiện và dễ sử dụng, ứng dụng cho phép người dùng quản lý thu nhập, chi tiêu và tạo báo cáo chi tiết để hiểu rõ hơn về thói quen chi tiêu của mình.

## Tính năng chính

- Quản lý người dùng: Đăng ký, đăng nhập, cập nhật thông tin cá nhân
- Theo dõi giao dịch: Ghi lại các khoản thu nhập và chi tiêu
- Phân loại giao dịch: Phân loại theo danh mục để dễ dàng theo dõi
- Tiến độ ngân sách: Cho phép người dùng kiểm soát ngân sách dễ dàng
- Phân tích dữ liệu: Xem biểu đồ và báo cáo thống kê
- Quản lý ngân sách: Thiết lập và theo dõi ngân sách theo danh mục
- Xuất báo cáo: Tạo và tải xuống báo cáo Excel
  
## Giao diện người dùng
- Dashboard hiện đại với thống kê trực quan
- Biểu đồ tương tác cho phép theo dõi xu hướng chi tiêu
- Bảng tiến độ ngân sách với mã màu trực quan (xanh, vàng, đỏ)
- Thiết kế responsive thân thiện với người dùng
- Hỗ trợ chế độ xem theo tháng/tuần

## Điểm nổi bật
- Khả năng theo dõi chi tiêu theo thời gian thực
- Phân tích chi tiết tỷ lệ chi tiêu theo danh mục
- Tính năng đặt ngân sách và cảnh báo khi vượt ngưỡng
- Tạo báo cáo chi tiết với biểu đồ trực quan
- Tính năng lọc và tìm kiếm giao dịch linh hoạt

## Yêu cầu hệ thống
- Python 3.9 hoặc cao hơn
- Pip (trình quản lý gói Python)
- Git (để clone repository)
- Docker (tùy chọn, nếu muốn chạy trong container)
- 
## cài đặt

### Sử dụng Docker

#### 1.Xây dựng Docker image:
```
docker build -t expense-tracker .
```

#### 2.Chạy Docker container:
```
docker run -p 5000:5000 expense-tracker
```

#### 3. Truy cập ứng dụng: 
```
Mở trình duyệt web và truy cập http://localhost:5000/
```

## Sử dụng 
- Đăng ký tài khoản mới hoặc đăng nhập bằng tài khoản hiện có.
- Quản lý các chi tiêu của bạn và xem hồ sơ của bạn, bao gồm cả ảnh đại diện.

## Cấu trúc cây

```


```
