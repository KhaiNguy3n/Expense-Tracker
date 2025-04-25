from flask import render_template, url_for, flash, redirect, request, jsonify, session
from expenses_tracker import app, db, bcrypt
from expenses_tracker.forms import RegistrationForm, LoginForm, UpdateAccountForm, ExpenseForm
from expenses_tracker.models import User, Topic, Category, Income, Expense, Transaction, Budget
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from datetime import datetime, timedelta
from sqlalchemy import extract
from sqlalchemy import func
@app.route("/home")
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('home.html')

@app.route("/index")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
        
    # Lấy tháng và năm hiện tại để hiển thị
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Danh sách tên tháng bằng tiếng Việt
    month_names = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", 
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    
    # Tạo chuỗi tháng/năm để hiển thị trên giao diện
    current_period = f"{month_names[current_month-1]} {current_year}"
    
    return render_template('index.html',
                         title='Bảng điều khiển',
                         current_period=current_period,
                         current_month=current_month,
                         current_year=current_year)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account has been created! Please log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))  
    form = LoginForm() 
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check username and password', 'danger')      
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account has been updated', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image)
    return render_template('account.html', title='Account', image_file=image_file, form=form)

@app.route("/DanhMuc", methods=['GET'])
@login_required
def DanhMuc():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Lấy cả expenses và incomes
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).paginate(page=page, per_page=per_page)
    incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).paginate(page=page, per_page=per_page)
    
    form = ExpenseForm()

    default_topic = 'expense'
    categories = Category.query.filter_by(type=default_topic, user_id=current_user.id).all()
    form.category.choices = [(c.id, c.name) for c in categories] if categories else []
    
    form.date.data = datetime.now().date()
    return render_template('DanhMuc.html', title='Danh Mục', form=form, expenses=expenses, incomes=incomes)

@app.route("/add_expense", methods=['POST'])
@login_required
def add_expense():
    form = ExpenseForm(meta={'csrf': True})
    
    # Lấy topic type từ form
    topic_type = request.form.get('topic')
    
    # Lấy danh sách categories dựa trên topic type
    system_user = User.query.filter_by(username='system').first()
    system_user_id = system_user.id if system_user else None
    
    topic = Topic.query.filter_by(type=topic_type).first()
    if not topic:
        flash("Loại giao dịch không hợp lệ!", "danger")
        return redirect(url_for('DanhMuc'))
        
    categories = Category.query.filter(
        (Category.topic_id == topic.id) & 
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).all()
    
        
    form.category.choices = [(c.id, c.name) for c in categories]
    
    if not form.validate_on_submit():
        flash(f"Dữ liệu nhập không hợp lệ: {form.errors}", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Manual validation for category
    category_id = request.form.get('category')
    if not category_id:
        flash("Vui lòng chọn danh mục!", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Check if the category exists and belongs to either the current user or system user
    category = Category.query.filter(
        (Category.id == category_id) &
        (Category.type == topic_type) &
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).first()
    
    if not category:
        flash("Danh mục không hợp lệ!", "danger")
        return redirect(url_for('DanhMuc'))
    
    # Continue with your existing code...
    if topic_type == 'income':
        entry = Income(
            user_id=current_user.id,
            category_id=category.id,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data
        )
    else:
        entry = Expense(
            user_id=current_user.id,
            category_id=category.id,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data
        )

    db.session.add(entry)
    db.session.commit()
    flash('Thêm thành công!', 'success')
    return redirect(url_for('DanhMuc'))

@app.route("/delete_expenses", methods=['POST'])
@login_required
def delete_expenses():
    expense_ids = request.form.getlist('expense_ids')
    if not expense_ids:
        flash('Không có chi tiêu nào được chọn để xóa.', 'danger')
        return redirect(url_for('DanhMuc'))

    Expense.query.filter(Expense.id.in_(expense_ids), Expense.user_id == current_user.id).delete(synchronize_session=False)
    Income.query.filter(Income.id.in_(expense_ids), Income.user_id == current_user.id).delete(synchronize_session=False)
    db.session.commit()

    flash(f'Đã xóa thành công {len(expense_ids)} mục.', 'success')
    return redirect(url_for('DanhMuc'))


@app.route("/get_categories/<topic_type>")
@login_required
def get_categories(topic_type):
    # Get topic based on type
    topic = Topic.query.filter_by(type=topic_type).first()
    
    if not topic:
        return jsonify({'categories': []})

    # Get system user
    system_user = User.query.filter_by(username='system').first()
    system_user_id = system_user.id if system_user else None
    
    # Get categories for both current user and system user
    categories = Category.query.filter(
        (Category.topic_id == topic.id) & 
        ((Category.user_id == current_user.id) | (Category.user_id == system_user_id))
    ).all()
    
    # Format categories for JSON response
    categories_data = [{'id': cat.id, 'name': cat.name} for cat in categories]
    
    return jsonify({'categories': categories_data})

@app.route('/get_monthly_data')
@login_required
def get_monthly_data():
    # Lấy năm và tháng từ query params hoặc session, nếu không có thì lấy hiện tại
    selected_month = request.args.get('month', default=session.get('selected_month'))
    selected_year = request.args.get('year', default=session.get('selected_year'))
    
    # Nếu không có dữ liệu tháng/năm từ session hoặc query params, sử dụng tháng và năm hiện tại
    current_year = int(selected_year) if selected_year else datetime.now().year
    current_month = int(selected_month) if selected_month else datetime.now().month
    
    # Tạo dict để lưu dữ liệu theo tháng
    monthly_data = {
        'expenses': [0] * 12,
        'line_data': [0] * 12  # Dữ liệu cho biểu đồ đường
    }
    
    # Lấy dữ liệu chi tiêu theo tháng
    expense_data = db.session.query(
        extract('month', Expense.date).label('month'),
        db.func.sum(Expense.amount).label('total')
    ).filter(
        extract('year', Expense.date) == current_year,
        Expense.user_id == current_user.id
    ).group_by(extract('month', Expense.date)).all()
    
    # Cập nhật dữ liệu chi tiêu
    for month, total in expense_data:
        month_index = int(month) - 1  # Chuyển từ 1-12 sang 0-11
        monthly_data['expenses'][month_index] = float(total)
        monthly_data['line_data'][month_index] = float(total)
    
    # Tính toán tổng chi tiêu lũy kế cho biểu đồ đường
    total_so_far = 0
    for i in range(12):
        total_so_far += monthly_data['line_data'][i]
        monthly_data['line_data'][i] = total_so_far
    
    return jsonify(monthly_data)

@app.route('/get_dashboard_stats')
@login_required
def get_dashboard_stats():
    # Lấy tổng thu nhập và chi tiêu tháng hiện tại
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Tính toán cho tháng hiện tại
    current_income = db.session.query(db.func.sum(Income.amount))\
        .filter(Income.user_id == current_user.id,
                extract('month', Income.date) == current_month,
                extract('year', Income.date) == current_year)\
        .scalar() or 0
    
    current_expenses = db.session.query(db.func.sum(Expense.amount))\
        .filter(Expense.user_id == current_user.id,
                extract('month', Expense.date) == current_month,
                extract('year', Expense.date) == current_year)\
        .scalar() or 0
    
    # Tính toán cho tháng trước
    last_month = (current_month - 1) if current_month > 1 else 12
    last_year = current_year if current_month > 1 else current_year - 1
    
    last_month_income = db.session.query(db.func.sum(Income.amount))\
        .filter(Income.user_id == current_user.id,
                extract('month', Income.date) == last_month,
                extract('year', Income.date) == last_year)\
        .scalar() or 0
    
    last_month_expenses = db.session.query(db.func.sum(Expense.amount))\
        .filter(Expense.user_id == current_user.id,
                extract('month', Expense.date) == last_month,
                extract('year', Expense.date) == last_year)\
        .scalar() or 0
    
    # Tính total balance và saving rate hiện tại
    current_balance = current_income - current_expenses
    current_saving_rate = (current_balance / current_income * 100) if current_income > 0 else 0
    
    # Tính total balance và saving rate tháng trước
    last_balance = last_month_income - last_month_expenses
    last_saving_rate = (last_balance / last_month_income * 100) if last_month_income > 0 else 0
    
    # Tính phần trăm thay đổi
    income_change = ((current_income - last_month_income) / last_month_income * 100) if last_month_income > 0 else 0
    expense_change = ((current_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses > 0 else 0
    balance_change = ((current_balance - last_balance) / last_balance * 100) if last_balance > 0 else 0
    saving_rate_change = current_saving_rate - last_saving_rate
    
    return jsonify({
        'total_balance': current_balance,
        'total_income': current_income,
        'total_expenses': current_expenses,
        'saving_rate': current_saving_rate,
        'income_change': income_change,
        'expense_change': expense_change,
        'balance_change': balance_change,
        'saving_rate_change': saving_rate_change
    })

@app.route('/get_category_expenses')
def get_category_expenses():
    """
    API để lấy tổng chi tiêu theo danh mục trong tháng hiện tại hoặc tháng được chọn.
    Nhận tham số month và year từ query string.
    """
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Lấy tham số month và year từ request, mặc định là tháng hiện tại
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Log thông tin để debug
        print(f"[DEBUG] get_category_expenses: month={month}, year={year}, args={request.args}")
        
        if month and year:
            month = int(month)
            year = int(year)
            # Kiểm tra giá trị hợp lệ
            if not (1 <= month <= 12 and 2000 <= year <= 2100):
                raise ValueError(f"Invalid month/year: {month}/{year}")
        else:
            # Nếu không có tham số, lấy tháng và năm hiện tại
            current_date = datetime.now()
            month = current_date.month
            year = current_date.year
    except Exception as e:
        print(f"[ERROR] get_category_expenses: {str(e)}")
        # Nếu có lỗi, lấy tháng và năm hiện tại
        current_date = datetime.now()
        month = current_date.month
        year = current_date.year
    
    # Tạo khoảng thời gian cho tháng được chọn
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    print(f"[DEBUG] Tìm chi tiêu từ {start_date} đến {end_date}")
    
    # Truy vấn cơ sở dữ liệu để lấy tổng chi tiêu theo danh mục
    category_expenses = db.session.query(
        Category.name, 
        db.func.sum(Expense.amount).label('total')
    ).join(
        Expense, 
        Expense.category_id == Category.id
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).group_by(
        Category.name
    ).order_by(
        db.func.sum(Expense.amount).desc()
    ).all()
    
    # Tính tổng chi tiêu
    total_expense = sum(amount for _, amount in category_expenses)
    
    # Ánh xạ tên danh mục tiếng Anh sang tiếng Việt
    category_translations = {
        'Food': 'Ăn uống',
        'Transportation': 'Di chuyển',
        'Shopping': 'Mua sắm',
        'Entertainment': 'Giải trí',
        'Housing': 'Nhà cửa',
        'Utilities': 'Hóa đơn',
        'Healthcare': 'Y tế',
        'Personal': 'Cá nhân',
        'Education': 'Giáo dục',
        'Travel': 'Du lịch',
        'Debt': 'Nợ',
        'Gifts': 'Quà tặng',
        'Savings': 'Tiết kiệm',
        'Investment': 'Đầu tư',
        'Other': 'Khác'
    }
    
    # Chuẩn bị dữ liệu để trả về
    categories = []
    amounts = []
    percentages = []
    
    for category, amount in category_expenses:
        # Sử dụng tên danh mục tiếng Việt nếu có
        category_name = category_translations.get(category, category)
        categories.append(category_name)
        amounts.append(float(amount))
        if total_expense > 0:
            percentages.append(round((amount / total_expense) * 100, 2))
        else:
            percentages.append(0)
    
    # Trả về dữ liệu dạng JSON
    return jsonify({
        'categories': categories,
        'amounts': amounts,
        'percentages': percentages,
        'total': float(total_expense)
    })

@app.route('/get_recent_transactions')
@login_required
def get_recent_transactions():
    # Số lượng giao dịch gần đây cần lấy
    limit = request.args.get('limit', default=5, type=int)
    
    # Lấy dữ liệu chi tiêu gần đây
    recent_expenses = db.session.query(
        Expense.id,
        Expense.amount,
        Expense.description,
        Expense.date,
        Category.name.label('category_name')
    ).join(Category, Expense.category_id == Category.id)\
     .filter(Expense.user_id == current_user.id)\
     .order_by(Expense.date.desc())\
     .limit(limit).all()
    
    # Lấy dữ liệu thu nhập gần đây
    recent_incomes = db.session.query(
        Income.id,
        Income.amount,
        Income.description,
        Income.date,
        Category.name.label('category_name')
    ).join(Category, Income.category_id == Category.id)\
     .filter(Income.user_id == current_user.id)\
     .order_by(Income.date.desc())\
     .limit(limit).all()
    
    # Kết hợp và sắp xếp theo ngày gần nhất
    transactions = []
    
    for expense in recent_expenses:
        transactions.append({
            'id': expense.id,
            'type': 'expense',
            'amount': float(expense.amount),
            'description': expense.description,
            'date': expense.date.strftime('%d/%m/%Y'),
            'category': expense.category_name
        })
    
    for income in recent_incomes:
        transactions.append({
            'id': income.id,
            'type': 'income',
            'amount': float(income.amount),
            'description': income.description,
            'date': income.date.strftime('%d/%m/%Y'),
            'category': income.category_name
        })
    
    # Sắp xếp theo ngày giảm dần và giới hạn số lượng
    transactions.sort(key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'), reverse=True)
    transactions = transactions[:limit]
    
    return jsonify(transactions)

@app.route('/get_budget_progress')
@login_required
def get_budget_progress():
    # Lấy tháng và năm hiện tại hoặc được chọn từ session
    selected_month = session.get('selected_month', datetime.now().month)
    selected_year = session.get('selected_year', datetime.now().year)
    
    # Danh sách các danh mục cần loại bỏ
    excluded_categories = ['Thực phẩm', 'Ăn uống']
    
    # Lấy tất cả danh mục chi tiêu của người dùng
    expense_categories = db.session.query(Category.name).distinct().filter(
        Category.type == 'expense',
        (Category.user_id == current_user.id) | (Category.user_id == db.session.query(User.id).filter(User.username == 'system').scalar())
    ).all()
    
    expense_category_names = [cat[0] for cat in expense_categories]
    
    # Lấy ngân sách từ database
    budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        extract('month', Budget.month) == selected_month,
        extract('year', Budget.month) == selected_year
    ).all()
    
    # Map các category name tiếng Anh sang tên tiếng Việt
    category_name_map = {
        'Groceries': 'Thực phẩm',
        'Dining': 'Ăn uống',
        'Utilities': 'Hóa đơn & Dịch vụ',
        'Shopping': 'Mua sắm',
        'Entertainment': 'Giải trí',
        'Transportation': 'Di chuyển',
        'Health': 'Sức khỏe',
        'Other': 'Khác'
    }
    
    # Tạo mapping ngược từ tiếng Việt sang tiếng Anh để tìm kiếm
    reverse_map = {v: k for k, v in category_name_map.items()}
    
    # Tạo budget_data từ tất cả các danh mục chi tiêu
    budget_data = {}
    
    # Nếu không có budget trong tháng hiện tại, tạo mặc định cho tất cả danh mục
    if not budgets:
        for category in expense_category_names:
            # Chuyển đổi tên danh mục sang tiếng Việt nếu có trong mapping
            category_vi = category_name_map.get(category, category)
            # Bỏ qua các danh mục cần loại trừ
            if category_vi not in excluded_categories:
                budget_data[category_vi] = 300000  # Giá trị mặc định
    else:
        # Sử dụng dữ liệu từ database
        for budget in budgets:
            # Bỏ qua các danh mục cần loại trừ
            if budget.category not in excluded_categories:
                budget_data[budget.category] = float(budget.amount)
        
        # Thêm các danh mục chưa có trong budget
        for category in expense_category_names:
            category_vi = category_name_map.get(category, category)
            if category_vi not in excluded_categories and category_vi not in budget_data:
                budget_data[category_vi] = 300000  # Giá trị mặc định
    
    # Lấy chi tiêu thực tế theo danh mục
    category_expenses = db.session.query(
        Category.name,
        db.func.sum(Expense.amount).label('total')
    ).join(Expense, Expense.category_id == Category.id)\
     .filter(Expense.user_id == current_user.id,
             extract('month', Expense.date) == selected_month,
             extract('year', Expense.date) == selected_year)\
     .group_by(Category.name)\
     .all()
    
    # Tạo dictionary lưu chi tiêu theo danh mục
    actual_expenses = {}
    for category, amount in category_expenses:
        category_name = category_name_map.get(category, category)
        if category_name not in excluded_categories:
            actual_expenses[category_name] = float(amount)
    
    # Tính toán tiến độ ngân sách
    budget_progress = []
    
    for category, budget in budget_data.items():
        actual = actual_expenses.get(category, 0)
        percentage = min(100, (actual / budget * 100)) if budget > 0 else 0
        
        budget_progress.append({
            'category': category,
            'budget': budget,
            'actual': actual,
            'percentage': round(percentage, 1),
            'status': 'danger' if percentage >= 80 else ('warning' if percentage >= 60 else 'primary')
        })
    
    # Sắp xếp theo phần trăm sử dụng giảm dần
    budget_progress.sort(key=lambda x: x['percentage'], reverse=True)
    
    return jsonify(budget_progress)

@app.route('/filter_by_month', methods=['POST'])
@login_required
def filter_by_month():
    # Lấy tháng và năm từ dữ liệu POST
    data = request.get_json()
    month = data.get('month')
    year = data.get('year')
    
    if not month or not year:
        return jsonify({'error': 'Tháng và năm không hợp lệ'}), 400
    
    # Lưu tháng và năm đã chọn vào session để có thể sử dụng ở các route khác
    session['selected_month'] = month
    session['selected_year'] = year
    
    # Danh sách tên tháng bằng tiếng Việt
    month_names = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", 
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    
    # Tạo chuỗi tháng/năm để hiển thị trên giao diện
    selected_period = f"{month_names[month-1]} {year}"
    
    return jsonify({
        'success': True,
        'message': f'Đã chọn {selected_period}',
        'selected_period': selected_period,
        'selected_month': month,
        'selected_year': year
    })

@app.route('/get_weekly_data')
@login_required
def get_weekly_data():
    # Lấy tháng và năm từ query params hoặc session hoặc mặc định 
    selected_month = request.args.get('month', default=session.get('selected_month'))
    selected_year = request.args.get('year', default=session.get('selected_year'))
    
    # Nếu không có dữ liệu tháng/năm từ session hoặc query params, sử dụng tháng và năm hiện tại
    current_month = int(selected_month) if selected_month else datetime.now().month
    current_year = int(selected_year) if selected_year else datetime.now().year
    
    # In log để debug
    print(f"Lấy dữ liệu tuần cho tháng {current_month}, năm {current_year}")
    
    # Tạo dict để lưu dữ liệu theo tuần
    weekly_data = {
        'expenses': [0] * 5,  # Giả sử mỗi tháng có 5 tuần
        'line_data': [0] * 5,  # Dữ liệu cho biểu đồ đường
        'labels': []  # Lưu nhãn ngày cho mỗi tuần
    }
    
    # Lấy ngày đầu tháng và cuối tháng
    first_day = datetime(current_year, current_month, 1)
    
    # Xác định ngày cuối tháng
    if current_month == 12:
        last_day = datetime(current_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(current_year, current_month + 1, 1) - timedelta(days=1)
    
    # Tạo danh sách các tuần trong tháng
    current_day = first_day
    week_start_dates = []
    
    while current_day <= last_day:
        # Lấy ngày đầu tuần (Thứ Hai)
        start_of_week = current_day - timedelta(days=current_day.weekday())
        if start_of_week not in week_start_dates:
            week_start_dates.append(start_of_week)
        current_day += timedelta(days=1)
    
    # Tạo nhãn cho mỗi tuần
    for i, start_date in enumerate(week_start_dates[:5]):  # Giới hạn 5 tuần
        end_date = min(start_date + timedelta(days=6), last_day)
        weekly_data['labels'].append(f"{start_date.day}/{start_date.month} - {end_date.day}/{end_date.month}")
    
    # Lấy chi tiêu theo từng ngày trong tháng
    daily_expenses = db.session.query(
        Expense.date,
        db.func.sum(Expense.amount).label('total')
    ).filter(
        extract('month', Expense.date) == current_month,
        extract('year', Expense.date) == current_year,
        Expense.user_id == current_user.id
    ).group_by(Expense.date).all()
    
    # Phân bổ chi tiêu theo tuần
    for expense_date, total in daily_expenses:
        # Xác định tuần của ngày chi tiêu
        expense_date_obj = expense_date
        start_of_week = expense_date_obj - timedelta(days=expense_date_obj.weekday())
        
        # Tìm index của tuần trong danh sách
        if start_of_week in week_start_dates:
            week_index = week_start_dates.index(start_of_week)
            if week_index < 5:  # Chỉ xử lý 5 tuần
                weekly_data['expenses'][week_index] += float(total)
                weekly_data['line_data'][week_index] += float(total)
    
    # Tính toán tổng chi tiêu lũy kế cho biểu đồ đường
    total_so_far = 0
    for i in range(len(weekly_data['line_data'])):
        total_so_far += weekly_data['line_data'][i]
        weekly_data['line_data'][i] = total_so_far
    
    return jsonify(weekly_data)

@app.route('/get_budgets')
@login_required
def get_budgets():
    # Lấy tháng và năm hiện tại hoặc được chọn từ session
    selected_month = session.get('selected_month', datetime.now().month)
    selected_year = session.get('selected_year', datetime.now().year)
    
    # Danh sách các danh mục cần loại bỏ
    excluded_categories = ['Thực phẩm', 'Ăn uống']
    
    # Lấy tất cả danh mục chi tiêu của người dùng
    expense_categories = db.session.query(Category.name).distinct().filter(
        Category.type == 'expense',
        (Category.user_id == current_user.id) | (Category.user_id == db.session.query(User.id).filter(User.username == 'system').scalar())
    ).all()
    
    expense_category_names = [cat[0] for cat in expense_categories]
    
    # Map các category name tiếng Anh sang tên tiếng Việt
    category_name_map = {
        'Groceries': 'Thực phẩm',
        'Dining': 'Ăn uống',
        'Utilities': 'Hóa đơn & Dịch vụ',
        'Shopping': 'Mua sắm',
        'Entertainment': 'Giải trí',
        'Transportation': 'Di chuyển',
        'Health': 'Sức khỏe',
        'Other': 'Khác'
    }
    
    # Truy vấn danh sách budget từ database
    budgets = Budget.query.filter(
        Budget.user_id == current_user.id,
        extract('month', Budget.month) == selected_month,
        extract('year', Budget.month) == selected_year
    ).all()
    
    # Tạo dictionary từ budgets hiện có
    existing_budgets = {}
    for budget in budgets:
        if budget.category not in excluded_categories:
            existing_budgets[budget.category] = float(budget.amount)
    
    # Tạo danh sách budget cho tất cả danh mục, sử dụng giá trị hiện có hoặc mặc định
    budget_data = []
    
    for category in expense_category_names:
        # Chuyển đổi tên danh mục sang tiếng Việt nếu có trong mapping
        category_vi = category_name_map.get(category, category)
        
        # Bỏ qua các danh mục bị loại trừ
        if category_vi in excluded_categories:
            continue
        
        # Sử dụng giá trị đã có hoặc giá trị mặc định
        amount = existing_budgets.get(category_vi, 300000)
        
        budget_data.append({
            'category': category_vi,
            'amount': amount
        })
    
    # Thêm các budget đã tồn tại nhưng không nằm trong danh mục chi tiêu
    for category, amount in existing_budgets.items():
        if not any(item['category'] == category for item in budget_data) and category not in excluded_categories:
            budget_data.append({
                'category': category,
                'amount': amount
            })
    
    return jsonify(budget_data)

@app.route('/set_budget', methods=['POST'])
@login_required
def set_budget():
    data = request.get_json()
    
    # Kiểm tra dữ liệu
    if not data or 'budgets' not in data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ'}), 400
    
    # Lấy tháng và năm hiện tại hoặc được chọn từ session
    selected_month = session.get('selected_month', datetime.now().month)
    selected_year = session.get('selected_year', datetime.now().year)
    
    # Tạo ngày đầu tháng làm ngày tham chiếu
    budget_month = datetime(selected_year, selected_month, 1)
    
    # Xóa ngân sách cũ của tháng hiện tại
    Budget.query.filter(
        Budget.user_id == current_user.id,
        extract('month', Budget.month) == selected_month,
        extract('year', Budget.month) == selected_year
    ).delete()
    
    # Thêm ngân sách mới
    for budget_item in data['budgets']:
        category = budget_item.get('category')
        amount = budget_item.get('amount')
        
        if not category or not amount:
            continue
        
        budget = Budget(
            user_id=current_user.id,
            category=category,
            amount=amount,
            month=budget_month
        )
        db.session.add(budget)
    
    # Lưu vào database
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Cập nhật ngân sách thành công'})

@app.route('/get_daily_expenses')
@login_required
def get_daily_expenses():
    # Lấy ngày hiện tại
    today = datetime.now().date()
    
    # Tính ngày đầu tuần (thứ Hai) và cuối tuần (Chủ Nhật)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Tạo danh sách các ngày trong tuần
    days_of_week = []
    day_labels = []
    
    # Tên các ngày trong tuần bằng tiếng Việt
    vn_days = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']
    
    # Tạo danh sách các ngày và nhãn
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        days_of_week.append(day)
        day_labels.append(f"{vn_days[i]} ({day.day}/{day.month})")
    
    # Tạo dict để lưu dữ liệu chi tiêu theo ngày
    daily_data = {
        'expenses': [0] * 7,  # 7 ngày trong tuần
        'line_data': [0] * 7,  # Dữ liệu cho biểu đồ đường
        'labels': day_labels
    }
    
    # Lấy chi tiêu theo từng ngày trong tuần
    daily_expenses = db.session.query(
        Expense.date,
        db.func.sum(Expense.amount).label('total')
    ).filter(
        Expense.date.between(start_of_week, end_of_week),
        Expense.user_id == current_user.id
    ).group_by(Expense.date).all()
    
    # Cập nhật dữ liệu chi tiêu
    for expense_date, total in daily_expenses:
        # Xác định index của ngày trong tuần (0 = Thứ Hai, 6 = Chủ Nhật)
        day_index = (expense_date - start_of_week).days
        if 0 <= day_index < 7:
            daily_data['expenses'][day_index] = float(total)
            daily_data['line_data'][day_index] = float(total)
    
    # Tính toán tổng chi tiêu lũy kế cho biểu đồ đường
    total_so_far = 0
    for i in range(7):
        total_so_far += daily_data['line_data'][i]
        daily_data['line_data'][i] = total_so_far
    
    return jsonify(daily_data)

@app.route('/debug_check_data')
def debug_check_data():
    """Debug route để kiểm tra dữ liệu chi tiêu ngày 14/3/2024."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Kiểm tra chi tiêu cụ thể ngày 14/3/2024
    specific_date = datetime(2024, 3, 14).date()
    
    march_14_expenses = db.session.query(
        Expense.id, 
        Expense.amount, 
        Expense.date, 
        Expense.description,
        Category.name.label('category_name')
    ).join(
        Category, 
        Expense.category_id == Category.id
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date == specific_date
    ).all()
    
    # Lấy tổng chi tiêu theo từng ngày trong tháng 3/2024
    march_start = datetime(2024, 3, 1).date()
    march_end = datetime(2024, 3, 31).date()
    
    march_expenses = db.session.query(
        func.date(Expense.date).label('date'),
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= march_start,
        Expense.date <= march_end
    ).group_by(
        func.date(Expense.date)
    ).order_by(
        func.date(Expense.date)
    ).all()
    
    # Chuyển đổi kết quả thành định dạng JSON
    march_14_data = []
    for expense in march_14_expenses:
        march_14_data.append({
            'id': expense.id,
            'amount': expense.amount,
            'date': expense.date.strftime('%d/%m/%Y'),
            'description': expense.description,
            'category_name': expense.category_name
        })
    
    march_data = []
    for day in march_expenses:
        march_data.append({
            'date': day.date.strftime('%d/%m/%Y') if isinstance(day.date, datetime) else day.date,
            'total': day.total
        })
    
    return jsonify({
        'march_14_expenses': march_14_data,
        'march_expenses': march_data
    })

@app.route("/export_file")
@login_required
def export_file():
    return render_template('Export_file.html', title='Xuất báo cáo chi tiêu')

@app.route("/preview_export", methods=['POST'])
@login_required
def preview_export():
    try:
        # Lấy tháng và năm từ form
        month_str = request.form.get('month')
        if not month_str:
            return jsonify({"success": False, "message": "Vui lòng chọn tháng báo cáo"})
        
        year, month = map(int, month_str.split('-'))
        
        # Xác định ngày đầu tiên và cuối cùng của tháng
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Kiểm tra các loại dữ liệu cần xuất
        include_income = request.form.get('includeIncome') == 'true'
        include_expense = request.form.get('includeExpense') == 'true'
        include_chart = request.form.get('includeChart') == 'true'
        
        # Chuẩn bị dữ liệu
        data = {}
        
        # Lấy dữ liệu thu nhập
        if include_income:
            incomes = db.session.query(
                Income.id,
                Income.amount,
                Income.description,
                Income.date,
                Category.name.label('category_name')
            ).join(
                Category, 
                Income.category_id == Category.id
            ).filter(
                Income.user_id == current_user.id,
                Income.date >= first_day,
                Income.date <= last_day
            ).order_by(Income.date).all()
            
            # Tổng thu nhập
            total_income_result = db.session.query(
                func.sum(Income.amount)
            ).filter(
                Income.user_id == current_user.id,
                Income.date >= first_day,
                Income.date <= last_day
            ).first()
            
            # Định dạng dữ liệu thu nhập
            formatted_incomes = []
            for income in incomes:
                formatted_incomes.append({
                    'id': income.id,
                    'amount': float(income.amount),
                    'description': income.description,
                    'date': income.date.strftime('%d/%m/%Y'),
                    'category': income.category_name
                })
            
            data['incomes'] = formatted_incomes
            data['totalIncome'] = float(total_income_result[0] or 0)
        
        # Lấy dữ liệu chi tiêu
        if include_expense:
            expenses = db.session.query(
                Expense.id,
                Expense.amount,
                Expense.description,
                Expense.date,
                Category.name.label('category_name')
            ).join(
                Category, 
                Expense.category_id == Category.id
            ).filter(
                Expense.user_id == current_user.id,
                Expense.date >= first_day,
                Expense.date <= last_day
            ).order_by(Expense.date).all()
            
            # Tổng chi tiêu
            total_expense_result = db.session.query(
                func.sum(Expense.amount)
            ).filter(
                Expense.user_id == current_user.id,
                Expense.date >= first_day,
                Expense.date <= last_day
            ).first()
            
            # Định dạng dữ liệu chi tiêu
            formatted_expenses = []
            for expense in expenses:
                formatted_expenses.append({
                    'id': expense.id,
                    'amount': float(expense.amount),
                    'description': expense.description,
                    'date': expense.date.strftime('%d/%m/%Y'),
                    'category': expense.category_name
                })
            
            data['expenses'] = formatted_expenses
            data['totalExpense'] = float(total_expense_result[0] or 0)
        
        # Lấy dữ liệu cho biểu đồ
        if include_chart and include_expense:
            # Chi tiêu theo danh mục
            category_expenses = db.session.query(
                Category.name,
                func.sum(Expense.amount).label('total')
            ).join(
                Expense,
                Expense.category_id == Category.id
            ).filter(
                Expense.user_id == current_user.id,
                Expense.date >= first_day,
                Expense.date <= last_day
            ).group_by(
                Category.name
            ).all()
            
            # Định dạng dữ liệu biểu đồ
            category_data = {}
            for item in category_expenses:
                category_data[item.name] = float(item.total)
            
            data['categoryExpenses'] = category_data
        
        return jsonify({"success": True, "data": data})
    
    except Exception as e:
        app.logger.error(f"Error in preview_export: {str(e)}")
        return jsonify({"success": False, "message": f"Đã xảy ra lỗi: {str(e)}"})

@app.route("/download_excel", methods=['POST'])
@login_required
def download_excel():
    try:
        from io import BytesIO
        import xlsxwriter
        from datetime import datetime, timedelta
        from flask import send_file
        
        # Lấy tháng và năm từ form
        month_str = request.form.get('month')
        if not month_str:
            return jsonify({"success": False, "message": "Vui lòng chọn tháng báo cáo"})
        
        year, month = map(int, month_str.split('-'))
        
        # Xác định ngày đầu tiên và cuối cùng của tháng
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Kiểm tra các loại dữ liệu cần xuất
        include_income = request.form.get('includeIncome') == 'true'
        include_expense = request.form.get('includeExpense') == 'true'
        include_chart = request.form.get('includeChart') == 'true'
        
        # Tạo workbook mới
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Định dạng chung
        title_format = workbook.add_format({
            'bold': True, 
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAD3',
            'border': 1,
            'align': 'center'
        })
        
        expense_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F4CCCC',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left'
        })
        
        amount_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0',
            'align': 'right'
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy',
            'align': 'center'
        })
        
        # Tạo một worksheet cho tổng quan
        summary_sheet = workbook.add_worksheet('Tổng quan')
        
        # Tiêu đề
        month_names = [
            "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6", 
            "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
        ]
        title = f"BÁO CÁO CHI TIÊU {month_names[month-1].upper()} NĂM {year}"
        summary_sheet.merge_range('A1:E1', title, title_format)
        
        # Thông tin người dùng
        summary_sheet.write('A3', 'Người dùng:', workbook.add_format({'bold': True}))
        summary_sheet.write('B3', current_user.username)
        
        # Thêm dòng trống
        current_row = 5
        
        # Tổng thu nhập và chi tiêu
        summary_sheet.write('A5', 'Tổng quan:', workbook.add_format({'bold': True}))
        current_row += 1
        
        # Lấy tổng thu nhập
        total_income_result = db.session.query(
            func.sum(Income.amount)
        ).filter(
            Income.user_id == current_user.id,
            Income.date >= first_day,
            Income.date <= last_day
        ).first()
        total_income = float(total_income_result[0] or 0)
        
        # Lấy tổng chi tiêu
        total_expense_result = db.session.query(
            func.sum(Expense.amount)
        ).filter(
            Expense.user_id == current_user.id,
            Expense.date >= first_day,
            Expense.date <= last_day
        ).first()
        total_expense = float(total_expense_result[0] or 0)
        
        # Số dư cuối kỳ
        balance = total_income - total_expense
        
        # Viết tổng thu nhập, chi tiêu và số dư
        summary_sheet.write('A6', 'Tổng thu nhập:')
        summary_sheet.write('B6', total_income, amount_format)
        current_row += 1
        
        summary_sheet.write('A7', 'Tổng chi tiêu:')
        summary_sheet.write('B7', total_expense, amount_format)
        current_row += 1
        
        summary_sheet.write('A8', 'Số dư:')
        summary_sheet.write('B8', balance, amount_format)
        current_row += 2
        
        # Tạo bảng thu nhập nếu được yêu cầu
        if include_income:
            # Lấy dữ liệu thu nhập
            incomes = db.session.query(
                Income.id,
                Income.amount,
                Income.description,
                Income.date,
                Category.name.label('category_name')
            ).join(
                Category, 
                Income.category_id == Category.id
            ).filter(
                Income.user_id == current_user.id,
                Income.date >= first_day,
                Income.date <= last_day
            ).order_by(Income.date).all()
            
            # Tạo worksheet cho thu nhập
            income_sheet = workbook.add_worksheet('Thu nhập')
            
            # Tiêu đề
            income_title = f"DANH SÁCH THU NHẬP {month_names[month-1].upper()} NĂM {year}"
            income_sheet.merge_range('A1:E1', income_title, title_format)
            
            # Tiêu đề bảng
            income_sheet.write('A3', 'STT', header_format)
            income_sheet.write('B3', 'Ngày', header_format)
            income_sheet.write('C3', 'Danh mục', header_format)
            income_sheet.write('D3', 'Mô tả', header_format)
            income_sheet.write('E3', 'Số tiền (VNĐ)', header_format)
            
            # Thiết lập độ rộng cột
            income_sheet.set_column('A:A', 5)
            income_sheet.set_column('B:B', 12)
            income_sheet.set_column('C:C', 20)
            income_sheet.set_column('D:D', 30)
            income_sheet.set_column('E:E', 15)
            
            # Điền dữ liệu
            for i, income in enumerate(incomes):
                row = i + 4
                income_sheet.write(f'A{row}', i + 1, cell_format)
                income_sheet.write_datetime(f'B{row}', income.date, date_format)
                income_sheet.write(f'C{row}', income.category_name, cell_format)
                income_sheet.write(f'D{row}', income.description or '-', cell_format)
                income_sheet.write(f'E{row}', float(income.amount), amount_format)
            
            # Tổng cộng
            total_row = len(incomes) + 4
            income_sheet.write(f'D{total_row}', 'Tổng cộng:', workbook.add_format({'bold': True, 'align': 'right'}))
            income_sheet.write(f'E{total_row}', total_income, workbook.add_format({'bold': True, 'num_format': '#,##0', 'align': 'right'}))
            
            # Thêm vào bảng tổng quan
            summary_sheet.write(f'A{current_row}', 'Chi tiết Thu nhập:', workbook.add_format({'bold': True}))
            current_row += 1
            
            summary_sheet.write(f'A{current_row}', 'STT')
            summary_sheet.write(f'B{current_row}', 'Danh mục')
            summary_sheet.write(f'C{current_row}', 'Số tiền (VNĐ)')
            summary_sheet.write(f'D{current_row}', 'Tỷ lệ (%)')
            current_row += 1
            
            # Thu nhập theo danh mục
            category_incomes = db.session.query(
                Category.name,
                func.sum(Income.amount).label('total')
            ).join(
                Income,
                Income.category_id == Category.id
            ).filter(
                Income.user_id == current_user.id,
                Income.date >= first_day,
                Income.date <= last_day
            ).group_by(
                Category.name
            ).all()
            
            for i, item in enumerate(category_incomes):
                percentage = (float(item.total) / total_income * 100) if total_income > 0 else 0
                summary_sheet.write(f'A{current_row}', i + 1)
                summary_sheet.write(f'B{current_row}', item.name)
                summary_sheet.write(f'C{current_row}', float(item.total), amount_format)
                summary_sheet.write(f'D{current_row}', f'{percentage:.2f}%')
                current_row += 1
            
            current_row += 1
            
        # Tạo bảng chi tiêu nếu được yêu cầu
        if include_expense:
            # Lấy dữ liệu chi tiêu
            expenses = db.session.query(
                Expense.id,
                Expense.amount,
                Expense.description,
                Expense.date,
                Category.name.label('category_name')
            ).join(
                Category, 
                Expense.category_id == Category.id
            ).filter(
                Expense.user_id == current_user.id,
                Expense.date >= first_day,
                Expense.date <= last_day
            ).order_by(Expense.date).all()
            
            # Tạo worksheet cho chi tiêu
            expense_sheet = workbook.add_worksheet('Chi tiêu')
            
            # Tiêu đề
            expense_title = f"DANH SÁCH CHI TIÊU {month_names[month-1].upper()} NĂM {year}"
            expense_sheet.merge_range('A1:E1', expense_title, title_format)
            
            # Tiêu đề bảng
            expense_sheet.write('A3', 'STT', expense_header_format)
            expense_sheet.write('B3', 'Ngày', expense_header_format)
            expense_sheet.write('C3', 'Danh mục', expense_header_format)
            expense_sheet.write('D3', 'Mô tả', expense_header_format)
            expense_sheet.write('E3', 'Số tiền (VNĐ)', expense_header_format)
            
            # Thiết lập độ rộng cột
            expense_sheet.set_column('A:A', 5)
            expense_sheet.set_column('B:B', 12)
            expense_sheet.set_column('C:C', 20)
            expense_sheet.set_column('D:D', 30)
            expense_sheet.set_column('E:E', 15)
            
            # Điền dữ liệu
            for i, expense in enumerate(expenses):
                row = i + 4
                expense_sheet.write(f'A{row}', i + 1, cell_format)
                expense_sheet.write_datetime(f'B{row}', expense.date, date_format)
                expense_sheet.write(f'C{row}', expense.category_name, cell_format)
                expense_sheet.write(f'D{row}', expense.description or '-', cell_format)
                expense_sheet.write(f'E{row}', float(expense.amount), amount_format)
            
            # Tổng cộng
            total_row = len(expenses) + 4
            expense_sheet.write(f'D{total_row}', 'Tổng cộng:', workbook.add_format({'bold': True, 'align': 'right'}))
            expense_sheet.write(f'E{total_row}', total_expense, workbook.add_format({'bold': True, 'num_format': '#,##0', 'align': 'right'}))
            
            # Thêm vào bảng tổng quan
            summary_sheet.write(f'A{current_row}', 'Chi tiết Chi tiêu:', workbook.add_format({'bold': True}))
            current_row += 1
            
            summary_sheet.write(f'A{current_row}', 'STT')
            summary_sheet.write(f'B{current_row}', 'Danh mục')
            summary_sheet.write(f'C{current_row}', 'Số tiền (VNĐ)')
            summary_sheet.write(f'D{current_row}', 'Tỷ lệ (%)')
            current_row += 1
            
            # Chi tiêu theo danh mục
            category_expenses = db.session.query(
                Category.name,
                func.sum(Expense.amount).label('total')
            ).join(
                Expense,
                Expense.category_id == Category.id
            ).filter(
                Expense.user_id == current_user.id,
                Expense.date >= first_day,
                Expense.date <= last_day
            ).group_by(
                Category.name
            ).all()
            
            # Dữ liệu cho biểu đồ
            category_names = []
            category_values = []
            
            for i, item in enumerate(category_expenses):
                percentage = (float(item.total) / total_expense * 100) if total_expense > 0 else 0
                summary_sheet.write(f'A{current_row}', i + 1)
                summary_sheet.write(f'B{current_row}', item.name)
                summary_sheet.write(f'C{current_row}', float(item.total), amount_format)
                summary_sheet.write(f'D{current_row}', f'{percentage:.2f}%')
                current_row += 1
                
                category_names.append(item.name)
                category_values.append(float(item.total))
            
            current_row += 1
            
            # Thêm biểu đồ nếu được yêu cầu và có dữ liệu chi tiêu
            if include_chart and len(category_expenses) > 0:
                # Tạo worksheet cho biểu đồ
                chart_sheet = workbook.add_worksheet('Biểu đồ')
                
                # Thiết lập độ rộng cột
                chart_sheet.set_column('A:A', 30)  # Cột danh mục
                chart_sheet.set_column('B:B', 20)  # Cột số tiền
                chart_sheet.set_column('C:C', 15)  # Cột tỷ lệ
                
                # Tiêu đề
                chart_title = f"BIỂU ĐỒ CHI TIÊU THEO DANH MỤC {month_names[month-1].upper()} NĂM {year}"
                chart_sheet.merge_range('A1:E1', chart_title, title_format)
                
                # Thêm dữ liệu cho biểu đồ
                chart_sheet.write('A3', 'Danh mục', header_format)
                chart_sheet.write('B3', 'Số tiền (VNĐ)', header_format)
                chart_sheet.write('C3', 'Tỷ lệ (%)', header_format)
                
                # Điền dữ liệu cho bảng
                for i, (name, value) in enumerate(zip(category_names, category_values)):
                    row = i + 4
                    percentage = (value / total_expense * 100) if total_expense > 0 else 0
                    chart_sheet.write(f'A{row}', name, cell_format)
                    chart_sheet.write(f'B{row}', value, amount_format)
                    chart_sheet.write(f'C{row}', f'{percentage:.2f}%', cell_format)
                
                # Tạo biểu đồ tròn
                pie_chart = workbook.add_chart({'type': 'pie'})
                
                # Thêm dữ liệu vào biểu đồ
                last_row = len(category_names) + 3
                pie_chart.add_series({
                    'name': 'Chi tiêu theo danh mục',
                    'categories': f'=Biểu đồ!$A$4:$A${last_row}',
                    'values': f'=Biểu đồ!$B$4:$B${last_row}',
                    'data_labels': {
                        'percentage': True,
                        'category': True,
                        'position': 'outside_end',
                        'font': {'size': 10}
                    },
                })
                
                # Thiết lập tiêu đề biểu đồ
                pie_chart.set_title({'name': 'Tỷ lệ chi tiêu theo danh mục', 'name_font': {'size': 14, 'bold': True}})
                
                # Thiết lập kích thước và vị trí biểu đồ
                pie_chart.set_size({'width': 500, 'height': 400})
                
                # Thêm biểu đồ vào worksheet
                chart_sheet.insert_chart('D4', pie_chart)
        
        # Đóng workbook và trả về file
        workbook.close()
        output.seek(0)
        
        # Trả về file Excel sử dụng send_file của Flask
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Bao_cao_chi_tieu_{month}_{year}.xlsx'
        )
    
    except Exception as e:
        app.logger.error(f"Error in download_excel: {str(e)}")
        return jsonify({"success": False, "message": f"Đã xảy ra lỗi: {str(e)}"}), 500