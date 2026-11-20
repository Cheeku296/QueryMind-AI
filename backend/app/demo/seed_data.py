import os
import random
from datetime import date, datetime, timedelta, timezone
import psycopg

DEMO_DB_URL = os.getenv(
    "DEMO_DATABASE_URL",
    "postgresql://postgres:postgrespassword@localhost:5432/querymind_demo",
).replace("+psycopg", "")


def seed_demo_database(db_url: str = DEMO_DB_URL):
    """Initializes and seeds querymind_demo database with realistic e-commerce and HR data."""
    random.seed(42)  # Deterministic seed

    # Read schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print(f"Connecting to demo database: {db_url}...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Apply schema
            print("Applying demo schema...")
            cur.execute(schema_sql)

            # 2. Seed departments
            print("Seeding departments...")
            departments = [
                ("Engineering", "ENG", 1850000.00),
                ("Sales", "SLS", 1200000.00),
                ("Marketing", "MKT", 950000.00),
                ("Customer Support", "SUP", 650000.00),
                ("Finance", "FIN", 800000.00),
                ("Human Resources", "HR", 450000.00),
                ("Data & AI", "DAI", 1400000.00),
            ]
            cur.executemany(
                "INSERT INTO departments (name, code, budget) VALUES (%s, %s, %s)",
                departments,
            )

            # Retrieve department IDs
            cur.execute("SELECT id, name FROM departments ORDER BY id")
            dept_map = {name: id for id, name in cur.fetchall()}

            # 3. Seed employees (45 employees)
            print("Seeding employees...")
            first_names = [
                "Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", "Alexander",
                "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn",
                "Aarav", "Priya", "Carlos", "Elena", "Jin", "Mei", "Marcus", "Chloe", "Tariq", "Fatima",
                "Lukas", "Astrid", "Mateo", "Camila", "Dmitry", "Olga", "Kofi", "Amina", "Kenji", "Yuki",
                "Ethan", "Grace", "Leo", "Zoe", "Sam"
            ]
            last_names = [
                "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
                "Patel", "Sharma", "Tanaka", "Sato", "Kim", "Park", "Mueller", "Schmidt", "Dubois", "Moreau",
                "Silva", "Santos", "Novak", "Kowalski", "Ivanov", "Petrov", "Mensah", "Osei", "Suzuki", "Takahashi",
                "Clark", "Lewis", "Robinson", "Walker", "Hall"
            ]

            roles_by_dept = {
                "Engineering": [
                    ("Staff Software Engineer", 145000, 185000),
                    ("Senior Backend Developer", 120000, 150000),
                    ("Frontend Developer", 95000, 125000),
                    ("DevOps Engineer", 110000, 140000),
                    ("QA Automation Engineer", 85000, 110000),
                ],
                "Data & AI": [
                    ("Principal AI Architect", 170000, 210000),
                    ("Senior Machine Learning Engineer", 140000, 175000),
                    ("Data Engineer", 115000, 145000),
                    ("Data Analyst", 85000, 115000),
                ],
                "Sales": [
                    ("VP of Enterprise Sales", 160000, 200000),
                    ("Account Executive", 85000, 120000),
                    ("Sales Development Rep", 55000, 75000),
                ],
                "Marketing": [
                    ("Head of Growth", 130000, 160000),
                    ("Product Marketing Manager", 100000, 130000),
                    ("Content Strategist", 70000, 90000),
                ],
                "Customer Support": [
                    ("Support Operations Lead", 85000, 105000),
                    ("Tier 2 Technical Specialist", 65000, 80000),
                    ("Customer Support Rep", 45000, 60000),
                ],
                "Finance": [
                    ("Controller", 140000, 170000),
                    ("Senior Financial Analyst", 95000, 125000),
                    ("Staff Accountant", 70000, 90000),
                ],
                "Human Resources": [
                    ("Director of People Operations", 130000, 160000),
                    ("Technical Recruiter", 80000, 105000),
                    ("HR Generalist", 60000, 80000),
                ],
            }

            emp_records = []
            used_emails = set()
            today = date.today()

            for i in range(45):
                dept_name = list(roles_by_dept.keys())[i % len(roles_by_dept)]
                dept_id = dept_map[dept_name]
                role_info = roles_by_dept[dept_name][i % len(roles_by_dept[dept_name])]
                title = role_info[0]
                salary = round(random.uniform(role_info[1], role_info[2]), 2)
                fn = first_names[i]
                ln = last_names[i]
                email_base = f"{fn.lower()}.{ln.lower()}"
                email = f"{email_base}@corp.querymind.internal"
                while email in used_emails:
                    email = f"{email_base}{random.randint(1, 99)}@corp.querymind.internal"
                used_emails.add(email)

                hire_days_ago = random.randint(100, 2500)
                hire_date = today - timedelta(days=hire_days_ago)
                is_active = random.random() > 0.08  # 8% left company

                emp_records.append((dept_id, fn, ln, email, title, salary, hire_date, is_active))

            cur.executemany(
                """INSERT INTO employees 
                   (department_id, first_name, last_name, email, job_title, salary, hire_date, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                emp_records,
            )

            # 4. Seed customers (75 customers)
            print("Seeding customers...")
            cities_countries = [
                ("New York", "USA"), ("San Francisco", "USA"), ("Austin", "USA"), ("Seattle", "USA"),
                ("London", "UK"), ("Manchester", "UK"), ("Berlin", "Germany"), ("Munich", "Germany"),
                ("Toronto", "Canada"), ("Vancouver", "Canada"), ("Sydney", "Australia"), ("Melbourne", "Australia"),
                ("Paris", "France"), ("Lyon", "France"), ("Tokyo", "Japan"), ("Osaka", "Japan"),
                ("Bengaluru", "India"), ("Mumbai", "India"), ("Singapore", "Singapore"), ("Amsterdam", "Netherlands")
            ]
            tiers = ["Platinum", "Gold", "Silver", "Standard"]
            tier_weights = [0.1, 0.25, 0.35, 0.3]

            cust_records = []
            for i in range(75):
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                email = f"{fn.lower()}.{ln.lower()}{i+10}@example.com"
                city, country = random.choice(cities_countries)
                tier = random.choices(tiers, weights=tier_weights)[0]
                phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
                cust_records.append((fn, ln, email, phone, city, country, tier))

            cur.executemany(
                """INSERT INTO customers (first_name, last_name, email, phone, city, country, tier)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                cust_records,
            )

            # Retrieve customer IDs
            cur.execute("SELECT id FROM customers ORDER BY id")
            customer_ids = [r[0] for r in cur.fetchall()]

            # 5. Seed products (25 products)
            print("Seeding products...")
            products = [
                ("SKU-1001", "UltraBook Pro 16", "Laptops", 1899.99, 1250.00, 45),
                ("SKU-1002", "Developer Workstation X", "Desktops", 2799.00, 1900.00, 20),
                ("SKU-1003", "Ergonomic Mechanical Keyboard", "Accessories", 159.50, 65.00, 180),
                ("SKU-1004", "Precision Wireless Mouse", "Accessories", 89.99, 32.00, 240),
                ("SKU-1005", "4K Ultra-Wide Monitor 34-inch", "Monitors", 749.00, 480.00, 60),
                ("SKU-1006", "Noise-Cancelling Studio Headset", "Audio", 299.99, 130.00, 110),
                ("SKU-1007", "USB-C Thunderbolt 4 Dock", "Accessories", 229.00, 95.00, 95),
                ("SKU-1008", "Cloud Server Rack Unit 2U", "Server Hardware", 4500.00, 3100.00, 15),
                ("SKU-1009", "Enterprise NVMe SSD 4TB", "Storage", 420.00, 240.00, 130),
                ("SKU-1010", "AI Acceleration GPU Board", "Hardware", 1999.00, 1450.00, 25),
                ("SKU-1011", "Smart Standing Desk Pro", "Furniture", 850.00, 490.00, 40),
                ("SKU-1012", "Aeron Chair Ergonomic", "Furniture", 1250.00, 750.00, 30),
                ("SKU-1013", "HD Conference Webcam 4K", "Audio & Video", 199.00, 85.00, 140),
                ("SKU-1014", "Managed Gigabit Switch 24P", "Networking", 380.00, 210.00, 75),
                ("SKU-1015", "Wi-Fi 7 Enterprise Access Point", "Networking", 450.00, 260.00, 85),
                ("SKU-1016", "QueryMind AI Analytics License (Annual)", "Software", 2400.00, 200.00, 999),
                ("SKU-1017", "PostgreSQL Performance Tuning Toolkit", "Software", 499.00, 50.00, 999),
                ("SKU-1018", "Data Governance & Compliance Suite", "Software", 3600.00, 300.00, 999),
                ("SKU-1019", "Automated SQL Security Scanner", "Software", 899.00, 80.00, 999),
                ("SKU-1020", "High-Speed Thermal Receipt Printer", "POS", 185.00, 85.00, 90),
                ("SKU-1021", "Barcode Scanner Wireless", "POS", 120.00, 45.00, 160),
                ("SKU-1022", "Magnetic Whiteboard 72x48", "Office Supplies", 145.00, 60.00, 50),
                ("SKU-1023", "Fiber Optic Patch Cable 10m (10pk)", "Networking", 95.00, 30.00, 300),
                ("SKU-1024", "Backup Battery UPS 1500VA", "Power", 320.00, 180.00, 70),
                ("SKU-1025", "Hardware Security Key FIDO2 (2pk)", "Security", 85.00, 28.00, 350),
            ]
            cur.executemany(
                """INSERT INTO products (sku, name, category, price, cost, stock_quantity)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                products,
            )

            # Retrieve product IDs with pricing
            cur.execute("SELECT id, price FROM products ORDER BY id")
            product_catalog = cur.fetchall()

            # 6. Seed orders & order items & payments
            print("Seeding orders, items and payments...")
            # We reserve 10 customers to NEVER have placed orders (question 4 test)
            active_customer_ids = customer_ids[10:]  # First 10 have zero orders!
            order_statuses = ["completed", "completed", "completed", "completed", "shipped", "pending", "cancelled", "refunded"]
            payment_methods = ["credit_card", "paypal", "bank_transfer", "stripe"]

            now = datetime.now(timezone.utc)
            order_count = 320
            order_id = 1

            for _ in range(order_count):
                cust_id = random.choice(active_customer_ids)
                days_ago = random.randint(1, 365)
                order_date = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
                status = random.choice(order_statuses)

                # Pick 1 to 4 items
                num_items = random.randint(1, 4)
                chosen_products = random.sample(product_catalog, num_items)
                order_items_data = []
                order_total = 0.0

                for prod_id, unit_price in chosen_products:
                    qty = random.randint(1, 3)
                    subtotal = round(float(unit_price) * qty, 2)
                    order_total += subtotal
                    order_items_data.append((prod_id, qty, unit_price, subtotal))

                order_total = round(order_total, 2)
                shipping_city = random.choice(["New York", "San Francisco", "London", "Berlin", "Toronto", "Sydney", "Paris", "Tokyo"])

                cur.execute(
                    """INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_city)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (cust_id, order_date, status, order_total, shipping_city),
                )
                curr_order_id = cur.fetchone()[0]

                # Insert items
                for prod_id, qty, unit_price, subtotal in order_items_data:
                    cur.execute(
                        """INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (curr_order_id, prod_id, qty, unit_price, subtotal),
                    )

                # Insert payment
                if status in ("completed", "shipped", "refunded"):
                    pay_status = "refunded" if status == "refunded" else "success"
                    method = random.choice(payment_methods)
                    ref = f"TXN-{curr_order_id:06d}-{random.randint(1000, 9999)}"
                    cur.execute(
                        """INSERT INTO payments (order_id, payment_method, payment_status, amount, transaction_reference, paid_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (curr_order_id, method, pay_status, order_total, ref, order_date + timedelta(minutes=5)),
                    )
                elif status == "cancelled":
                    # Some cancelled had failed payment attempts
                    cur.execute(
                        """INSERT INTO payments (order_id, payment_method, payment_status, amount, transaction_reference, paid_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (curr_order_id, "credit_card", "failed", order_total, f"TXN-FAIL-{curr_order_id:06d}", order_date),
                    )

            # 7. Seed subscriptions (40 subscriptions)
            print("Seeding subscriptions...")
            plans = [("Starter", 49.00), ("Pro", 199.00), ("Enterprise", 899.00)]
            sub_records = []
            for cust_id in random.sample(active_customer_ids, 40):
                plan_name, price = random.choice(plans)
                sub_status = random.choices(["active", "cancelled", "paused"], weights=[0.75, 0.15, 0.1])[0]
                start_days_ago = random.randint(30, 400)
                start_d = today - timedelta(days=start_days_ago)
                end_d = None if sub_status == "active" else start_d + timedelta(days=random.randint(30, 200))
                sub_records.append((cust_id, plan_name, price, sub_status, start_d, end_d))

            cur.executemany(
                """INSERT INTO subscriptions (customer_id, plan_name, monthly_price, status, start_date, end_date)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                sub_records,
            )

        conn.commit()
    print("Demo database successfully seeded!")


if __name__ == "__main__":
    seed_demo_database()

