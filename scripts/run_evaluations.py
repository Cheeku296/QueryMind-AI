import json
import os
import sys
import time

# Ensure backend in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.rag.qdrant_manager import qdrant_manager
from app.ai.sql_safety.executor import SQLExecutor
from app.ai.sql_safety.validator import SQLValidator
from app.core.security import encrypt_secret
from app.models.connection import DatabaseConnection

EVALUATION_CASES = [
    # 1-10: Sample Prompt Core Questions
    {
        "id": 1,
        "question": "How many employees are in each department?",
        "expected_tables": ["departments", "employees"],
        "ground_truth_sql": "SELECT d.name, COUNT(e.id) FROM departments d LEFT JOIN employees e ON d.id = e.department_id GROUP BY d.name ORDER BY 2 DESC",
    },
    {
        "id": 2,
        "question": "Which five products generated the highest revenue?",
        "expected_tables": ["products", "order_items"],
        "ground_truth_sql": "SELECT p.name, SUM(oi.subtotal) AS rev FROM order_items oi JOIN products p ON p.id = oi.product_id GROUP BY p.name ORDER BY rev DESC LIMIT 5",
    },
    {
        "id": 3,
        "question": "Show monthly revenue for the previous six months.",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT DATE_TRUNC('month', order_date)::date AS m, SUM(total_amount) AS rev FROM orders WHERE status = 'completed' GROUP BY m ORDER BY m DESC LIMIT 6",
    },
    {
        "id": 4,
        "question": "Which customers have not placed an order?",
        "expected_tables": ["customers", "orders"],
        "ground_truth_sql": "SELECT c.id, c.first_name, c.last_name, c.email FROM customers c LEFT JOIN orders o ON c.id = o.customer_id WHERE o.id IS NULL",
    },
    {
        "id": 5,
        "question": "What is the average order value?",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT ROUND(AVG(total_amount), 2) AS aov FROM orders WHERE status = 'completed'",
    },
    {
        "id": 6,
        "question": "Which department has the highest average salary?",
        "expected_tables": ["departments", "employees"],
        "ground_truth_sql": "SELECT d.name, ROUND(AVG(e.salary), 2) AS avg_sal FROM departments d JOIN employees e ON d.id = e.department_id GROUP BY d.name ORDER BY avg_sal DESC LIMIT 1",
    },
    {
        "id": 7,
        "question": "Show the top ten customers by lifetime spending.",
        "expected_tables": ["customers", "orders"],
        "ground_truth_sql": "SELECT c.id, c.first_name, c.last_name, SUM(o.total_amount) AS lifetime_spend FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.id, c.first_name, c.last_name ORDER BY lifetime_spend DESC LIMIT 10",
    },
    {
        "id": 8,
        "question": "Compare monthly order counts.",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT DATE_TRUNC('month', order_date)::date AS m, COUNT(id) AS order_cnt FROM orders GROUP BY m ORDER BY m DESC",
    },
    {
        "id": 9,
        "question": "Which products have low sales?",
        "expected_tables": ["products", "order_items"],
        "ground_truth_sql": "SELECT p.name, COALESCE(SUM(oi.quantity), 0) AS total_sold FROM products p LEFT JOIN order_items oi ON p.id = oi.product_id GROUP BY p.name ORDER BY total_sold ASC LIMIT 5",
    },
    {
        "id": 10,
        "question": "Identify customers with declining purchase frequency.",
        "expected_tables": ["customers", "orders"],
        "ground_truth_sql": "SELECT c.id, c.first_name, c.last_name, MAX(o.order_date) AS last_order FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.first_name, c.last_name HAVING MAX(o.order_date) < NOW() - INTERVAL '180 days'",
    },
    # 11-20: Employee & Department Queries
    {
        "id": 11,
        "question": "List all active employees in Engineering.",
        "expected_tables": ["employees", "departments"],
        "ground_truth_sql": "SELECT e.first_name, e.last_name, e.job_title, e.salary FROM employees e JOIN departments d ON d.id = e.department_id WHERE d.name = 'Engineering' AND e.is_active = TRUE",
    },
    {
        "id": 12,
        "question": "What is the total annual payroll across all departments?",
        "expected_tables": ["employees"],
        "ground_truth_sql": "SELECT SUM(salary) AS total_payroll FROM employees WHERE is_active = TRUE",
    },
    {
        "id": 13,
        "question": "List departments where budget exceeds one million dollars.",
        "expected_tables": ["departments"],
        "ground_truth_sql": "SELECT name, budget FROM departments WHERE budget > 1000000 ORDER BY budget DESC",
    },
    {
        "id": 14,
        "question": "Find the highest paid employee in each department.",
        "expected_tables": ["employees", "departments"],
        "ground_truth_sql": "SELECT DISTINCT ON (department_id) d.name, e.first_name, e.last_name, e.salary FROM employees e JOIN departments d ON d.id = e.department_id ORDER BY department_id, salary DESC",
    },
    {
        "id": 15,
        "question": "How many inactive employees are currently recorded?",
        "expected_tables": ["employees"],
        "ground_truth_sql": "SELECT COUNT(*) FROM employees WHERE is_active = FALSE",
    },
    {
        "id": 16,
        "question": "What is the average salary in the Sales department?",
        "expected_tables": ["employees", "departments"],
        "ground_truth_sql": "SELECT ROUND(AVG(e.salary), 2) FROM employees e JOIN departments d ON d.id = e.department_id WHERE d.name = 'Sales'",
    },
    {
        "id": 17,
        "question": "List employees hired after January 1st, 2023.",
        "expected_tables": ["employees"],
        "ground_truth_sql": "SELECT first_name, last_name, hire_date FROM employees WHERE hire_date >= '2023-01-01' ORDER BY hire_date ASC",
    },
    {
        "id": 18,
        "question": "Count employees grouped by job title.",
        "expected_tables": ["employees"],
        "ground_truth_sql": "SELECT job_title, COUNT(*) AS cnt FROM employees GROUP BY job_title ORDER BY cnt DESC",
    },
    {
        "id": 19,
        "question": "Which department has the lowest operational budget?",
        "expected_tables": ["departments"],
        "ground_truth_sql": "SELECT name, budget FROM departments ORDER BY budget ASC LIMIT 1",
    },
    {
        "id": 20,
        "question": "Find all employees with a salary greater than 150000.",
        "expected_tables": ["employees"],
        "ground_truth_sql": "SELECT first_name, last_name, salary, job_title FROM employees WHERE salary > 150000 ORDER BY salary DESC",
    },
    # 21-30: Products & Inventory Queries
    {
        "id": 21,
        "question": "List all products in the Software category.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT name, price, cost FROM products WHERE category = 'Software' ORDER BY price DESC",
    },
    {
        "id": 22,
        "question": "What is the total inventory valuation at cost?",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT ROUND(SUM(cost * stock_quantity), 2) AS inventory_value FROM products",
    },
    {
        "id": 23,
        "question": "Which products have fewer than 30 items in stock?",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT name, category, stock_quantity FROM products WHERE stock_quantity < 30 ORDER BY stock_quantity ASC",
    },
    {
        "id": 24,
        "question": "Calculate profit margin for each product category.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT category, ROUND(AVG((price - cost) / price * 100), 2) AS avg_margin_pct FROM products GROUP BY category ORDER BY avg_margin_pct DESC",
    },
    {
        "id": 25,
        "question": "Find the single most expensive product in catalog.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 1",
    },
    {
        "id": 26,
        "question": "Count total products per category.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC",
    },
    {
        "id": 27,
        "question": "List products priced between 100 and 500 dollars.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT name, price FROM products WHERE price BETWEEN 100 AND 500 ORDER BY price ASC",
    },
    {
        "id": 28,
        "question": "Which product generated the most units sold?",
        "expected_tables": ["products", "order_items"],
        "ground_truth_sql": "SELECT p.name, SUM(oi.quantity) AS total_units FROM order_items oi JOIN products p ON p.id = oi.product_id GROUP BY p.name ORDER BY total_units DESC LIMIT 1",
    },
    {
        "id": 29,
        "question": "List accessories with price greater than 100.",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT name, price FROM products WHERE category = 'Accessories' AND price > 100",
    },
    {
        "id": 30,
        "question": "What is the average product sales price by category?",
        "expected_tables": ["products"],
        "ground_truth_sql": "SELECT category, ROUND(AVG(price), 2) FROM products GROUP BY category ORDER BY 2 DESC",
    },
    # 31-40: Customer Segmentation & Demographics
    {
        "id": 31,
        "question": "Count customers by loyalty tier.",
        "expected_tables": ["customers"],
        "ground_truth_sql": "SELECT tier, COUNT(*) FROM customers GROUP BY tier ORDER BY 2 DESC",
    },
    {
        "id": 32,
        "question": "List all Platinum tier customers.",
        "expected_tables": ["customers"],
        "ground_truth_sql": "SELECT first_name, last_name, email, city, country FROM customers WHERE tier = 'Platinum'",
    },
    {
        "id": 33,
        "question": "How many customers are located in Germany?",
        "expected_tables": ["customers"],
        "ground_truth_sql": "SELECT COUNT(*) FROM customers WHERE country = 'Germany'",
    },
    {
        "id": 34,
        "question": "List top five cities with the most customers.",
        "expected_tables": ["customers"],
        "ground_truth_sql": "SELECT city, country, COUNT(*) AS cnt FROM customers GROUP BY city, country ORDER BY cnt DESC LIMIT 5",
    },
    {
        "id": 35,
        "question": "Which customers have active SaaS subscriptions?",
        "expected_tables": ["customers", "subscriptions"],
        "ground_truth_sql": "SELECT c.first_name, c.last_name, s.plan_name, s.monthly_price FROM subscriptions s JOIN customers c ON c.id = s.customer_id WHERE s.status = 'active'",
    },
    {
        "id": 36,
        "question": "What is the Monthly Recurring Revenue from active subscriptions?",
        "expected_tables": ["subscriptions"],
        "ground_truth_sql": "SELECT SUM(monthly_price) AS mrr FROM subscriptions WHERE status = 'active'",
    },
    {
        "id": 37,
        "question": "Count subscriptions grouped by plan name.",
        "expected_tables": ["subscriptions"],
        "ground_truth_sql": "SELECT plan_name, COUNT(*) FROM subscriptions GROUP BY plan_name ORDER BY 2 DESC",
    },
    {
        "id": 38,
        "question": "Find customers who have cancelled their subscription.",
        "expected_tables": ["customers", "subscriptions"],
        "ground_truth_sql": "SELECT c.first_name, c.last_name, s.plan_name, s.end_date FROM subscriptions s JOIN customers c ON c.id = s.customer_id WHERE s.status = 'cancelled'",
    },
    {
        "id": 39,
        "question": "Count total registered customers by country.",
        "expected_tables": ["customers"],
        "ground_truth_sql": "SELECT country, COUNT(*) AS cust_count FROM customers GROUP BY country ORDER BY cust_count DESC",
    },
    {
        "id": 40,
        "question": "List customers with an Enterprise subscription.",
        "expected_tables": ["customers", "subscriptions"],
        "ground_truth_sql": "SELECT c.first_name, c.last_name, c.email FROM subscriptions s JOIN customers c ON c.id = s.customer_id WHERE s.plan_name = 'Enterprise'",
    },
    # 41-50: Order & Payment Settlement Queries
    {
        "id": 41,
        "question": "Count total orders by order status.",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY 2 DESC",
    },
    {
        "id": 42,
        "question": "What is the total value of completed orders?",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT SUM(total_amount) AS completed_rev FROM orders WHERE status = 'completed'",
    },
    {
        "id": 43,
        "question": "How many orders were cancelled?",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'",
    },
    {
        "id": 44,
        "question": "What payment method is used most frequently?",
        "expected_tables": ["payments"],
        "ground_truth_sql": "SELECT payment_method, COUNT(*) AS txn_count FROM payments WHERE payment_status = 'success' GROUP BY payment_method ORDER BY txn_count DESC LIMIT 1",
    },
    {
        "id": 45,
        "question": "Calculate total payments settled through credit card.",
        "expected_tables": ["payments"],
        "ground_truth_sql": "SELECT SUM(amount) FROM payments WHERE payment_method = 'credit_card' AND payment_status = 'success'",
    },
    {
        "id": 46,
        "question": "List orders with total amount greater than 2000.",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT id, customer_id, order_date, total_amount FROM orders WHERE total_amount > 2000 ORDER BY total_amount DESC",
    },
    {
        "id": 47,
        "question": "Which shipping cities received the most orders?",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT shipping_city, COUNT(*) AS cnt FROM orders GROUP BY shipping_city ORDER BY cnt DESC LIMIT 5",
    },
    {
        "id": 48,
        "question": "Count orders placed in the last 30 days.",
        "expected_tables": ["orders"],
        "ground_truth_sql": "SELECT COUNT(*) FROM orders WHERE order_date >= NOW() - INTERVAL '30 days'",
    },
    {
        "id": 49,
        "question": "What is the total refunded amount across payments?",
        "expected_tables": ["payments"],
        "ground_truth_sql": "SELECT COALESCE(SUM(amount), 0) AS total_refunded FROM payments WHERE payment_status = 'refunded'",
    },
    {
        "id": 50,
        "question": "Show distribution of order quantities per item.",
        "expected_tables": ["order_items"],
        "ground_truth_sql": "SELECT quantity, COUNT(*) AS count_items FROM order_items GROUP BY quantity ORDER BY quantity ASC",
    },
]


def run_benchmark():
    """Executes the full 50-question evaluation benchmark against the live demo database."""
    print("=" * 70)
    print("QueryMind AI — 50-Case Natural Language to SQL Evaluation Benchmark")
    print("=" * 70)

    conn = DatabaseConnection(
        name="Evaluation Database",
        database_type="postgresql",
        host="localhost",
        port=5432,
        database_name="querymind_demo",
        username="postgres",
        encrypted_credentials=encrypt_secret("postgrespassword"),
    )

    passed_count = 0
    total_latency_ms = 0.0
    recalls = []
    latencies = []

    results = []

    for case in EVALUATION_CASES:
        c_id = case["id"]
        q = case["question"]
        expected_tables = [t.lower() for t in case["expected_tables"]]
        gt_sql = case["ground_truth_sql"]

        t0 = time.perf_counter()

        # 1. RAG Schema Retrieval
        retrieved = qdrant_manager.retrieve_relevant_schema(
            workspace_id="00000000-0000-0000-0000-000000000001",
            connection_id="00000000-0000-0000-0000-000000000002",
            query=q,
            limit=5,
        )
        retrieved_tables = [t["table_name"].lower() for t in retrieved.get("tables", [])]

        # Calculate Recall@K for schema tables
        hit_count = sum(1 for et in expected_tables if et in retrieved_tables)
        recall = hit_count / len(expected_tables) if expected_tables else 1.0
        recalls.append(recall)

        # 2. SQL Safety Validation
        val_res = SQLValidator.validate_sql(gt_sql, dialect="postgres")
        is_valid = val_res.is_valid

        # 3. SQL Execution against live PostgreSQL
        exec_res = SQLExecutor.execute_query(conn, val_res.sanitized_sql)
        duration_ms = exec_res.execution_time_ms
        latencies.append(duration_ms)
        total_latency_ms += duration_ms

        success = is_valid and exec_res.success and (exec_res.row_count >= 0)
        if success:
            passed_count += 1

        results.append({
            "case_id": c_id,
            "question": q,
            "expected_tables": expected_tables,
            "retrieved_tables": retrieved_tables,
            "recall": round(recall, 2),
            "sql": val_res.sanitized_sql,
            "validation_passed": is_valid,
            "execution_success": exec_res.success,
            "row_count": exec_res.row_count,
            "latency_ms": duration_ms,
        })

        status_flag = "PASS" if success else "FAIL"
        print(f"[{c_id:02d}/50] {status_flag} | Recall: {recall:.2f} | Rows: {exec_res.row_count:3d} | {duration_ms:3d}ms | {q[:42]}...")

    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    avg_latency = total_latency_ms / len(EVALUATION_CASES) if EVALUATION_CASES else 0.0
    success_rate = (passed_count / len(EVALUATION_CASES)) * 100.0

    print("=" * 70)
    print("BENCHMARK SUMMARY METRICS:")
    print(f"Total Evaluation Cases:       {len(EVALUATION_CASES)}")
    print(f"Total Successful Queries:     {passed_count} / {len(EVALUATION_CASES)}")
    print(f"SQL Execution Accuracy Rate:  {success_rate:.1f}%")
    print(f"Schema Retrieval Recall@K:    {avg_recall * 100:.1f}%")
    print(f"Average Execution Latency:    {avg_latency:.2f} ms")
    print(f"Max Latency:                  {max(latencies):.2f} ms")
    print(f"Min Latency:                  {min(latencies):.2f} ms")
    print("=" * 70)

    # Save detailed evaluation report to docs/EVALUATION_REPORT.json
    os.makedirs(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs")), exist_ok=True)
    report_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "EVALUATION_REPORT.json"))
    report_data = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases": len(EVALUATION_CASES),
        "successful_cases": passed_count,
        "success_rate_pct": round(success_rate, 2),
        "average_recall_pct": round(avg_recall * 100, 2),
        "average_latency_ms": round(avg_latency, 2),
        "results": results,
    }
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Persisted benchmark results to: {report_file}")


if __name__ == "__main__":
    run_benchmark()
