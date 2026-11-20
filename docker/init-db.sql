-- Create application and demo databases
CREATE DATABASE querymind;
CREATE DATABASE querymind_demo;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE querymind TO postgres;
GRANT ALL PRIVILEGES ON DATABASE querymind_demo TO postgres;

