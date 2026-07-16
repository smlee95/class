import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_products.db"
    monkeypatch.setattr(main, "DB_FILE", str(db_path))
    main.initialize_database()
    yield db_path


def test_product_crud_flow(isolated_db):
    product_id = main.add_product("노트북", 1299000.0, 10)
    assert product_id is not None

    products = main.get_products()
    assert len(products) == 1
    assert products[0]["product_name"] == "노트북"
    assert products[0]["price"] == 1299000.0

    main.update_product(product_id, "노트북 Pro", 1499000.0, 5)
    updated = main.get_products()[0]
    assert updated["product_name"] == "노트북 Pro"
    assert updated["stock_quantity"] == 5

    main.delete_product(product_id)
    assert main.get_products() == []


def test_product_metadata_and_summary(isolated_db):
    main.add_product("마우스", 50000.0, 3, category="전자기기", description="무선 마우스")

    products = main.get_products()
    assert products[0]["category"] == "전자기기"
    assert products[0]["description"] == "무선 마우스"

    summary = main.get_product_summary()
    assert summary["total_products"] == 1
    assert summary["total_stock"] == 3
    assert summary["total_value"] == 50000.0
    assert summary["low_stock_count"] == 1
