import json
import os
import re
import sqlite3
from datetime import datetime

import streamlit as st

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DATA_FILE = os.path.join(os.path.dirname(__file__), "customers.json")
DB_FILE = os.path.join(os.path.dirname(__file__), "products.db")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[0-9\-\s()+]+$")


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_customers():
    ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_customers(customers):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(customers, f, ensure_ascii=False, indent=2)


def get_next_customer_id(customers):
    if not customers:
        return 1
    return max(customer["id"] for customer in customers) + 1


def validate_email(email):
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_phone(phone):
    return bool(PHONE_PATTERN.match(phone.strip()))


def login_form():
    st.title("HelloAI 고객관리 시스템")
    st.write("관리자 계정으로 로그인해야 고객과 상품을 조회하고 관리할 수 있습니다.")

    with st.form("login_form"):
        username = st.text_input("관리자 ID")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state["logged_in"] = True
            st.session_state["login_message"] = "로그인 성공. 관리 화면으로 이동합니다."
            st.experimental_rerun()
        else:
            st.error("관리자 ID 또는 비밀번호가 올바르지 않습니다.")


def logout():
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.experimental_rerun()


def render_customer_table(customers, search_text):
    filtered = []
    if search_text:
        search_text = search_text.lower()
        for customer in customers:
            if (
                search_text in str(customer["id"]).lower()
                or search_text in customer["name"].lower()
                or search_text in customer["email"].lower()
                or search_text in customer["phone"].lower()
            ):
                filtered.append(customer)
    else:
        filtered = customers

    if not filtered:
        st.info("조건에 맞는 고객 정보가 없습니다.")
        return []

    st.dataframe(
        [
            {
                "고객ID": customer["id"],
                "이름": customer["name"],
                "이메일": customer["email"],
                "전화번호": customer["phone"],
                "가입일시": customer["joined_at"],
            }
            for customer in filtered
        ],
        use_container_width=True,
    )
    return filtered


def add_customer(customers):
    st.subheader("신규 고객 등록")
    with st.form("add_customer"):
        name = st.text_input("이름")
        email = st.text_input("이메일")
        phone = st.text_input("전화번호")
        submitted = st.form_submit_button("등록")

    if submitted:
        if not name.strip():
            st.warning("이름을 입력해주세요.")
            return
        if not validate_email(email):
            st.warning("올바른 이메일 형식을 입력해주세요.")
            return
        if not validate_phone(phone):
            st.warning("올바른 전화번호를 입력해주세요. 숫자와 -, (), 공백만 허용됩니다.")
            return

        new_customer = {
            "id": get_next_customer_id(customers),
            "name": name.strip(),
            "email": email.strip(),
            "phone": phone.strip(),
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        customers.append(new_customer)
        save_customers(customers)
        st.success(f"고객 {new_customer['name']}님이 등록되었습니다.")
        st.experimental_rerun()


def update_customer(customers):
    st.subheader("고객 정보 수정 / 삭제")
    if not customers:
        st.info("등록된 고객이 없습니다.")
        return

    customer_map = {f"{customer['id']} - {customer['name']}": customer for customer in customers}
    selected_key = st.selectbox("수정할 고객 선택", [""] + list(customer_map.keys()))
    if not selected_key:
        return

    customer = customer_map[selected_key]
    with st.form("update_customer"):
        st.text_input("고객ID", value=str(customer["id"]), disabled=True)
        name = st.text_input("이름", value=customer["name"])
        email = st.text_input("이메일", value=customer["email"])
        phone = st.text_input("전화번호", value=customer["phone"])
        st.text_input("가입일시", value=customer["joined_at"], disabled=True)
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("수정 저장")
        with col2:
            deleted = st.form_submit_button("삭제", help="선택한 고객 정보를 삭제합니다.")

    if submitted:
        if not name.strip():
            st.warning("이름을 입력해주세요.")
            return
        if not validate_email(email):
            st.warning("올바른 이메일 형식을 입력해주세요.")
            return
        if not validate_phone(phone):
            st.warning("올바른 전화번호를 입력해주세요. 숫자와 -, (), 공백만 허용됩니다.")
            return

        customer["name"] = name.strip()
        customer["email"] = email.strip()
        customer["phone"] = phone.strip()
        save_customers(customers)
        st.success("고객 정보가 변경되었습니다.")
        st.experimental_rerun()

    if deleted:
        customers.remove(customer)
        save_customers(customers)
        st.warning("고객 정보가 삭제되었습니다.")
        st.experimental_rerun()


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                category TEXT DEFAULT '일반',
                description TEXT DEFAULT '',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def get_products():
    initialize_database()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT product_id, product_name, price, stock_quantity, category, description, updated_at FROM product ORDER BY product_id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def add_product(product_name, price, stock_quantity, category="일반", description=""):
    initialize_database()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO product (product_name, price, stock_quantity, category, description, updated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (product_name, float(price), int(stock_quantity), category, description),
        )
        conn.commit()
        return cursor.lastrowid


def update_product(product_id, product_name, price, stock_quantity, category="일반", description=""):
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            "UPDATE product SET product_name = ?, price = ?, stock_quantity = ?, category = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
            (product_name, float(price), int(stock_quantity), category, description, int(product_id)),
        )
        conn.commit()


def delete_product(product_id):
    initialize_database()
    with get_connection() as conn:
        conn.execute("DELETE FROM product WHERE product_id = ?", (int(product_id),))
        conn.commit()


def get_product_summary():
    products = get_products()
    total_products = len(products)
    total_stock = sum(int(product["stock_quantity"]) for product in products)
    total_value = sum(float(product["price"]) * int(product["stock_quantity"]) for product in products)
    low_stock_count = sum(1 for product in products if int(product["stock_quantity"]) <= 5)
    return {
        "total_products": total_products,
        "total_stock": total_stock,
        "total_value": round(total_value, 2),
        "low_stock_count": low_stock_count,
    }


def render_product_table(products, search_text):
    filtered = []
    if search_text:
        search_text = search_text.lower()
        for product in products:
            if (
                search_text in str(product["product_id"]).lower()
                or search_text in product["product_name"].lower()
                or search_text in str(product["price"]).lower()
                or search_text in str(product["stock_quantity"]).lower()
                or search_text in product.get("category", "").lower()
                or search_text in product.get("description", "").lower()
            ):
                filtered.append(product)
    else:
        filtered = products

    if not filtered:
        st.info("조건에 맞는 상품 정보가 없습니다.")
        return []

    st.dataframe(
        [
            {
                "상품ID": product["product_id"],
                "상품명": product["product_name"],
                "카테고리": product.get("category", "일반"),
                "가격": f"{product['price']:.2f}",
                "재고": product["stock_quantity"],
                "설명": product.get("description", ""),
                "수정일시": product["updated_at"],
            }
            for product in filtered
        ],
        use_container_width=True,
    )
    return filtered


def add_product_form():
    st.subheader("신규 상품 등록")
    with st.form("add_product"):
        product_name = st.text_input("상품명")
        category = st.selectbox("카테고리", ["일반", "전자기기", "생활용품", "식품", "의류"])
        price = st.number_input("가격", min_value=0.0, step=1000.0, format="%.2f")
        stock_quantity = st.number_input("재고 수량", min_value=0, step=1)
        description = st.text_area("상품 설명")
        submitted = st.form_submit_button("등록")

    if submitted:
        if not product_name.strip():
            st.warning("상품명을 입력해주세요.")
            return

        product_id = add_product(product_name.strip(), price, stock_quantity, category=category, description=description)
        st.success(f"상품이 등록되었습니다. (상품ID: {product_id})")
        st.experimental_rerun()


def update_product_form(products):
    st.subheader("상품 정보 수정 / 삭제")
    if not products:
        st.info("등록된 상품이 없습니다.")
        return

    product_map = {f"{product['product_id']} - {product['product_name']}": product for product in products}
    selected_key = st.selectbox("수정할 상품 선택", [""] + list(product_map.keys()))
    if not selected_key:
        return

    product = product_map[selected_key]
    with st.form("update_product"):
        st.text_input("상품ID", value=str(product["product_id"]), disabled=True)
        product_name = st.text_input("상품명", value=product["product_name"])
        category = st.selectbox(
            "카테고리",
            ["일반", "전자기기", "생활용품", "식품", "의류"],
            index=["일반", "전자기기", "생활용품", "식품", "의류"].index(product.get("category", "일반")),
        )
        price = st.number_input("가격", min_value=0.0, value=float(product["price"]), step=1000.0, format="%.2f")
        stock_quantity = st.number_input("재고 수량", min_value=0, value=int(product["stock_quantity"]), step=1)
        description = st.text_area("상품 설명", value=product.get("description", ""))
        st.text_input("수정일시", value=product["updated_at"], disabled=True)
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("수정 저장")
        with col2:
            deleted = st.form_submit_button("삭제", help="선택한 상품 정보를 삭제합니다.")

    if submitted:
        if not product_name.strip():
            st.warning("상품명을 입력해주세요.")
            return

        update_product(product["product_id"], product_name.strip(), price, stock_quantity, category=category, description=description)
        st.success("상품 정보가 변경되었습니다.")
        st.experimental_rerun()

    if deleted:
        delete_product(product["product_id"])
        st.warning("상품 정보가 삭제되었습니다.")
        st.experimental_rerun()


def render_product_management():
    st.header("상품 관리")
    summary = get_product_summary()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("등록 상품 수", summary["total_products"])
    col2.metric("총 재고", summary["total_stock"])
    col3.metric("재고 금액", f"{summary['total_value']:,.0f}원")
    col4.metric("품절 임박", summary["low_stock_count"])

    tab1, tab2 = st.tabs(["상품 현황", "상품 등록"])

    with tab1:
        st.header("상품 현황")
        search_text = st.text_input("상품 검색 (상품명, 카테고리, 설명, 가격, 재고)")
        products = get_products()
        filtered_products = render_product_table(products, search_text)
        if filtered_products:
            update_product_form(products)

    with tab2:
        st.header("상품 등록")
        add_product_form()


def main():
    st.set_page_config(page_title="HelloAI 고객관리", layout="wide")
    initialize_database()

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login_form()
        return

    st.sidebar.title("관리자 메뉴")
    st.sidebar.write("HelloAI 고객관리 시스템에 오신 것을 환영합니다.")
    management_mode = st.sidebar.radio("관리 항목", ["고객 관리", "상품 관리"], index=0)
    logout()

    if management_mode == "상품 관리":
        render_product_management()
    else:
        customers = load_customers()

        tab1, tab2 = st.tabs(["고객 현황", "고객 등록"])

        with tab1:
            st.header("고객 현황")
            search_text = st.text_input("고객 검색 (ID, 이름, 이메일, 전화번호)")
            filtered_customers = render_customer_table(customers, search_text)
            if filtered_customers:
                update_customer(customers)

        with tab2:
            st.header("고객 등록")
            add_customer(customers)

    st.markdown("---")
    st.info("관리자 계정: admin / 비밀번호: admin123")


if __name__ == "__main__":
    main()
