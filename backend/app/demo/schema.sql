-- QueryMind Demo Database Schema
-- Realistic Enterprise E-Commerce & Operations Synthetic Database

DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS departments CASCADE;

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE,
    budget NUMERIC(15, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE departments IS 'Company functional departments and budgetary allocations';
COMMENT ON COLUMN departments.budget IS 'Annual operational budget for department';

-- Employees
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    department_id INT REFERENCES departments(id) ON DELETE SET NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    salary NUMERIC(12, 2) NOT NULL,
    hire_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_salary ON employees(salary);
COMMENT ON TABLE employees IS 'Corporate personnel with departmental links and compensation details';

-- Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(50),
    city VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    tier VARCHAR(50) DEFAULT 'Standard', -- Bronze, Silver, Gold, Platinum
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_customers_country ON customers(country);
CREATE INDEX idx_customers_tier ON customers(tier);
COMMENT ON TABLE customers IS 'Registered client base with geographic and loyalty segment metadata';

-- Products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    cost NUMERIC(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(price);
COMMENT ON TABLE products IS 'Merchandise catalogue with unit sales pricing and inventory levels';

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    order_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL, -- completed, pending, cancelled, refunded, shipped
    total_amount NUMERIC(12, 2) NOT NULL,
    shipping_city VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
COMMENT ON TABLE orders IS 'Customer order transactions with completion states';

-- Order Items
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE RESTRICT,
    quantity INT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL
);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
COMMENT ON TABLE order_items IS 'Itemized product quantities and line totals per transaction';

-- Payments
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id) ON DELETE CASCADE,
    payment_method VARCHAR(50) NOT NULL, -- credit_card, paypal, bank_transfer, stripe
    payment_status VARCHAR(50) NOT NULL, -- success, failed, refunded
    amount NUMERIC(12, 2) NOT NULL,
    transaction_reference VARCHAR(100) UNIQUE NOT NULL,
    paid_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(payment_status);
COMMENT ON TABLE payments IS 'Settlement transactions and payment gateway records';

-- Subscriptions
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL, -- Starter, Pro, Enterprise
    monthly_price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL, -- active, cancelled, paused
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
COMMENT ON TABLE subscriptions IS 'Recurring SaaS service agreements linked to customers';
