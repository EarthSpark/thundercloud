CREATE TABLE sales_accounts_users (
    sales_account_id CHAR(32) NOT NULL,
    user_id CHAR(32) NOT NULL,
    id CHAR(32) DEFAULT uuid_generate_v4() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(sales_account_id) REFERENCES sales_account (id),
    FOREIGN KEY(user_id) REFERENCES "user" (id)
)

